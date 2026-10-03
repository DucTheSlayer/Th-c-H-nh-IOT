"""Bài 3: thiết bị nhận ON/OFF qua MQTT và phản hồi trạng thái JSON."""

from mqtt_common import (Session, device_id, parse_args, parser_for,
                         receiver_options, run)


def main():
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="light01")
    receiver_options(parser)
    args = parse_args(parser)
    cmd_topic = f"iot/lab/{args.device_id}/cmd"
    status_topic = f"iot/lab/{args.device_id}/status"
    state = "OFF"

    def on_message(session, message):
        nonlocal state
        # Lệnh không retain; bỏ qua lệnh cũ lưu trên broker nếu có.
        if message.retain:
            print("Bỏ qua lệnh retained cũ.", flush=True)
            return False
        command = message.payload.decode("utf-8").strip().upper()
        if command not in ("ON", "OFF"):
            print(f"Lệnh không hợp lệ: {command!r}; chỉ nhận ON hoặc OFF.", flush=True)
            return False
        state = command
        payload = {"device_id": args.device_id, "status": state}
        session.send(status_topic, payload, retain=True, wait=False)
        print(f"Thiết bị {args.device_id}: {'BẬT' if state == 'ON' else 'TẮT'}"
              f" | Đã gửi trạng thái: {payload}", flush=True)

    def on_ready(session):
        session.send(status_topic, {"device_id": args.device_id, "status": state},
                     retain=True, wait=False)

    with Session(args, "device-bai3", cmd_topic, on_message, on_ready) as session:
        print(f"Trạng thái ban đầu của {args.device_id}: {state}", flush=True)
        session.listen()


if __name__ == "__main__":
    raise SystemExit(run(main))
