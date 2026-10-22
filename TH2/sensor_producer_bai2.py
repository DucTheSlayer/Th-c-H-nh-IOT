"""
BUỔI THỰC HÀNH: LẬP TRÌNH PYTHON VỚI GIAO THỨC AMQP
Bài 2: Mô phỏng cảm biến IoT gửi dữ liệu môi trường (Sensor Producer)

Yêu cầu:
- Mô phỏng cảm biến định kỳ gửi dữ liệu đo môi trường mỗi 3 giây.
- Gửi dữ liệu vào queue: sensor_data_queue.
- Định dạng dữ liệu: JSON gồm device_id, temperature, humidity.
  Ví dụ: {"device_id": "sensor01", "temperature": 29.5, "humidity": 62.1}
- Giá trị nhiệt độ và độ ẩm được sinh ngẫu nhiên.

Gợi ý mở rộng:
- Bổ sung trường thời gian gửi (timestamp) qua cờ --include-timestamp.
- Mô phỏng 2 hoặc 3 cảm biến khác nhau qua cờ --devices hoặc --device-id.
- Hỗ trợ tham số --temperature và --humidity cố định để dễ dàng kiểm thử cảnh báo.
"""

import argparse
from datetime import datetime
import json
import math
import random

import pika

from amqp_common import connect, run


def parse_arguments():
    """Thiết lập và phân tích các tham số dòng lệnh."""
    parser = argparse.ArgumentParser(
        description="Mô phỏng cảm biến IoT gửi telemetry lên RabbitMQ qua AMQP."
    )
    parser.add_argument(
        "--device-id",
        type=str,
        default="sensor01",
        help="Mã định danh thiết bị cảm biến (mặc định: sensor01).",
    )
    parser.add_argument(
        "--devices",
        type=str,
        default=None,
        help="Danh sách mã cảm biến mô phỏng, phân tách bằng dấu phẩy (vd: sensor01,sensor02,sensor03).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Chu kỳ gửi dữ liệu tính bằng giây (mặc định: 3 giây).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Số lần gửi dữ liệu (mặc định: 0 = gửi liên tục đến khi dừng bằng Ctrl+C).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Nhiệt độ cố định để kiểm thử cảnh báo (vd: 36.4).",
    )
    parser.add_argument(
        "--humidity",
        type=float,
        default=None,
        help="Độ ẩm cố định để kiểm thử cảnh báo (vd: 38.9).",
    )
    parser.add_argument(
        "--include-timestamp",
        action="store_true",
        help="Mở rộng: bổ sung trường thời gian gửi (timestamp) vào JSON payload.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Kiểm tra tính hợp lệ của tham số
    if args.count < 0:
        raise ValueError("--count không được âm.")
    if args.interval <= 0:
        raise ValueError("--interval phải lớn hơn 0.")
    for val, name in [(args.temperature, "temperature"), (args.humidity, "humidity")]:
        if val is not None and not math.isfinite(val):
            raise ValueError(f"{name} phải là số hữu hạn.")

    # Xác định danh sách cảm biến cần mô phỏng
    if args.devices:
        device_list = [d.strip() for d in args.devices.split(",") if d.strip()]
        if not device_list:
            raise ValueError("--devices không được rỗng.")
    else:
        if not args.device_id.strip():
            raise ValueError("--device-id không được rỗng.")
        device_list = [args.device_id.strip()]

    queue_name = "sensor_data_queue"

    print("=" * 60)
    print("   IOT SENSOR PRODUCER - BÀI 2 AMQP (RABBITMQ)")
    print("=" * 60)
    print(f"[*] Hàng đợi đích  : {queue_name}")
    print(f"[*] Danh sách sensor: {', '.join(device_list)}")
    print(f"[*] Chu kỳ gửi      : {args.interval}s")
    print(f"[*] Số lần gửi      : {'Không giới hạn' if args.count == 0 else args.count}")
    print(f"[*] Trường mở rộng  : {'Có timestamp' if args.include_timestamp else 'Chuẩn đề bài (3 trường)'}")
    print("=" * 60)
    print("Nhấn Ctrl+C để dừng mô phỏng.\n", flush=True)

    # 1. Kết nối tới RabbitMQ broker
    with connect() as connection:
        channel = connection.channel()

        # 2. Khai báo queue sensor_data_queue (durable=True để bền vững)
        channel.queue_declare(queue=queue_name, durable=True)

        sent_cycles = 0
        device_index = 0

        while args.count == 0 or sent_cycles < args.count:
            # Chọn cảm biến (nếu có nhiều cảm biến, luân phiên gửi lần lượt)
            current_device = device_list[device_index % len(device_list)]
            device_index += 1

            # 3. Sinh giá trị ngẫu nhiên hoặc lấy giá trị cố định nếu chỉ định
            # Nhiệt độ môi trường trong khoảng [20.0, 40.0] °C
            temp = (
                args.temperature
                if args.temperature is not None
                else round(random.uniform(20.0, 40.0), 1)
            )
            # Độ ẩm môi trường trong khoảng [30.0, 80.0] %
            humi = (
                args.humidity
                if args.humidity is not None
                else round(random.uniform(30.0, 80.0), 1)
            )

            # 4. Đóng gói dữ liệu định dạng JSON theo đúng yêu cầu đề bài
            payload_data = {
                "device_id": current_device,
                "temperature": temp,
                "humidity": humi,
            }

            # Gợi ý mở rộng: bổ sung trường thời gian gửi
            if args.include_timestamp:
                payload_data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            message_body = json.dumps(payload_data, ensure_ascii=False)

            # 5. Gửi message vào queue sensor_data_queue qua default exchange ("")
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=message_body.encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
            )

            sent_cycles += 1
            print(f"[{sent_cycles:03d}] Da gui: {message_body}", flush=True)

            # 6. Chờ theo chu kỳ đã cấu hình (mặc định 3 giây)
            if args.count == 0 or sent_cycles < args.count:
                connection.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(run(main))
