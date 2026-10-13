"""Bài 1: nhận lời chào từ iot_lab_queue và in thời điểm nhận."""

from datetime import datetime

from amqp_common import connect, run


def on_message(channel, method, properties, body):
    print(f"Da nhan message: {body.decode('utf-8', errors='replace')}", flush=True)
    print(f"Thoi gian nhan: {datetime.now():%H:%M:%S}", flush=True)


def main():
    with connect() as connection:
        channel = connection.channel()
        channel.queue_declare(queue="iot_lab_queue", durable=True)
        channel.basic_consume(queue="iot_lab_queue", on_message_callback=on_message,
                              auto_ack=True)
        print("Dang lang nghe iot_lab_queue. Nhan Ctrl+C de dung.", flush=True)
        channel.start_consuming()


if __name__ == "__main__":
    raise SystemExit(run(main))
