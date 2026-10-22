"""Bài 3: nhập ON/OFF/STATUS/EXIT để điều khiển thiết bị."""

import json

import aiocoap

from coap_common import (arguments, client_context, device_id, request,
                         run, show_response, show_state)


def setup(parser, config):
    parser.add_argument("--device-id", type=device_id, default="light01")


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
                print("Lệnh không hợp lệ. Chọn ON, OFF, STATUS hoặc EXIT.", flush=True)
                continue
            path = f"iot/lab/{args.device_id}/status"
            if command == "STATUS":
                response = await request(context, args, aiocoap.GET, path)
            else:
                payload = json.dumps({"device_id": args.device_id, "command": command}).encode("utf-8")
                response = await request(context, args, aiocoap.PUT, path, payload, 50)
            show_response(response)
            show_state(response, args.device_id, "Trang thai hien tai")
    finally:
        await context.shutdown()


if __name__ == "__main__":
    raise SystemExit(run(main))
