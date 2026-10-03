"""Bài 2: mô phỏng cảm biến gửi JSON nhiệt độ và độ ẩm mỗi 3 giây."""

import random
import time
from mqtt_common import (Session, device_id, finite_float, nonnegative_int,
                         parse_args, parser_for, positive_float, run)


def main():
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="sensor01")
    parser.add_argument("--count", type=nonnegative_int, default=0,
                        help="Số lần gửi, 0 = chạy liên tục")
    parser.add_argument("--interval", type=positive_float, default=3)
    parser.add_argument("--temperature", type=finite_float, help="Nhiệt độ cố định để demo cảnh báo")
    parser.add_argument("--humidity", type=finite_float, help="Độ ẩm cố định để demo cảnh báo")
    parser.add_argument("--seed", type=int, help="Seed để tái lập dữ liệu ngẫu nhiên")
    args = parse_args(parser)
    if args.temperature is not None and not -40 <= args.temperature <= 80:
        parser.error("Nhiệt độ mô phỏng phải nằm trong [-40, 80] °C.")
    if args.humidity is not None and not 0 <= args.humidity <= 100:
        parser.error("Độ ẩm phải nằm trong [0, 100] %.")
    rng = random.Random(args.seed)
    topic = f"iot/lab/{args.device_id}/data"
    with Session(args, "sensor-bai2") as session:
        sent = 0
        while args.count == 0 or sent < args.count:
            data = {
                "device_id": args.device_id,
                "temperature": args.temperature if args.temperature is not None else round(rng.uniform(20, 40), 1),
                "humidity": args.humidity if args.humidity is not None else round(rng.uniform(30, 80), 1),
            }
            session.send(topic, data)
            sent += 1
            print(f"Đã gửi [{sent}] | Topic: {topic} | Payload: {data}", flush=True)
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(run(main))
