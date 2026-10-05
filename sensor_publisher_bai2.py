"""Bài 2: Mô phỏng cảm biến nhiệt độ và độ ẩm định kỳ gửi dữ liệu JSON lên MQTT Broker.

- Topic mặc định: iot/lab/sensor01/data (hoặc iot/lab/<device_id>/data)
- Chu kỳ gửi: mặc định 3 giây/lần
- Định dạng dữ liệu (JSON):
    {
        "device_id": "sensor01",
        "temperature": 28.5,
        "humidity": 65.2
    }
- Giá trị sinh ngẫu nhiên:
    + Nhiệt độ: 20.0°C đến 40.0°C
    + Độ ẩm: 30.0% đến 80.0%
"""

import random
import time
from mqtt_common import (
    Session,
    device_id,
    finite_float,
    nonnegative_int,
    parse_args,
    parser_for,
    positive_float,
    run,
)


def main():
    # 1. Khởi tạo parser tham số dòng lệnh và cấu hình từ config.json
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="sensor01",
                        help="Mã định danh cảm biến (mặc định: sensor01)")
    parser.add_argument("--count", type=nonnegative_int, default=0,
                        help="Số lượng bản tin cần gửi (0 = gửi liên tục đến khi nhấn Ctrl+C)")
    parser.add_argument("--interval", type=positive_float, default=3,
                        help="Chu kỳ gửi dữ liệu tính bằng giây (mặc định: 3 giây)")
    parser.add_argument("--temperature", type=finite_float,
                        help="Cố định nhiệt độ (°C) để demo cảnh báo")
    parser.add_argument("--humidity", type=finite_float,
                        help="Cố định độ ẩm để demo cảnh báo")
    parser.add_argument("--seed", type=int,
                        help="Seed cố định bộ sinh số ngẫu nhiên khi kiểm thử")
    args = parse_args(parser)

    # 2. Kiểm tra tính hợp lệ của dải dữ liệu vật lý
    if args.temperature is not None and not -40 <= args.temperature <= 80:
        parser.error("Nhiệt độ mô phỏng phải nằm trong [-40, 80] °C.")
    if args.humidity is not None and not 0 <= args.humidity <= 100:
        parser.error("Độ ẩm phải nằm trong [0, 100] %.")

    # 3. Khởi tạo bộ sinh ngẫu nhiên
    rng = random.Random(args.seed)

    # 4. Xác định Topic MQTT theo cấu trúc: iot/lab/<device_id>/data
    topic = f"iot/lab/{args.device_id}/data"

    # 5. Mở phiên kết nối MQTT tới Broker (hỗ trợ tự động kết nối lại và dọn dẹp)
    with Session(args, "sensor-bai2") as session:
        sent = 0
        while args.count == 0 or sent < args.count:
            # Tạo dữ liệu ngẫu nhiên hoặc lấy giá trị cố định nếu được chỉ định
            temp_val = (
                args.temperature
                if args.temperature is not None
                else round(rng.uniform(20.0, 40.0), 1)
            )
            humi_val = (
                args.humidity
                if args.humidity is not None
                else round(rng.uniform(30.0, 80.0), 1)
            )

            # Đóng gói dữ liệu theo chuẩn JSON yêu cầu của đề bài
            data = {
                "device_id": args.device_id,
                "temperature": temp_val,
                "humidity": humi_val,
            }

            # Publish bản tin lên topic tương ứng
            session.send(topic, data)
            sent += 1
            print(f"Đã gửi [{sent}] | Topic: {topic} | Payload: {data}", flush=True)

            # Tạm dừng theo chu kỳ yêu cầu (mặc định 3 giây)
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(run(main))
