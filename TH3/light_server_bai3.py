"""Bài 3: tài nguyên đèn GET/PUT và CoAP Observe."""

import json

import aiocoap
from aiocoap import resource

from coap_common import arguments, device_id, json_message, run, serve


class LightResource(resource.ObservableResource):
    def __init__(self, identifier="light01"):
        super().__init__()
        self.identifier = identifier
        self.status = "OFF"

    def update_observation_count(self, newcount):
        print(f"Observe clients: {newcount}", flush=True)

    async def render_get(self, request):
        return json_message({"device_id": self.identifier, "status": self.status})

    async def render_put(self, request):
        if request.opt.content_format != 50:
            return aiocoap.Message(code=aiocoap.UNSUPPORTED_CONTENT_FORMAT,
                                   payload=b"Can Content-Format application/json (50)")
        try:
            data = json.loads(request.payload.decode("utf-8"))
            if not isinstance(data, dict) or data.get("device_id") != self.identifier or data.get("command") not in ("ON", "OFF"):
                raise ValueError("Sai device_id hoac command (ON/OFF)")
        except (ValueError, UnicodeDecodeError) as error:
            return aiocoap.Message(code=aiocoap.BAD_REQUEST, payload=str(error).encode("utf-8"))
        previous = self.status
        self.status = data["command"]
        print(f"PUT request received: Device: {self.identifier}, Command: {self.status}", flush=True)
        if previous != self.status:
            print(f"Light state changed: {previous} -> {self.status}\nNotify observers: {self.status}", flush=True)
            self.updated_state()
        return json_message({"device_id": self.identifier, "status": self.status}, aiocoap.CHANGED)


def setup(parser, config):
    parser.add_argument("--device-id", type=device_id, default="light01")


async def main():
    args = arguments(__doc__, setup)
    site = resource.Site()
    site.add_resource(["iot", "lab", args.device_id, "status"], LightResource(args.device_id))
    await serve(site, args)


if __name__ == "__main__":
    raise SystemExit(run(main))
