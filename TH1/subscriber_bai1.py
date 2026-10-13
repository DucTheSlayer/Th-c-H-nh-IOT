"""Bài 1: nhận lời chào MQTT, hiển thị topic, payload và thời điểm nhận."""

from datetime import datetime
from mqtt_common import Session, parse_args, parser_for, receiver_options, run

TOPIC = "iot/lab/message"


def on_message(session, message):
    payload = message.payload.decode("utf-8")
    print(f"\nNhan duoc message:\nTopic: {message.topic}\nPayload: {payload}"
          f"\nTime: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}", flush=True)


def main():
    parser = parser_for(__doc__)
    receiver_options(parser)
    args = parse_args(parser)
    with Session(args, "subscriber-bai1", TOPIC, on_message) as session:
        session.listen()


if __name__ == "__main__":
    raise SystemExit(run(main))
