"""Bài 3: gửi ba mức cảnh báo qua direct exchange iot_alert_exchange."""

from amqp_common import connect, run


def main():
    alerts = [
        ("info", "He thong giam sat IoT dang hoat dong binh thuong"),
        ("warning", "Nhiet do phong may vuot nguong warning"),
        ("critical", "Cam bien kho lanh mat ket noi critical"),
    ]
    with connect() as connection:
        channel = connection.channel()
        channel.exchange_declare(exchange="iot_alert_exchange", exchange_type="direct")
        for level, message in alerts:
            channel.basic_publish(exchange="iot_alert_exchange", routing_key=level,
                                  body=message.encode("utf-8"))
            print(f"Da gui [{level}]: {message}", flush=True)


if __name__ == "__main__":
    raise SystemExit(run(main))
