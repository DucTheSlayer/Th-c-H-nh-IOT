"""Cấu hình và kết nối MQTT dùng chung cho sáu chương trình thực hành."""

import argparse
import json
import math
import re
import sys
import threading
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Giá trị phải là số hữu hạn lớn hơn 0.")
    return number


def nonnegative_int(value):
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("Giá trị phải lớn hơn hoặc bằng 0.")
    return number


def device_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("device_id chỉ gồm chữ, số, _ hoặc -.")
    return value


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError("Giá trị phải là số hữu hạn.")
    return number


def parser_for(description):
    # UTF-8 cho terminal Windows và khi chuyển hướng đầu ra sang file.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--host", help="Địa chỉ broker; mặc định 127.0.0.1")
    parser.add_argument("--port", type=int, help="Cổng broker; mặc định 1883")
    parser.add_argument("--username", help="Tên đăng nhập broker")
    parser.add_argument("--password", help="Mật khẩu broker (nên lưu ở config.json)")
    parser.add_argument("--tls", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--ca-cert", help="File chứng chỉ CA cho TLS")
    parser.add_argument("--timeout", type=positive_float, help="Thời gian chờ kết nối/ACK (giây)")
    return parser


def parse_args(parser):
    args = parser.parse_args()
    config = {}
    if args.config.exists():
        try:
            config = json.loads(args.config.read_text(encoding="utf-8-sig"))
            if not isinstance(config, dict):
                raise ValueError("Cấu hình phải là một JSON object.")
        except (OSError, ValueError) as error:
            parser.error(f"Không đọc được {args.config}: {error}")
    elif "--config" in sys.argv or any(a.startswith("--config=") for a in sys.argv):
        parser.error(f"Không tìm thấy file cấu hình: {args.config}")
    defaults = dict(host="127.0.0.1", port=1883, username="", password="",
                    tls=False, ca_cert=None, timeout=10)
    for key, default in defaults.items():
        if getattr(args, key) is None:
            setattr(args, key, config.get(key, default))
    if not isinstance(args.host, str) or not args.host.strip():
        parser.error("host phải là địa chỉ broker không rỗng.")
    if type(args.port) is not int or not 1 <= args.port <= 65535:
        parser.error("port phải là số nguyên từ 1 đến 65535.")
    if type(args.tls) is not bool:
        parser.error("tls phải là true hoặc false.")
    if not isinstance(args.timeout, (int, float)) or isinstance(args.timeout, bool):
        parser.error("timeout phải là số lớn hơn 0.")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout phải là số hữu hạn lớn hơn 0.")
    for key in ("username", "password"):
        if not isinstance(getattr(args, key), str):
            parser.error(f"{key} phải là chuỗi.")
    if args.ca_cert is not None and not isinstance(args.ca_cert, str):
        parser.error("ca_cert phải là đường dẫn dạng chuỗi hoặc null.")
    if args.ca_cert and not args.tls:
        parser.error("Cần bật --tls khi dùng --ca-cert.")
    args.student_name = config.get("student_name", "")
    args.config_student_id = config.get("student_id", "")
    if not isinstance(args.student_name, str) or not isinstance(args.config_student_id, str):
        parser.error("student_name và student_id trong cấu hình phải là chuỗi.")
    return args


def receiver_options(parser):
    parser.add_argument("--max-messages", type=nonnegative_int, default=0,
                        help="Dừng sau N bản tin hợp lệ; 0 = chạy đến Ctrl+C")
    parser.add_argument("--duration", type=positive_float,
                        help="Tự dừng sau N giây; mặc định chạy liên tục")


def json_object(payload):
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Payload phải là JSON object.")
    return data


class Session:
    """loop_start nhận bản tin trên luồng riêng; luồng chính vẫn nhập/gửi được."""

    def __init__(self, args, role, topic=None, on_message=None, on_ready=None):
        self.args = args
        self.topic = topic
        self.handler = on_message
        self.ready_handler = on_ready
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.failure = None
        self.received = 0
        self.pending = []
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"{role}-{uuid.uuid4().hex[:12]}",
                                  protocol=mqtt.MQTTv311)
        if args.username:
            self.client.username_pw_set(args.username, args.password)
        if args.tls:
            self.client.tls_set(ca_certs=args.ca_cert)
        self.client.connect_timeout = args.timeout
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)
        self.client.on_connect = self._on_connect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _fail(self, text):
        self.failure = text
        self.ready.set()
        self.stop.set()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self._fail(f"Broker từ chối kết nối: {reason_code}")
            return
        print(f"Đã kết nối broker {self.args.host}:{self.args.port}", flush=True)
        if self.topic:
            result, _ = client.subscribe(self.topic, qos=1)
            if result != mqtt.MQTT_ERR_SUCCESS:
                self._fail(f"Không subscribe được {self.topic}: {result}")
        else:
            self.ready.set()

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        if any(code.is_failure for code in reason_codes):
            self._fail(f"Broker từ chối subscribe {self.topic}")
            return
        # Chỉ báo sẵn sàng khi broker xác nhận SUBACK, tránh bỏ lỡ bản tin đầu.
        print(f"Đã subscribe: {self.topic}", flush=True)
        if self.ready_handler:
            try:
                self.ready_handler(self)
            except (OSError, RuntimeError, ValueError) as error:
                self._fail(str(error))
                return
        self.ready.set()

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.ready.clear()
        if reason_code.is_failure:
            print("Mất kết nối broker, đang kết nối lại...", flush=True)

    def _on_message(self, client, userdata, message):
        try:
            accepted = self.handler(self, message)
        except (ValueError, UnicodeError, TypeError, KeyError) as error:
            print(f"Bỏ qua dữ liệu không hợp lệ trên {message.topic}: {error}", flush=True)
            return
        except (OSError, RuntimeError) as error:
            self._fail(str(error))
            return
        if accepted is False:
            return
        self.received += 1
        limit = getattr(self.args, "max_messages", 0)
        if limit and self.received >= limit:
            self.stop.set()

    def __enter__(self):
        try:
            self.client.connect(self.args.host, self.args.port, keepalive=60)
            self.client.loop_start()
            if not self.ready.wait(self.args.timeout):
                raise TimeoutError("Hết thời gian chờ kết nối hoặc SUBACK.")
            if self.failure:
                raise RuntimeError(self.failure)
            return self
        except BaseException:
            self.client.disconnect()
            self.client.loop_stop()
            raise

    def send(self, topic, payload, *, retain=False, wait=True):
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        info = self.client.publish(topic, payload, qos=1, retain=retain)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Publish thất bại: {mqtt.error_string(info.rc)}")
        if wait:
            self._wait_publish(info)
        else:
            # Không chờ ACK trong callback: callback chạy trên chính luồng mạng.
            self.pending = [item for item in self.pending if not item.is_published()]
            self.pending.append(info)

    def _wait_publish(self, info):
        info.wait_for_publish(timeout=self.args.timeout)
        if not info.is_published():
            raise TimeoutError("Broker chưa xác nhận publish trong thời gian cho phép.")

    def listen(self):
        print("Đang lắng nghe. Nhấn Ctrl+C để dừng.", flush=True)
        self.stop.wait(getattr(self.args, "duration", None))
        if self.failure:
            raise RuntimeError(self.failure)

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                for info in self.pending:
                    self._wait_publish(info)
        finally:
            self.client.disconnect()
            self.client.loop_stop()


def run(main):
    try:
        result = main()
        return result or 0
    except (KeyboardInterrupt, EOFError):
        print("\nĐã dừng chương trình.", flush=True)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Lỗi: {error}", file=sys.stderr, flush=True)
        return 1
