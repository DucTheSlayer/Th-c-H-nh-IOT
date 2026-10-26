"""
BUỔI THỰC HÀNH: LẬP TRÌNH PYTHON VỚI GIAO THỨC COAP
Bài 2: Mô phỏng cảm biến nhiệt độ và độ ẩm bằng CoAP (Sensor CoAP Server)

Mục tiêu:
- Mô phỏng thiết bị cảm biến nhiệt độ và độ ẩm cung cấp dữ liệu qua CoAP.
- Cung cấp tài nguyên: coap://<host>:<port>/iot/lab/<device_id>/data (mặc định: sensor01).
- Tự động cập nhật dữ liệu cảm biến sau mỗi 3 giây (độc lập với yêu cầu GET của Client).
- Nhiệt độ sinh ngẫu nhiên 20–40 °C, độ ẩm 30–80 %, làm tròn 1 chữ số thập phân.
- Hỗ trợ phương thức GET để Client truy vấn dữ liệu cảm biến hiện tại.
- Dữ liệu trả về ở định dạng JSON với Content-Format application/json (50):
  {"device_id": "sensor01", "temperature": 28.5, "humidity": 65.2}

Gợi ý mở rộng:
- Bổ sung trường timestamp trong JSON payload qua cờ --include-timestamp.
- Mô phỏng đồng thời 2 hoặc 3 cảm biến (sensor01, sensor02, sensor03) qua cờ --devices.
- Cấu hình giá trị cố định --temperature và --humidity phục vụ kiểm thử cảnh báo.
"""

import asyncio
import math
import random

from aiocoap import resource

from coap_common import arguments, device_id, json_message, now, positive, run, serve


class SensorResource(resource.Resource):
    """Tài nguyên CoAP mô phỏng cảm biến nhiệt độ và độ ẩm."""

    def __init__(self, identifier="sensor01", temperature=None, humidity=None, include_timestamp=False):
        super().__init__()
        self.identifier = identifier
        self.temperature = temperature
        self.humidity = humidity
        self.include_timestamp = include_timestamp
        self.data = {}
        self.update()

    def update(self):
        """Cập nhật giá trị đo mới của cảm biến (ngẫu nhiên hoặc cố định)."""
        temp = self.temperature if self.temperature is not None else round(random.uniform(20.0, 40.0), 1)
        hum = self.humidity if self.humidity is not None else round(random.uniform(30.0, 80.0), 1)
        data = {
            "device_id": self.identifier,
            "temperature": temp,
            "humidity": hum,
        }
        if self.include_timestamp:
            data["timestamp"] = now()
        self.data = data
        print(f"Sensor updated: {self.data}", flush=True)

    async def render_get(self, request):
        """Xử lý yêu cầu GET từ Client và trả về dữ liệu cảm biến dạng JSON."""
        return json_message(self.data)


def setup(parser, config):
    """Thiết lập các tham số dòng lệnh cho Sensor Server."""
    parser.add_argument("--device-id", type=device_id, default="sensor01",
                        help="Mã định danh cảm biến (mặc định: sensor01).")
    parser.add_argument("--devices", type=str, default=None,
                        help="Danh sách nhiều mã cảm biến, phân tách bằng dấu phẩy (vd: sensor01,sensor02,sensor03).")
    parser.add_argument("--interval", type=positive, default=3,
                        help="Chu kỳ cập nhật dữ liệu cảm biến tính bằng giây (mặc định: 3 giây).")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Nhiệt độ cố định để kiểm thử cảnh báo (20..40).")
    parser.add_argument("--humidity", type=float, default=None,
                        help="Độ ẩm cố định để kiểm thử cảnh báo (30..80).")
    parser.add_argument("--include-timestamp", action="store_true",
                        help="Gợi ý mở rộng: Bổ sung trường timestamp vào JSON payload.")


async def main():
    args = arguments(__doc__, setup)

    # Kiểm tra tính hợp lệ của giá trị nhiệt độ và độ ẩm cố định nếu được cung cấp
    for value, low, high, name in ((args.temperature, 20, 40, "nhiệt độ"), (args.humidity, 30, 80, "độ ẩm")):
        if value is not None and (not math.isfinite(value) or not low <= value <= high):
            raise ValueError(f"Giá trị {name} phải là số hữu hạn trong khoảng {low}..{high}.")

    # Xác định danh sách các cảm biến cần khởi tạo
    if args.devices:
        device_ids = [d.strip() for d in args.devices.split(",") if d.strip()]
        if not device_ids:
            raise ValueError("--devices không được rỗng.")
        for d in device_ids:
            device_id(d)
    else:
        device_ids = [args.device_id]

    site = resource.Site()
    sensors = []
    for d_id in device_ids:
        sensor = SensorResource(
            identifier=d_id,
            temperature=args.temperature,
            humidity=args.humidity,
            include_timestamp=args.include_timestamp,
        )
        sensors.append(sensor)
        site.add_resource(["iot", "lab", d_id, "data"], sensor)

    async def update_loop():
        """Vòng lặp tự động cập nhật dữ liệu cảm biến sau mỗi interval giây."""
        while True:
            await asyncio.sleep(args.interval)
            for s in sensors:
                s.update()

    banner = f"SERVER READY {args.host}:{args.port} (UDP)"
    await serve(site, args, update_loop, banner=banner)


if __name__ == "__main__":
    raise SystemExit(run(main))
