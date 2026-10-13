"""Bài 2: mô phỏng cảm biến gửi JSON mỗi 3 giây vào sensor_data_queue."""

import argparse
import json
import math
import random

import pika

from amqp_common import connect, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", default="sensor01")
    parser.add_argument("--count", type=int, default=0, help="0: gửi liên tục")
    parser.add_argument("--temperature", type=float, help="Giá trị cố định để demo cảnh báo")
    parser.add_argument("--humidity", type=float, help="Giá trị cố định để demo cảnh báo")
    args = parser.parse_args()
    if args.count < 0 or not args.device_id.strip():
        parser.error("--count không được âm; --device-id không được trống")
    for value in (args.temperature, args.humidity):
        if value is not None and not math.isfinite(value):
            parser.error("Nhiệt độ và độ ẩm phải là số hữu hạn")

    with connect() as connection:
        channel = connection.channel()
        channel.queue_declare(queue="sensor_data_queue", durable=True)
        sent = 0
        while args.count == 0 or sent < args.count:
            data = {
                "device_id": args.device_id,
                "temperature": args.temperature if args.temperature is not None else round(random.uniform(20, 40), 1),
                "humidity": args.humidity if args.humidity is not None else round(random.uniform(30, 80), 1),
            }
            message = json.dumps(data, ensure_ascii=False, allow_nan=False)
            channel.basic_publish(exchange="", routing_key="sensor_data_queue",
                                  body=message.encode("utf-8"),
                                  properties=pika.BasicProperties(content_type="application/json"))
            print(f"Da gui: {message}", flush=True)
            sent += 1
            if args.count == 0 or sent < args.count:
                connection.sleep(3)


if __name__ == "__main__":
    raise SystemExit(run(main))
