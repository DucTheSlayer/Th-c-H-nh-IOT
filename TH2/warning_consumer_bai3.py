"""Bài 3: warning_queue chỉ nhận routing key warning."""

from amqp_common import connect, run


def on_message(channel, method, properties, body):
    print(f"[warning_queue] Da nhan: {body.decode('utf-8', errors='replace')}", flush=True)


def main():
    with connect() as connection:
        channel = connection.channel()
        channel.exchange_declare(exchange="iot_alert_exchange", exchange_type="direct")
        channel.queue_declare(queue="warning_queue", durable=True)
        channel.queue_bind(exchange="iot_alert_exchange", queue="warning_queue",
                           routing_key="warning")
        channel.basic_consume(queue="warning_queue", on_message_callback=on_message,
                              auto_ack=True)
        print("Dang lang nghe warning_queue. Nhan Ctrl+C de dung.", flush=True)
        channel.start_consuming()


if __name__ == "__main__":
    raise SystemExit(run(main))
