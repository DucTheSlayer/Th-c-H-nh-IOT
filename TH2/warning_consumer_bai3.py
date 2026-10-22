"""Bài 3: warning_queue chỉ nhận routing key warning."""

from amqp_common import connect, run

EXCHANGE_NAME = "iot_alert_exchange"
QUEUE_NAME = "warning_queue"
ROUTING_KEY = "warning"


def on_message(channel, method, properties, body):
    message = body.decode("utf-8", errors="replace")
    print(f"[{QUEUE_NAME}] Da nhan: {message}", flush=True)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    with connect() as connection:
        channel = connection.channel()
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct")
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
        print(f"Dang lang nghe {QUEUE_NAME}. Nhan Ctrl+C de dung.", flush=True)
        channel.start_consuming()


if __name__ == "__main__":
    raise SystemExit(run(main))
