"""
BUỔI THỰC HÀNH: LẬP TRÌNH PYTHON VỚI GIAO THỨC AMQP
Bài 2: Hệ thống giám sát dữ liệu cảm biến (Monitoring Consumer)

Yêu cầu:
- Nhận dữ liệu telemetry từ queue: sensor_data_queue.
- Phân tích JSON và in ra màn hình:
  + Mã thiết bị (Device)
  + Nhiệt độ (Temperature)
  + Độ ẩm (Humidity)
- Kiểm tra ngưỡng và cảnh báo:
  + Nếu nhiệt độ > 35: Cảnh báo "CANH BAO: Nhiet do cao"
  + Nếu độ ẩm < 40   : Cảnh báo "CANH BAO: Do am thap"
- Định dạng đầu ra mẫu:
  Device: sensor01
  Temperature: 36.4
  Humidity: 38.9
  CANH BAO: Nhiet do cao
  CANH BAO: Do am thap
"""

import json
import math

from amqp_common import connect, run


def on_message(channel, method, properties, body):
    """Callback xử lý mỗi khi nhận được một message từ sensor_data_queue."""
    # 1. Giải mã message nhận được từ UTF-8 và parse JSON
    try:
        raw_text = body.decode("utf-8")
        data = json.loads(raw_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        print(f"[!] Bo qua ban tin khong hop le (loi giai ma JSON): {err}", flush=True)
        return

    # 2. Kiểm tra tính toàn vẹn và hợp lệ của các trường dữ liệu
    try:
        device_id = data["device_id"]
        temperature = data["temperature"]
        humidity = data["humidity"]

        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("Trường 'device_id' phải là chuỗi ký tự không rỗng.")

        for val, name in [(temperature, "temperature"), (humidity, "humidity")]:
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f"Trường '{name}' phải là số hữu hạn.")
    except (KeyError, ValueError, TypeError) as err:
        print(f"[!] Bo qua ban tin khong hop le ve cau truc: {err}", flush=True)
        return

    # 3. Hiển thị thông tin theo đúng định dạng mẫu yêu cầu
    print("-" * 35, flush=True)
    print(f"Device: {device_id}", flush=True)
    print(f"Temperature: {temperature}", flush=True)
    print(f"Humidity: {humidity}", flush=True)

    # Hiển thị trường mở rộng thời gian gửi nếu có
    if "timestamp" in data:
        print(f"Timestamp: {data['timestamp']}", flush=True)

    # 4. Kiểm tra ngưỡng và hiển thị cảnh báo độc lập
    if temperature > 35:
        print("CANH BAO: Nhiet do cao", flush=True)
    if humidity < 40:
        print("CANH BAO: Do am thap", flush=True)
    print("-" * 35, flush=True)


def main():
    queue_name = "sensor_data_queue"

    print("=" * 60)
    print("   IOT MONITORING CONSUMER - BÀI 2 AMQP (RABBITMQ)")
    print("=" * 60)
    print("[*] Dang ket noi toi RabbitMQ broker...")
    print(f"[*] Lang nghe queue: {queue_name}")
    print("[*] Nhan Ctrl+C de dung chuong trinh.")
    print("=" * 60, flush=True)

    # 1. Kết nối tới RabbitMQ broker
    with connect() as connection:
        channel = connection.channel()

        # 2. Khai báo queue sensor_data_queue (durable=True để đồng bộ với producer)
        channel.queue_declare(queue=queue_name, durable=True)

        # 3. Đăng ký hàm nhận tin nhắn callback
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=True,
        )

        print(f"[*] San sang nhan du lieu tu {queue_name}...\n", flush=True)

        # 4. Bắt đầu lắng nghe liên tục cho đến khi ngắt
        channel.start_consuming()


if __name__ == "__main__":
    raise SystemExit(run(main))
