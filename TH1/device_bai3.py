"""Bài 3: thiết bị nhận ON/OFF qua MQTT và phản hồi trạng thái JSON."""

from mqtt_common import (Session, device_id, parse_args, parser_for,
                         receiver_options, run)


VALID_STATES = ("ON", "OFF")
INITIAL_STATE = "OFF"


def command_topic(identifier):
    return f"iot/lab/{identifier}/cmd"


def status_topic(identifier):
    return f"iot/lab/{identifier}/status"


def normalize_command(payload):
    return payload.decode("utf-8").strip().upper()


def status_payload(identifier, state):
    return {"device_id": identifier, "status": state}


def main():
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="light01")
    receiver_options(parser)
    args = parse_args(parser)
    cmd_topic = command_topic(args.device_id)
    state_topic = status_topic(args.device_id)
    state = INITIAL_STATE

    def on_message(session, message):
        nonlocal state
        # Lệnh không retain; bỏ qua lệnh cũ lưu trên broker nếu có.
        if message.retain:
            print("Bỏ qua lệnh retained cũ.", flush=True)
            return False
        command = normalize_command(message.payload)
        if command not in VALID_STATES:
            print(f"Lệnh không hợp lệ: {command!r}; chỉ nhận ON hoặc OFF.", flush=True)
            return False
        state = command
        payload = status_payload(args.device_id, state)
        session.send(state_topic, payload, retain=True, wait=False)
        print(f"Thiết bị {args.device_id}: {'BẬT' if state == 'ON' else 'TẮT'}"
              f" | Đã gửi trạng thái: {payload}", flush=True)

    with Session(args, "device-bai3", cmd_topic, on_message) as session:
        session.send(state_topic, status_payload(args.device_id, state), retain=True)
        print(f"Trạng thái ban đầu của {args.device_id}: {state}", flush=True)
        try:
            session.listen()
        finally:
            session.send(state_topic, "", retain=True)


if __name__ == "__main__":
    raise SystemExit(run(main))

