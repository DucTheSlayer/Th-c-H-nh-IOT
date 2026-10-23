"""Cấu hình, UDP transport và xử lý phản hồi dùng chung cho TH3."""

import argparse
import asyncio
from datetime import datetime
import json
import math
from pathlib import Path
import re
import sys

import aiocoap


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Giá trị phải là số hữu hạn lớn hơn 0.")
    return number


def nonnegative(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("Giá trị phải >= 0.")
    return number


def arguments(description, setup=None):
    config = {"host": "127.0.0.1", "port": 5683, "timeout": 5,
              "student_name": "", "student_id": ""}
    path = Path(__file__).with_name("config.json")
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("config.json phải chứa một đối tượng JSON.")
        config.update(data)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--host", default=config["host"])
    parser.add_argument("--port", type=int, default=config["port"])
    parser.add_argument("--timeout", type=positive, default=config["timeout"])
    if setup:
        setup(parser, config)
    args = parser.parse_args()
    args.port = int(args.port)
    if not 1 <= args.port <= 65535:
        parser.error("Cổng phải nằm trong khoảng 1..65535.")
    args.timeout = positive(str(args.timeout))
    return args


def device_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("Mã thiết bị chỉ gồm chữ, số, _ và -.")
    return value


def uri(args, path):
    host = f"[{args.host}]" if ":" in args.host else args.host
    return f"coap://{host}:{args.port}/{path}"


async def client_context():
    # UDP đơn giản hoạt động trên cả Windows; không cần websockets/DTLS.
    return await aiocoap.Context.create_client_context(transports=["simple6"])


async def serve(site, args, background=None, banner=None):
    context = await aiocoap.Context.create_server_context(
        site, bind=(args.host, args.port), transports=["simplesocketserver"])
    task = asyncio.create_task(background()) if background else None
    try:
        print(banner or f"SERVER READY {args.host}:{args.port} (UDP)", flush=True)
        await asyncio.Future()
    finally:
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await context.shutdown()


async def request(context, args, method, path, payload=b"", content_format=None):
    message = aiocoap.Message(code=method, uri=uri(args, path), payload=payload)
    if content_format is not None:
        message.opt.content_format = content_format
    pending = context.request(message)
    try:
        return await asyncio.wait_for(pending.response, args.timeout)
    finally:
        if not pending.response.done():
            pending.response.cancel()


def show_response(response):
    print(f"Code: {response.code}\nPayload: {response.payload.decode('utf-8')}", flush=True)


def require_success(response):
    if not response.code.is_successful():
        raise ValueError(f"Server trả về {response.code}: {response.payload.decode('utf-8', errors='replace')}")


def json_message(data, code=aiocoap.CONTENT):
    return aiocoap.Message(code=code, payload=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                          content_format=50)


def read_json(response):
    require_success(response)
    if response.opt.content_format != 50:
        raise ValueError("Phản hồi không có Content-Format application/json (50).")
    data = json.loads(response.payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Payload JSON phải là một đối tượng.")
    return data


def now():
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def read_state(response, expected_id):
    data = read_json(response)
    if data.get("device_id") != expected_id or data.get("status") not in ("ON", "OFF"):
        raise ValueError("Payload trạng thái thiết bị không hợp lệ.")
    return data


def show_state(response, expected_id, label):
    data = read_state(response, expected_id)
    time = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{time}] {label}\nDevice: {data['device_id']}\nStatus: {data['status']}", flush=True)


def run(main):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")
    except (OSError, ValueError, TypeError, EOFError, argparse.ArgumentTypeError,
            aiocoap.error.Error, asyncio.TimeoutError) as error:
        detail = "Hết thời gian chờ phản hồi từ server" if isinstance(error, asyncio.TimeoutError) else str(error)
        print(f"Lỗi: {detail}. Kiểm tra server, địa chỉ và cổng UDP.", file=sys.stderr)
        return 1
    return 0
