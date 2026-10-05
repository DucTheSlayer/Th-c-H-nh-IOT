"""Bài 2: Ứng dụng giám sát (Monitoring Subscriber) dữ liệu cảm biến qua MQTT.

- Đăng ký lắng nghe (Subscribe):
    + Topic đơn lẻ: iot/lab/sensor01/data (hoặc --device-id)
    + Mở rộng đa thiết bị: iot/lab/+/data (sử dụng cờ --all-devices)
- Nhận và giải mã JSON payload:
    + device_id (chuỗi)
    + temperature (số thực °C)
    + humidity (số thực %)
- Kiểm tra ngưỡng và cảnh báo theo yêu cầu:
    + Nếu nhiệt độ > 35°C  -> In: "CANH BAO: Nhiet do cao"
    + Nếu độ ẩm < 40%     -> In: "CANH BAO: Do am thap"
"""

import math
from mqtt_common import (
    Session,
    device_id,
    json_object,
    parse_args,
    parser_for,
    receiver_options,
    run,
)


def on_message(session, message):
    """Callback xử lý mỗi khi có bản tin mới từ MQTT Broker."""
    # 1. Giải mã payload từ dạng bytes sang dict (JSON object)
    data = json_object(message.payload)

    # 2. Xác thực tính toàn vẹn của dữ liệu: device_id phải khớp với topic
    identifier = data["device_id"]
    if not isinstance(identifier, str) or message.topic != f"iot/lab/{identifier}/data":
        raise ValueError("device_id không khớp với topic.")

    # 3. Xác thực kiểu dữ liệu của nhiệt độ và độ ẩm
    for key in ("temperature", "humidity"):
        value = data[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{key} phải là số hữu hạn.")

    temperature = data["temperature"]
    humidity = data["humidity"]

    # 4. Kiểm tra giới hạn vật lý hợp lý
    if not -40 <= temperature <= 80 or not 0 <= humidity <= 100:
        raise ValueError("Giá trị cảm biến nằm ngoài khoảng mô phỏng.")

    # 5. In thông tin ra màn hình theo đúng định dạng mẫu yêu cầu
    print(
        f"\nDevice: {identifier}\nTemperature: {temperature:.1f} C\nHumidity: {humidity:.1f} %",
        flush=True,
    )

    # 6. Kiểm tra ngưỡng và hiển thị cảnh báo độc lập
    if temperature > 35:
        print("CANH BAO: Nhiet do cao", flush=True)
    if humidity < 40:
        print("CANH BAO: Do am thap", flush=True)


def main():
    # Khởi tạo parser nhận tham số dòng lệnh
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="sensor01",
                        help="ID của cảm biến cần giám sát (mặc định: sensor01)")
    parser.add_argument("--all-devices", action="store_true",
                        help="Lắng nghe dữ liệu của tất cả cảm biến (topic: iot/lab/+/data)")
    receiver_options(parser)
    args = parse_args(parser)

    # Xác định topic đăng ký: wildcard '+' nếu giám sát toàn bộ hoặc topic cụ thể
    topic = "iot/lab/+/data" if args.all_devices else f"iot/lab/{args.device_id}/data"

    # Mở phiên kết nối và lắng nghe dữ liệu
    with Session(args, "monitor-bai2", topic, on_message) as session:
        session.listen()


if __name__ == "__main__":
    raise SystemExit(run(main))
