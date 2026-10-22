"""Bài 2: cảm biến tự cập nhật mỗi 3 giây, cung cấp GET JSON."""

import asyncio
import math
import random

from aiocoap import resource

from coap_common import arguments, device_id, json_message, positive, run, serve


class SensorResource(resource.Resource):
    def __init__(self, identifier, temperature=None, humidity=None):
        super().__init__()
        self.identifier = identifier
        self.temperature = temperature
        self.humidity = humidity
        self.update()

    def update(self):
        self.data = {"device_id": self.identifier,
                     "temperature": self.temperature if self.temperature is not None else round(random.uniform(20, 40), 1),
                     "humidity": self.humidity if self.humidity is not None else round(random.uniform(30, 80), 1)}
        print(f"Sensor updated: {self.data}", flush=True)

    async def render_get(self, request):
        return json_message(self.data)


def setup(parser, config):
    parser.add_argument("--device-id", type=device_id, default="sensor01")
    parser.add_argument("--interval", type=positive, default=3)
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--humidity", type=float)


async def main():
    args = arguments(__doc__, setup)
    for value, low, high in ((args.temperature, 20, 40), (args.humidity, 30, 80)):
        if value is not None and (not math.isfinite(value) or not low <= value <= high):
            raise ValueError(f"Giá trị cảm biến phải trong khoảng {low}..{high}.")
    sensor = SensorResource(args.device_id, args.temperature, args.humidity)
    site = resource.Site()
    site.add_resource(["iot", "lab", args.device_id, "data"], sensor)

    async def update_loop():
        while True:
            await asyncio.sleep(args.interval)
            sensor.update()

    await serve(site, args, update_loop)


if __name__ == "__main__":
    raise SystemExit(run(main))
