"""Bài 1: tài nguyên GET/POST và lưu thông điệp gần nhất."""

import aiocoap
from aiocoap import resource

from coap_common import arguments, now, run, serve

PATH = "iot/lab/message"


class MessageResource(resource.Resource):
    def __init__(self):
        super().__init__()
        self.message = "Xin chao tu CoAP Server"

    async def render_get(self, request):
        print(f"GET request received: /{PATH}", flush=True)
        return aiocoap.Message(code=aiocoap.CONTENT, payload=self.message.encode("utf-8"), content_format=0)

    async def render_post(self, request):
        try:
            message = request.payload.decode("utf-8")
        except UnicodeDecodeError:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=b"Payload phai la UTF-8")
        if not message.strip():
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=b"Thong diep rong")
        self.message = message
        print(f"POST request received:\nPayload: {message}\nTime: {now()}", flush=True)
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"Server da nhan thong diep", content_format=0)


async def main():
    args = arguments(__doc__)
    site = resource.Site()
    site.add_resource(PATH.split("/"), MessageResource())
    await serve(site, args)


if __name__ == "__main__":
    raise SystemExit(run(main))
