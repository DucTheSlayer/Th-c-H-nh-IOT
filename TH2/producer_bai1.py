"""Bài 1: gửi lời chào, mã sinh viên và họ tên vào iot_lab_queue."""

import argparse

from amqp_common import connect, load_config, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Họ tên sinh viên")
    parser.add_argument("--student-id", help="Mã sinh viên")
    parser.add_argument("--count", type=int, default=1, help="Số message gửi")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count phải lớn hơn hoặc bằng 1")

    config = load_config()
    name = (args.name or config["student_name"] or input("Họ tên: ")).strip()
    student_id = (args.student_id or config["student_id"] or input("Mã sinh viên: ")).strip()
    if not name or not student_id:
        raise ValueError("Cần điền đầy đủ họ tên và mã sinh viên")
    message = f"Xin chao tu ung dung Python AMQP - {student_id} - {name}"

    with connect(config) as connection:
        channel = connection.channel()
        channel.queue_declare(queue="iot_lab_queue", durable=True)
        for index in range(args.count):
            channel.basic_publish(exchange="", routing_key="iot_lab_queue",
                                  body=message.encode("utf-8"))
            print(f"Da gui [{index + 1}]: {message}", flush=True)


if __name__ == "__main__":
    raise SystemExit(run(main))
