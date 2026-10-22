"""Bài 1: GET lời chào rồi POST thông tin sinh viên."""

import aiocoap

from coap_common import (arguments, client_context, nonnegative, request,
                         require_success, run, show_response, uri)

PATH = "iot/lab/message"


def setup(parser, config):
    parser.add_argument("--name", default=config["student_name"])
    parser.add_argument("--student-id", default=config["student_id"])
    parser.add_argument("--count", type=nonnegative, default=1)


async def main():
    args = arguments(__doc__, setup)
    name = (args.name or input("Họ tên sinh viên: ")).strip()
    student = (args.student_id or input("Mã sinh viên: ")).strip()
    if not name or not student:
        raise ValueError("Cần nhập đủ họ tên và mã sinh viên.")
    if args.count < 1:
        raise ValueError("--count phải >= 1.")
    context = await client_context()
    try:
        print(f"Sending GET request...\nURI: {uri(args, PATH)}", flush=True)
        response = await request(context, args, aiocoap.GET, PATH)
        show_response(response)
        require_success(response)
        for _ in range(args.count):
            payload = f"Xin chao tu CoAP Client - {student} - {name}"
            print(f"Sending POST request...\nPayload: {payload}", flush=True)
            response = await request(context, args, aiocoap.POST, PATH, payload.encode("utf-8"), 0)
            show_response(response)
            require_success(response)
    finally:
        await context.shutdown()


if __name__ == "__main__":
    raise SystemExit(run(main))
