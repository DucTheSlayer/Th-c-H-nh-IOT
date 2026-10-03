"""Bài 2: giám sát dữ liệu cảm biến và cảnh báo theo ngưỡng của đề bài."""

import math
from mqtt_common import (Session, device_id, json_object, parse_args,
                         parser_for, receiver_options, run)


def on_message(session, message):
    data = json_object(message.payload)
    identifier = data["device_id"]
    if not isinstance(identifier, str) or message.topic != f"iot/lab/{identifier}/data":
        raise ValueError("device_id không khớp với topic.")
    for key in ("temperature", "humidity"):
        value = data[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{key} phải là số hữu hạn.")
    temperature, humidity = data["temperature"], data["humidity"]
    if not -40 <= temperature <= 80 or not 0 <= humidity <= 100:
        raise ValueError("Giá trị cảm biến nằm ngoài khoảng mô phỏng.")
    print(f"\nDevice: {identifier}\nTemperature: {temperature:.1f} C"
          f"\nHumidity: {humidity:.1f} %", flush=True)
    if temperature > 35:
        print("CANH BAO: Nhiet do cao", flush=True)
    if humidity < 40:
        print("CANH BAO: Do am thap", flush=True)


def main():
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="sensor01")
    parser.add_argument("--all-devices", action="store_true", help="Subscribe iot/lab/+/data")
    receiver_options(parser)
    args = parse_args(parser)
    topic = "iot/lab/+/data" if args.all_devices else f"iot/lab/{args.device_id}/data"
    with Session(args, "monitor-bai2", topic, on_message) as session:
        session.listen()


if __name__ == "__main__":
    raise SystemExit(run(main))
