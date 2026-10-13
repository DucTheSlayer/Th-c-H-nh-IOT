"""Bài 3: critical_queue chỉ nhận routing key critical."""

from amqp_common import connect, run


def on_message(channel, method, properties, body):
    print(f"[critical_queue] Da nhan: {body.decode('utf-8', errors='replace')}", flush=True)


def main():
    with connect() as connection:
        channel = connection.channel()
        channel.exchange_declare(exchange="iot_alert_exchange", exchange_type="direct")
        channel.queue_declare(queue="critical_queue", durable=True)
        channel.queue_bind(exchange="iot_alert_exchange", queue="critical_queue",
                           routing_key="critical")
        channel.basic_consume(queue="critical_queue", on_message_callback=on_message,
                              auto_ack=True)
        print("Dang lang nghe critical_queue. Nhan Ctrl+C de dung.", flush=True)
        channel.start_consuming()


if __name__ == "__main__":
    raise SystemExit(run(main))
