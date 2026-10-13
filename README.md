# Thực hành IoT

Các buổi thực hành được tổ chức trong thư mục riêng:

| Thư mục | Nội dung |
| --- | --- |
| [TH1](TH1/) | Python với MQTT: gửi/nhận thông điệp, mô phỏng cảm biến và điều khiển thiết bị. Gồm bài 1, bài 2 và bài 3 của buổi TH1. |
| [TH2](TH2/) | Python với AMQP và RabbitMQ: gửi/nhận queue, dữ liệu cảm biến và điều phối cảnh báo qua direct exchange. |

## Chạy TH1

Mở terminal tại thư mục gốc repository rồi chuyển vào TH1:

```powershell
cd TH1
```

Làm theo [hướng dẫn TH1](TH1/README.md) để cài thư viện, chạy broker và các chương trình.
Môi trường Python `.venv` nằm ở thư mục gốc repository; khi đang ở TH1, dùng `..\.venv\Scripts\python.exe`.

Ví dụ chạy kiểm thử từ thư mục TH1:

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Làm TH2

Chạy `cd TH2` từ thư mục gốc repository rồi làm theo [hướng dẫn TH2](TH2/README.md).
TH2 có đủ 7 chương trình theo đề, cấu hình mẫu và file Docker Compose để mở RabbitMQ cục bộ.
