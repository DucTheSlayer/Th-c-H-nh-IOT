"""Bài 3: đăng ký Observe một lần, nhận thông báo từ server."""

import asyncio

import aiocoap

from coap_common import (arguments, client_context, device_id, nonnegative,
                         run, show_state, uri)


def setup(parser, config):
    parser.add_argument("--device-id", type=device_id, default="light01")
    parser.add_argument("--max-notifications", type=nonnegative, default=0,
                        help="Số trạng thái nhận, gồm ban đầu; 0: đến Ctrl+C")


async def main():
    args = arguments(__doc__, setup)
    context = await client_context()
    pending = None
    try:
        message = aiocoap.Message(code=aiocoap.GET,
                                  uri=uri(args, f"iot/lab/{args.device_id}/status"), observe=0)
        print("Registering CoAP Observe...", flush=True)
        pending = context.request(message)
        initial = await asyncio.wait_for(pending.response, args.timeout)
        show_state(initial, args.device_id, "Initial State")
        if initial.opt.observe is None:
            raise ValueError("Server không chấp nhận CoAP Observe.")
        print("Observe registration successful", flush=True)
        received = 1
        if args.max_notifications == 1:
            return
        # Không gửi GET định kỳ. Iterator chờ thông báo Observe từ server.
        async for response in pending.observation:
            show_state(response, args.device_id, "State Updated")
            received += 1
            if args.max_notifications and received >= args.max_notifications:
                break
        else:
            raise ValueError("Server đã kết thúc đăng ký Observe.")
    finally:
        if pending and pending.observation and not pending.observation.cancelled:
            pending.observation.cancel()
        await context.shutdown()


if __name__ == "__main__":
    raise SystemExit(run(main))
