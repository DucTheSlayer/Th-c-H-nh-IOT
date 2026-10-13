# Thực hành buổi 2 Python với AMQP

Bài làm sử dụng Python, thư viện `pika` và RabbitMQ qua AMQP 0-9-1.
Gồm đủ 7 chương trình của 3 bài trong đề. Các consumer chạy liên tục đến khi nhấn Ctrl+C.
Các queue được khai báo với `durable=True` để tương thích RabbitMQ 4.3 trở lên.

## 1. Chuẩn bị

Mở terminal tại thư mục gốc repository và chạy:

```powershell
cd TH2
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.json config.json
```

Nếu chưa có `.venv`, tạo bằng `python -m venv ..\.venv` trước khi cài thư viện.
Tất cả lệnh Python bên dưới chạy tại thư mục **TH2**. Mỗi chương trình cần một terminal riêng.

Mở `config.json` và điền `student_name`, `student_id` bằng họ tên và mã sinh viên thật.
Nếu chưa điền, producer bài 1 sẽ hỏi khi chạy. File cấu hình được đọc theo vị trí mã nguồn
và được Git bỏ qua.

### Broker sử dụng

Mặc định: RabbitMQ trên `127.0.0.1`, cổng AMQP `5672`, tài khoản `guest/guest`, virtual host `/`.

Máy có Docker Desktop: mở Docker Desktop, đợi Docker chạy rồi khởi động broker trong TH2:

```powershell
docker compose up -d
docker compose logs rabbitmq
```

Đợi log báo server đã khởi động và sẵn sàng nhận kết nối rồi chạy các chương trình Python.
Trang quản lý: <http://localhost:15672>, đăng nhập `guest/guest`.
Dừng broker sau khi thực hành bằng `docker compose stop`; mở lại bằng `docker compose start`.

Nếu đã cài RabbitMQ trực tiếp trên Windows thì dùng broker đó, không cần chạy Docker.
Hướng dẫn cài: [RabbitMQ trên Windows](https://www.rabbitmq.com/docs/install-windows).
Nếu dùng broker của lớp, sửa `host`, `port`, `username`, `password`, `virtual_host` trong `config.json`
theo thông tin thầy cung cấp. Tài khoản `guest` mặc định chỉ dùng từ máy chạy RabbitMQ.

## 2. Bài 1 Gửi và nhận message qua queue

Queue: `iot_lab_queue`.

Terminal 1 chạy consumer:

```powershell
..\.venv\Scripts\python.exe consumer_bai1.py
```

Terminal 2 chạy producer:

```powershell
..\.venv\Scripts\python.exe producer_bai1.py
```

Producer gửi lời chào kèm mã sinh viên và họ tên. Consumer in nội dung và thời điểm nhận.
Có thể thêm `--count 3` vào lệnh producer để gửi 3 message liên tiếp.

Ví dụ đầu ra (thông tin sinh viên và thời gian chỉ minh họa):

```text
Da nhan message: Xin chao tu ung dung Python AMQP - B21xxxx - Nguyen Van A
Thoi gian nhan: 14:05:21
```

## 3. Bài 2 Mô phỏng cảm biến và giám sát

Queue: `sensor_data_queue`.

Terminal 1 chạy monitoring consumer:

```powershell
..\.venv\Scripts\python.exe monitor_consumer_bai2.py
```

Terminal 2 chạy sensor producer:

```powershell
..\.venv\Scripts\python.exe sensor_producer_bai2.py
```

Cảm biến gửi mỗi **3 giây**, sinh nhiệt độ ngẫu nhiên từ 20 đến 40 và độ ẩm từ 30 đến 80.
Payload là JSON, gồm đúng các trường:

```json
{"device_id": "sensor01", "temperature": 29.5, "humidity": 62.1}
```

Monitor in mã thiết bị, nhiệt độ, độ ẩm. Hai cảnh báo được xét độc lập:

- Nhiệt độ **> 35**: `CANH BAO: Nhiet do cao`.
- Độ ẩm **< 40**: `CANH BAO: Do am thap`.

Giá trị bằng 35 hoặc 40 không kích hoạt cảnh báo tương ứng.
Để demo cả hai cảnh báo, dừng sensor ngẫu nhiên bằng Ctrl+C, sau đó chạy:

```powershell
..\.venv\Scripts\python.exe sensor_producer_bai2.py --temperature 36.4 --humidity 38.9 --count 1
```

Đầu ra mong đợi:

```text
Device: sensor01
Temperature: 36.4
Humidity: 38.9
CANH BAO: Nhiet do cao
CANH BAO: Do am thap
```

## 4. Bài 3 Điều phối cảnh báo bằng exchange

Direct exchange: `iot_alert_exchange`.

| Routing key | Queue nhận |
| --- | --- |
| `info` | Không queue nào trong hai consumer của bài này |
| `warning` | `warning_queue` |
| `critical` | `critical_queue` |

**Chạy cả hai consumer trước producer** để queue đã được tạo và bind với exchange.

Terminal 1:

```powershell
..\.venv\Scripts\python.exe warning_consumer_bai3.py
```

Terminal 2:

```powershell
..\.venv\Scripts\python.exe critical_consumer_bai3.py
```

Đợi cả hai terminal báo `Dang lang nghe`, sau đó chạy terminal 3:

```powershell
..\.venv\Scripts\python.exe alert_producer_bai3.py
```

Producer gửi 3 message với routing key `info`, `warning`, `critical`.
Warning consumer chỉ in:

```text
[warning_queue] Da nhan: Nhiet do phong may vuot nguong warning
```

Critical consumer chỉ in:

```text
[critical_queue] Da nhan: Cam bien kho lanh mat ket noi critical
```

Cả hai consumer không nhận message `info`.

## 5. Kết quả và file nộp bài

Bài làm có gửi/nhận lời chào và thời gian nhận, gửi JSON cảm biến theo chu kỳ 3 giây,
phát hiện hai điều kiện cảnh báo, và phân phối cảnh báo đúng routing key bằng direct exchange.
Kết quả kiểm tra thực tế được ghi riêng trong [kết quả kiểm thử](docs/ket_qua_kiem_thu.txt).
Đã kiểm tra cú pháp và 9 trường hợp logic bằng kết nối giả lập. Ngày 13/10/2026 đã kết nối
RabbitMQ 4.3.6 và khai báo thành công cả 4 queue với `durable=True`.
Chưa kiểm thử đầy đủ việc gửi/nhận trên broker. Các đoạn đầu ra phía trên là kết quả mong đợi khi demo.

Nộp 7 file đúng tên trong đề:

- `producer_bai1.py`, `consumer_bai1.py`.
- `sensor_producer_bai2.py`, `monitor_consumer_bai2.py`.
- `alert_producer_bai3.py`, `warning_consumer_bai3.py`, `critical_consumer_bai3.py`.

Nộp kèm `amqp_common.py`, `requirements.txt`, `config.example.json` và `README.md` để chạy được.
File `compose.yaml` giúp mở RabbitMQ bằng Docker. Điền thông tin sinh viên thật trước khi demo.

Nếu gặp lỗi kết nối, kiểm tra broker đang chạy, cổng **5672** và thông tin trong `config.json`.
Cổng **15672** là trang quản lý, không dùng để kết nối Pika.

Tham khảo: [gửi/nhận queue](https://www.rabbitmq.com/tutorials/tutorial-one-python),
[direct exchange và routing key](https://www.rabbitmq.com/tutorials/tutorial-four-python).
