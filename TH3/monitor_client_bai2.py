"""Bài 2: truy vấn cảm biến mỗi 3 giây và cảnh báo theo ngưỡng."""

import asyncio
import math

import aiocoap

from coap_common import (arguments, client_context, device_id, nonnegative, now,
                         positive, read_json, request, run)


def display_sensor(response, expected_id):
    data = read_json(response)
    if data.get("device_id") != expected_id:
        raise ValueError("Mã thiết bị trong phản hồi không khớp.")
    for key, low, high in (("temperature", 20, 40), ("humidity", 30, 80)):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Giá trị {key} không hợp lệ.")
    print(f"[{now()}] Received sensor data\nDevice: {data['device_id']}\n"
          f"Temperature: {data['temperature']} C\nHumidity: {data['humidity']} %", flush=True)
    hot, dry = data["temperature"] > 35, data["humidity"] < 40
    if hot:
        print("CANH BAO: Nhiet do cao", flush=True)
    if dry:
        print("CANH BAO: Do am thap", flush=True)
    if not hot and not dry:
        print("Trang thai: Binh thuong", flush=True)


def setup(parser, config):
    parser.add_argument("--device-id", type=device_id, default="sensor01")
    parser.add_argument("--interval", type=positive, default=3)
    parser.add_argument("--count", type=nonnegative, default=0, help="0: chạy đến Ctrl+C")


async def main():
    args = arguments(__doc__, setup)
    context = await client_context()
    try:
        total = 0
        while args.count == 0 or total < args.count:
            start = asyncio.get_running_loop().time()
            try:
                response = await request(context, args, aiocoap.GET, f"iot/lab/{args.device_id}/data")
                display_sensor(response, args.device_id)
            except (ValueError, aiocoap.error.Error, OSError, asyncio.TimeoutError) as error:
                print(f"Lỗi đọc cảm biến: {str(error) or 'Hết thời gian chờ'}. Sẽ thử lại.", flush=True)
            total += 1
            if args.count == 0 or total < args.count:
                await asyncio.sleep(max(0, args.interval - (asyncio.get_running_loop().time() - start)))
    finally:
        await context.shutdown()


if __name__ == "__main__":
    raise SystemExit(run(main))
