"""
BUỔI THỰC HÀNH: LẬP TRÌNH PYTHON VỚI GIAO THỨC COAP
Bài 2: Chương trình giám sát dữ liệu cảm biến định kỳ (Monitoring CoAP Client)

Mục tiêu:
- Gửi yêu cầu GET định kỳ mỗi 3 giây đến tài nguyên:
  coap://<host>:<port>/iot/lab/<device_id>/data
- Nhận và phân tích dữ liệu JSON từ Server.
- Hiển thị thông tin:
  + Thời điểm nhận dữ liệu
  + Mã thiết bị (Device)
  + Nhiệt độ (Temperature)
  + Độ ẩm (Humidity)
- Kiểm tra các điều kiện ngưỡng và cảnh báo:
  + Nếu nhiệt độ > 35 °C: Hiển thị "CANH BAO: Nhiet do cao"
  + Nếu độ ẩm < 40 %: Hiển thị "CANH BAO: Do am thap"
  + Nếu bình thường: Hiển thị "Trang thai: Binh thuong"
- Chương trình tiếp tục giám sát cho đến khi người dùng nhấn Ctrl+C hoặc hết --count.
- Xử lý lỗi an toàn khi Server không phản hồi và tự động thử lại ở chu kỳ kế tiếp.

Gợi ý mở rộng:
- Cho phép lựa chọn mã thiết bị cần giám sát qua cờ --device-id.
- Ghi dữ liệu nhận được ra file CSV (--export-csv) hoặc JSON (--export-json).
- Thống kê số lần GET, số lần thành công/lỗi và thời gian phản hồi trung bình (RTT).
"""

import asyncio
import csv
import json
import math
from pathlib import Path

import aiocoap

from coap_common import (arguments, client_context, device_id, nonnegative, now,
                         positive, read_json, request, run)


def display_sensor(response, expected_id):
    """Phân tích payload JSON phản hồi từ cảm biến, kiểm tra tính hợp lệ và hiển thị cảnh báo."""
    data = read_json(response)
    if data.get("device_id") != expected_id:
        raise ValueError("Mã thiết bị trong phản hồi không khớp.")

    for key, low, high in (("temperature", 20, 40), ("humidity", 30, 80)):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Giá trị {key} không hợp lệ.")

    print(f"[{now()}] Received sensor data\nDevice: {data['device_id']}\n"
          f"Temperature: {data['temperature']} C\nHumidity: {data['humidity']} %", flush=True)

    if "timestamp" in data:
        print(f"Timestamp: {data['timestamp']}", flush=True)

    hot = data["temperature"] > 35
    dry = data["humidity"] < 40

    if hot:
        print("CANH BAO: Nhiet do cao", flush=True)
    if dry:
        print("CANH BAO: Do am thap", flush=True)
    if not hot and not dry:
        print("Trang thai: Binh thuong", flush=True)

    return data


def save_to_csv(filepath, record):
    """Ghi bản ghi dữ liệu cảm biến vào file CSV."""
    path = Path(filepath)
    file_exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "device_id", "temperature", "humidity", "status"])
        alert_str = "NORMAL"
        if record["temperature"] > 35 and record["humidity"] < 40:
            alert_str = "HIGH_TEMP_AND_LOW_HUMIDITY"
        elif record["temperature"] > 35:
            alert_str = "HIGH_TEMP"
        elif record["humidity"] < 40:
            alert_str = "LOW_HUMIDITY"
        writer.writerow([
            record.get("timestamp", now()),
            record["device_id"],
            record["temperature"],
            record["humidity"],
            alert_str,
        ])


def save_to_json(filepath, record):
    """Ghi bản ghi dữ liệu cảm biến vào file JSON."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    if path.exists():
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(records, list):
                records = [records]
        except Exception:
            records = []
    records.append(record)
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def setup(parser, config):
    """Thiết lập các tham số dòng lệnh cho Monitoring Client."""
    parser.add_argument("--device-id", type=device_id, default="sensor01",
                        help="Mã cảm biến cần giám sát (mặc định: sensor01).")
    parser.add_argument("--interval", type=positive, default=3,
                        help="Chu kỳ gửi yêu cầu GET tính bằng giây (mặc định: 3 giây).")
    parser.add_argument("--count", type=nonnegative, default=0,
                        help="Số lần truy vấn cảm biến (0: chạy liên tục đến khi nhấn Ctrl+C).")
    parser.add_argument("--export-csv", type=str, default=None,
                        help="Gợi ý mở rộng: Đường dẫn file CSV lưu trữ dữ liệu cảm biến.")
    parser.add_argument("--export-json", type=str, default=None,
                        help="Gợi ý mở rộng: Đường dẫn file JSON lưu trữ dữ liệu cảm biến.")


async def main():
    args = arguments(__doc__, setup)
    context = await client_context()

    total = 0
    successful = 0
    failures = 0
    rtt_list = []

    try:
        while args.count == 0 or total < args.count:
            start = asyncio.get_running_loop().time()
            try:
                response = await request(context, args, aiocoap.GET, f"iot/lab/{args.device_id}/data")
                rtt = asyncio.get_running_loop().time() - start
                rtt_list.append(rtt)
                data = display_sensor(response, args.device_id)
                successful += 1

                if args.export_csv:
                    try:
                        save_to_csv(args.export_csv, data)
                    except Exception as err:
                        print(f"[!] Không thể ghi CSV: {err}", flush=True)

                if args.export_json:
                    try:
                        save_to_json(args.export_json, data)
                    except Exception as err:
                        print(f"[!] Không thể ghi JSON: {err}", flush=True)

            except (ValueError, aiocoap.error.Error, OSError, asyncio.TimeoutError) as error:
                failures += 1
                detail = "Hết thời gian chờ" if isinstance(error, asyncio.TimeoutError) else (str(error) or "Hết thời gian chờ")
                print(f"Lỗi đọc cảm biến: {detail}. Sẽ thử lại.", flush=True)

            total += 1
            if args.count == 0 or total < args.count:
                elapsed = asyncio.get_running_loop().time() - start
                await asyncio.sleep(max(0.0, args.interval - elapsed))

    finally:
        await context.shutdown()
        if total > 0 and (args.count > 0 or total > 1):
            avg_rtt = f"{sum(rtt_list) / len(rtt_list) * 1000:.1f} ms" if rtt_list else "N/A"
            print("\n" + "=" * 45, flush=True)
            print("         THONG KE GIAM SAT CAM BIEN", flush=True)
            print("=" * 45, flush=True)
            print(f"Tong so lan truy van : {total}", flush=True)
            print(f"Thanh cong           : {successful}", flush=True)
            print(f"Loi / mat ket noi    : {failures}", flush=True)
            print(f"Thoi gian phan hoi TB: {avg_rtt}", flush=True)
            print("=" * 45, flush=True)


if __name__ == "__main__":
    raise SystemExit(run(main))
