THỰC HÀNH BUỔI 1 PYTHON VỚI MQTT

1. Môi trường và broker
Python >= 3.10, paho-mqtt 2.1.0. Broker mặc định: aMQTT cục bộ,
127.0.0.1:1883, MQTT TCP, không yêu cầu tài khoản.
Các lệnh chạy trong thư mục chứa mã nguồn, bằng PowerShell:

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-broker.txt
Copy-Item config.example.json config.json

Điền student_name và student_id trong config.json bằng thông tin của bạn.
Nếu chưa điền, publisher bài 1 sẽ hỏi từ bàn phím.
Host/port và tài khoản broker cũng cấu hình trong file này.
Có thể dùng --host, --port, --config, --username, --password, --tls,
--ca-cert, --timeout để cấu hình khi chạy; xem --help của từng chương trình.

Mở terminal riêng, giữ broker hoạt động:
.\.venv\Scripts\python.exe tools/local_broker.py
Đợi: BROKER READY 127.0.0.1:1883

Nếu dùng Mosquitto đã cài, thay broker trên bằng:
& "C:\Program Files\mosquitto\mosquitto.exe" -c .\broker\mosquitto.conf -v
Không chạy hai broker trên cùng cổng. Nếu đổi cổng, đổi cho mọi client.

2. Bài 1
Terminal 1, chạy trước và đợi xác nhận subscribe:
.\.venv\Scripts\python.exe subscriber_bai1.py
Terminal 2:
.\.venv\Scripts\python.exe publisher_bai1.py --count 3
Kết quả: nhận lời chào, họ tên, mã sinh viên trên iot/lab/message;
hiển thị Topic, Payload, Time. --count 0 gửi liên tục.

3. Bài 2
Terminal 1:
.\.venv\Scripts\python.exe monitor_subscriber_bai2.py
Đợi subscribe; terminal 2:
.\.venv\Scripts\python.exe sensor_publisher_bai2.py
Kết quả: JSON device_id, temperature, humidity gửi mỗi 3 giây trên
iot/lab/sensor01/data. Nhiệt độ > 35 C báo nhiệt độ cao;
độ ẩm < 40 % báo độ ẩm thấp. Bằng ngưỡng không báo.
Demo cả hai cảnh báo, thay sensor đang chạy bằng:
.\.venv\Scripts\python.exe sensor_publisher_bai2.py --temperature 36.1 --humidity 38.7 --count 1
Mở rộng: monitor --all-devices; chạy sensor --device-id sensor02
trong terminal riêng để giám sát nhiều thiết bị.

4. Bài 3
Terminal 1:
.\.venv\Scripts\python.exe device_bai3.py
Đợi trạng thái ban đầu; terminal 2:
.\.venv\Scripts\python.exe controller_bai3.py
Nhập ON, OFF, thử lệnh sai, nhập EXIT để kết thúc controller.
Kết quả: controller gửi lệnh vào iot/lab/light01/cmd; thiết bị gửi
JSON {"device_id":"light01","status":"ON"} hoặc OFF vào
iot/lab/light01/status sau mỗi lệnh hợp lệ.
Thiết bị và controller cùng dùng --device-id fan01 hoặc pump01
để mô phỏng quạt/bơm. Mỗi chương trình chạy trong terminal riêng.
Lệnh sai không thay đổi trạng thái; thiếu phản hồi được báo sau 5 giây.
Ctrl+C để dừng các chương trình chạy liên tục và broker.

5. Kiểm thử
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Tự chạy broker trên cổng tạm, kiểm thử trao đổi MQTT thật.
Xem kết quả thực tế trong docs/ket_qua_kiem_thu.txt.

6. Nộp bài
Nộp đủ sáu file theo đề, kèm mqtt_common.py, requirements.txt,
README.md, README.txt và các file hỗ trợ trong repository.
README.md có hướng dẫn chi tiết và ví dụ kết quả.
Theo đề: gửi link GitHub vào nhóm Zalo lớp trước 23:59 10/10/2026.
Không nộp .venv hoặc config.json chứa mật khẩu.
