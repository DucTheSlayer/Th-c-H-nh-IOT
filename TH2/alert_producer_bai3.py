"""Bài 3: gửi ba mức cảnh báo qua direct exchange iot_alert_exchange."""

import pika

from amqp_common import connect, run

EXCHANGE_NAME = "iot_alert_exchange"

ALERTS = [
    ("info", "He thong giam sat IoT dang hoat dong binh thuong"),
    ("warning", "Nhiet do phong may vuot nguong warning"),
    ("critical", "Cam bien kho lanh mat ket noi critical"),
]


def main():
    with connect() as connection:
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct")
        for level, message in ALERTS:
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=level,
                body=message.encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="text/plain",
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
            )
            print(f"Da gui [{level}]: {message}", flush=True)


if __name__ == "__main__":
    raise SystemExit(run(main))
