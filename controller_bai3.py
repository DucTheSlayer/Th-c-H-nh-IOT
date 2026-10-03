"""Bài 3: nhập ON/OFF/EXIT và nhận phản hồi trạng thái thiết bị qua MQTT."""

import json
import queue
import time
from mqtt_common import Session, device_id, json_object, parse_args, parser_for, positive_float, run


def main():
    parser = parser_for(__doc__)
    parser.add_argument("--device-id", type=device_id, default="light01")
    parser.add_argument("--response-timeout", type=positive_float, default=5,
                        help="Thời gian chờ thiết bị phản hồi; mặc định 5 giây")
    args = parse_args(parser)
    cmd_topic = f"iot/lab/{args.device_id}/cmd"
    status_topic = f"iot/lab/{args.device_id}/status"
    responses = queue.Queue()

    def on_message(session, message):
        data = json_object(message.payload)
        if data.get("device_id") != args.device_id or data.get("status") not in ("ON", "OFF"):
            raise ValueError("Trạng thái thiết bị không hợp lệ.")
        label = "Trạng thái lưu trên broker" if message.retain else "Trang thai nhan duoc"
        print(f"\n{label}:\n{json.dumps(data, ensure_ascii=False)}", flush=True)
        if not message.retain:
            responses.put(data["status"])

    failed = False
    with Session(args, "controller-bai3", status_topic, on_message) as session:
        print("Nhập ON để bật, OFF để tắt, EXIT để thoát.", flush=True)
        while True:
            command = input("Nhap lenh: ").strip().upper()
            if command == "EXIT":
                break
            if command not in ("ON", "OFF"):
                print("Lệnh không hợp lệ. Chỉ nhập ON, OFF hoặc EXIT.", flush=True)
                continue
            while True:
                try:
                    responses.get_nowait()
                except queue.Empty:
                    break
            session.send(cmd_topic, command, retain=False)
            print(f"Da gui lenh {command} toi {args.device_id}", flush=True)
            deadline = time.monotonic() + args.response_timeout
            while True:
                remaining = deadline - time.monotonic()
                try:
                    if remaining <= 0:
                        raise queue.Empty
                    status = responses.get(timeout=remaining)
                except queue.Empty:
                    print("Chưa nhận được phản hồi mới; kiểm tra thiết bị và broker.", flush=True)
                    failed = True
                    break
                if status == command:
                    print(f"Thiết bị đã phản hồi trạng thái {status}.", flush=True)
                    break
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run(main))
