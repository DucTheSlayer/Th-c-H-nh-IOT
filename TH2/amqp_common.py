"""Cấu hình và kết nối RabbitMQ dùng chung cho các bài TH2."""

import json
from pathlib import Path
import sys

import pika


def load_config():
    config = {
        "host": "127.0.0.1", "port": 5672,
        "username": "guest", "password": "guest", "virtual_host": "/",
        "student_name": "", "student_id": "",
    }
    path = Path(__file__).with_name("config.json")
    if path.exists():
        with path.open(encoding="utf-8-sig") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("config.json phải chứa một đối tượng JSON.")
        config.update(data)
    return config


def connect(config=None):
    if config is None:
        config = load_config()
    parameters = pika.ConnectionParameters(
        host=config["host"], port=int(config["port"]),
        virtual_host=config["virtual_host"],
        credentials=pika.PlainCredentials(config["username"], config["password"]),
        heartbeat=60, socket_timeout=5, blocked_connection_timeout=10,
    )
    return pika.BlockingConnection(parameters)


def run(main):
    # Giữ tiếng Việt đọc được cả khi đầu ra bị chuyển hướng trên Windows.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")
    except (pika.exceptions.AMQPError, OSError, ValueError, TypeError) as error:
        detail = str(error) or type(error).__name__
        print(f"Lỗi: {detail}. Kiểm tra RabbitMQ và config.json.", file=sys.stderr)
        return 1
    return 0
