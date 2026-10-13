"""Bài 2: nhận JSON cảm biến và cảnh báo nhiệt độ cao, độ ẩm thấp."""

import json
import math

from amqp_common import connect, run


def on_message(channel, method, properties, body):
    try:
        data = json.loads(body.decode("utf-8"))
        device_id = data["device_id"]
        temperature = data["temperature"]
        humidity = data["humidity"]
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id phải là chuỗi không trống")
        for value in (temperature, humidity):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("temperature và humidity phải là số hữu hạn")
    except (ValueError, KeyError, TypeError) as error:
        print(f"Bo qua du lieu khong hop le: {error}", flush=True)
        return

    print(f"Device: {device_id}", flush=True)
    print(f"Temperature: {temperature}", flush=True)
    print(f"Humidity: {humidity}", flush=True)
    if temperature > 35:
        print("CANH BAO: Nhiet do cao", flush=True)
    if humidity < 40:
        print("CANH BAO: Do am thap", flush=True)
    print(flush=True)


def main():
    with connect() as connection:
        channel = connection.channel()
        channel.queue_declare(queue="sensor_data_queue", durable=True)
        channel.basic_consume(queue="sensor_data_queue", on_message_callback=on_message,
                              auto_ack=True)
        print("Dang lang nghe sensor_data_queue. Nhan Ctrl+C de dung.", flush=True)
        channel.start_consuming()


if __name__ == "__main__":
    raise SystemExit(run(main))
