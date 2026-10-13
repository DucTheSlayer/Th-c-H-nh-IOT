"""Broker MQTT cục bộ cho thực hành, chỉ lắng nghe trên 127.0.0.1."""

import argparse
import asyncio
import logging
import sys

from amqtt.broker import Broker


async def serve(port):
    broker = Broker({
        "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}},
        "plugins": {
            "amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True},
        },
    })
    await broker.start()
    print(f"BROKER READY 127.0.0.1:{port}", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Cổng phải từ 1 đến 65535.")
    logging.basicConfig(level=logging.ERROR)
    try:
        asyncio.run(serve(args.port))
    except KeyboardInterrupt:
        print("\nĐã dừng broker.")
    except (OSError, RuntimeError) as error:
        print(f"Lỗi broker: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
