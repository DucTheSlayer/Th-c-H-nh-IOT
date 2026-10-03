"""Bài 1: gửi lời chào, họ tên và mã sinh viên lên iot/lab/message."""

import time
from mqtt_common import Session, nonnegative_int, parse_args, parser_for, positive_float, run

TOPIC = "iot/lab/message"


def main():
    parser = parser_for(__doc__)
    parser.add_argument("--name", help="Họ tên sinh viên")
    parser.add_argument("--student-id", help="Mã sinh viên")
    parser.add_argument("--message", default="Xin chao tu client Python MQTT")
    parser.add_argument("--count", type=nonnegative_int, default=1,
                        help="Số lần gửi, mặc định 1; 0 = gửi liên tục")
    parser.add_argument("--interval", type=positive_float, default=3)
    args = parse_args(parser)
    name = args.name or args.student_name or input("Nhập họ tên sinh viên: ")
    if not name.strip():
        parser.error("Họ tên không được rỗng.")
    student_id = args.student_id or args.config_student_id or input("Nhập mã sinh viên: ")
    if not student_id.strip() or not args.message.strip():
        parser.error("Mã sinh viên và lời chào không được rỗng.")
    payload = f"{args.message.strip()} - {student_id.strip()} - {name.strip()}"
    with Session(args, "publisher-bai1") as session:
        sent = 0
        while args.count == 0 or sent < args.count:
            session.send(TOPIC, payload)
            sent += 1
            print(f"Đã gửi [{sent}] | Topic: {TOPIC} | Payload: {payload}", flush=True)
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(run(main))
