"""Bài 3: nhập ON/OFF/STATUS/EXIT để điều khiển thiết bị."""

import asyncio
import json

import aiocoap

from coap_common import arguments, client_context, device_id, read_state, request, run


def setup(parser, config):
    parser.add_argument("--device-id", type=device_id, default="light01")


async def handle(context, args, command):
    path = f"iot/lab/{args.device_id}/status"
    if command == "STATUS":
        print("\nSending GET request...", flush=True)
        response = await request(context, args, aiocoap.GET, path)
        data = read_state(response, args.device_id)
        print(f"Response:\n{json.dumps(data, separators=(',', ':'))}", flush=True)
        return
    print("\nSending PUT request...", flush=True)
    payload = json.dumps({"device_id": args.device_id, "command": command}).encode("utf-8")
    response = await request(context, args, aiocoap.PUT, path, payload, 50)
    print(f"Response Code: {response.code}", flush=True)
    data = read_state(response, args.device_id)
    action = "bat" if data["status"] == "ON" else "tat"
    print(f"Da {action} den {data['device_id']}", flush=True)


async def main():
    args = arguments(__doc__, setup)
    context = await client_context()
    try:
        while True:
            try:
                command = input("Nhap lenh (ON/OFF/STATUS/EXIT): ").strip().upper()
            except EOFError:
                break
            if command == "EXIT":
                break
            if command not in ("ON", "OFF", "STATUS"):
                print("Lệnh không hợp lệ. Chọn ON, OFF, STATUS hoặc EXIT.\n", flush=True)
                continue
            try:
                await handle(context, args, command)
            except asyncio.TimeoutError:
                print("Lỗi: Hết thời gian chờ phản hồi từ server.", flush=True)
            except aiocoap.error.NetworkError:
                print("Lỗi: Không kết nối được server. Kiểm tra server, địa chỉ và cổng UDP.", flush=True)
            except (aiocoap.error.Error, ValueError) as error:
                print(f"Lỗi: {error or type(error).__name__}", flush=True)
            print(flush=True)
    finally:
        await context.shutdown()


if __name__ == "__main__":
    raise SystemExit(run(main))
