# Thực hành buổi 1 Python với MQTT

Bài thực hành gồm ba bài, sáu chương trình Python: gửi và nhận lời chào, mô phỏng cảm biến nhiệt độ và độ ẩm, điều khiển thiết bị qua MQTT hai chiều. Mã nguồn dùng `paho-mqtt==2.1.0`, MQTT 3.1.1 và callback API phiên bản 2.

## 1. Các file nộp bài

| File | Chức năng |
| --- | --- |
| `publisher_bai1.py` | Gửi lời chào kèm họ tên và mã sinh viên |
| `subscriber_bai1.py` | Hiển thị topic, payload và thời điểm nhận |
| `sensor_publisher_bai2.py` | Gửi JSON cảm biến định kỳ 3 giây |
| `monitor_subscriber_bai2.py` | Phân tích JSON và cảnh báo theo ngưỡng |
| `device_bai3.py` | Nhận ON/OFF và phản hồi trạng thái |
| `controller_bai3.py` | Nhập lệnh bàn phím và nhận trạng thái |
| `mqtt_common.py` | Cấu hình, kết nối, subscribe và publish dùng chung; phải nộp kèm |
| `README.md`, `README.txt` | Hướng dẫn chạy và cấu hình broker |
| `config.example.json` | Mẫu cấu hình broker và thông tin sinh viên |
| `requirements.txt` | Thư viện của sáu chương trình |
| `requirements-broker.txt`, `tools/local_broker.py` | Broker cục bộ tùy chọn và môi trường kiểm thử |
| `broker/mosquitto.conf` | Cấu hình Mosquitto thay thế |
| `tests/` | Kiểm thử tích hợp qua broker thật |
| `docs/ket_qua_kiem_thu.txt` | Kết quả kiểm thử thực tế |

## 2. Chuẩn bị môi trường

Yêu cầu Python 3.10 trở lên. Môi trường đã kiểm thử: Windows, Python 3.13.7. Chạy mọi lệnh bên dưới tại thư mục chứa sáu file Python.

PowerShell trên Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-broker.txt
Copy-Item config.example.json config.json
```

Mở `config.json`, điền `student_name` và `student_id` bằng thông tin thật. Giữ `host` là `127.0.0.1`, `port` là `1883` khi dùng broker cục bộ. Không cần điền tài khoản/mật khẩu cho broker thực hành này.

Nếu chỉ chạy các chương trình với broker đã có sẵn, cài `requirements.txt` là đủ. `amqtt` chỉ dùng cho broker cục bộ và kiểm thử, không phải thư viện client thay thế `paho-mqtt`.

Không cần kích hoạt môi trường ảo: dùng trực tiếp đường dẫn `.venv\Scripts\python.exe` như ví dụ. Trên Linux/macOS, tạo môi trường bằng `python3 -m venv .venv`, thay đường dẫn đó bằng `.venv/bin/python`, và dùng `cp config.example.json config.json`.

## 3. Cấu hình và khởi động MQTT broker

### Cách A dùng broker Python đi kèm

Mở terminal riêng, chạy và giữ terminal này trong suốt quá trình thực hành:

```powershell
.\.venv\Scripts\python.exe tools/local_broker.py
```

Kết quả khởi động:

```text
BROKER READY 127.0.0.1:1883
```

Broker aMQTT lắng nghe TCP trên `127.0.0.1:1883`, cho phép kết nối không tài khoản trên máy cục bộ. Đây là MQTT broker thật; các chương trình trao đổi bản tin qua kết nối mạng, không mô phỏng bằng gọi hàm trực tiếp. Trạng thái retained nằm trong bộ nhớ, mất khi broker dừng. Nhấn Ctrl+C để dừng broker.

Nếu cổng 1883 đang được dùng, chọn cổng khác:

```powershell
.\.venv\Scripts\python.exe tools/local_broker.py --port 1884
```

Khi đó sửa `port` trong `config.json` thành `1884`, hoặc thêm `--port 1884` cho **tất cả** chương trình client. Không chạy đồng thời hai broker trên cùng cổng.

### Cách B dùng Eclipse Mosquitto

Cài Mosquitto từ [trang tải chính thức](https://mosquitto.org/download/). Với đường dẫn cài mặc định Windows, chạy:

```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -c .\broker\mosquitto.conf -v
```

File cấu hình đã đặt `listener 1883 127.0.0.1`, `allow_anonymous true` và `persistence false`. Dùng `host = 127.0.0.1`, `port = 1883` như cách A. Cấu hình này phục vụ bài thực hành trên cùng máy.

### Broker khác có xác thực hoặc TLS

Sửa `config.json` theo địa chỉ/cổng/tài khoản do broker cung cấp. `tls: true` bật TLS với kiểm tra chứng chỉ; `ca_cert` là đường dẫn CA nếu broker dùng CA riêng, hoặc `null` để dùng kho CA mặc định. Cổng phải khớp với listener của broker; chương trình không tự đổi cổng khi bật TLS.

Cấu hình mặc định không cần `config.json`. Nếu file tồn tại, chương trình đọc file nằm cạnh mã nguồn. Có thể chọn file khác với `--config duong_dan.json`. Tham số dòng lệnh ưu tiên hơn file, file ưu tiên hơn mặc định. File `config.json` được bỏ qua bởi Git để tránh đưa mật khẩu lên repository.

Các tùy chọn chung: `--host`, `--port`, `--username`, `--password`, `--tls`, `--no-tls`, `--ca-cert`, `--timeout`. Xem `--help` của từng chương trình để biết các tùy chọn riêng.

## 4. Bài 1 gửi và nhận thông điệp

Broker vẫn chạy. Mở hai terminal client tại thư mục bài tập.

Terminal 1 chạy subscriber trước, chờ dòng `Đã subscribe: iot/lab/message`:

```powershell
.\.venv\Scripts\python.exe subscriber_bai1.py
```

Terminal 2 chạy publisher:

```powershell
.\.venv\Scripts\python.exe publisher_bai1.py
```

Publisher lấy họ tên và mã sinh viên trong `config.json`; nếu chưa có, chương trình hỏi từ bàn phím. Có thể truyền thông tin trực tiếp. Ví dụ dưới đây dùng **thông tin minh họa**, cần thay bằng thông tin của người nộp bài:

```powershell
.\.venv\Scripts\python.exe publisher_bai1.py --name "Nguyen Van A" --student-id "B23DCCN001" --count 3
```

Payload có đủ lời chào, mã sinh viên và họ tên. Ví dụ đầu ra subscriber:

```text
Nhan duoc message:
Topic: iot/lab/message
Payload: Xin chao tu client Python MQTT - B23DCCN001 - Nguyen Van A
Time: 2026-10-03 14:00:00 +0700
```

Thời điểm trên chỉ minh họa định dạng; chương trình lấy thời điểm nhận thật theo múi giờ máy chạy. `--count 3` gửi ba bản tin, `--count 0` gửi liên tục, `--interval 1` đổi khoảng gửi thành một giây. Có thể đổi lời chào bằng `--message "Loi chao cua toi"`. Subscriber mặc định chạy đến Ctrl+C.

## 5. Bài 2 mô phỏng và giám sát cảm biến

Terminal 1:

```powershell
.\.venv\Scripts\python.exe monitor_subscriber_bai2.py
```

Chờ dòng `Đã subscribe: iot/lab/sensor01/data`, rồi chạy terminal 2:

```powershell
.\.venv\Scripts\python.exe sensor_publisher_bai2.py
```

Mặc định cảm biến sinh ngẫu nhiên nhiệt độ từ 20 đến 40 °C, độ ẩm từ 30 đến 80 %, làm tròn một chữ số thập phân và gửi mỗi 3 giây trên `iot/lab/sensor01/data`. Payload truyền trên MQTT là JSON:

```json
{"device_id": "sensor01", "temperature": 28.5, "humidity": 65.2}
```

Để kiểm tra chắc chắn cả hai cảnh báo, dừng sensor đang chạy và gửi mẫu cố định:

```powershell
.\.venv\Scripts\python.exe sensor_publisher_bai2.py --temperature 36.1 --humidity 38.7 --count 1
```

Kết quả monitor:

```text
Device: sensor01
Temperature: 36.1 C
Humidity: 38.7 %
CANH BAO: Nhiet do cao
CANH BAO: Do am thap
```

Điều kiện đúng theo đề: nhiệt độ **> 35 °C**, độ ẩm **< 40 %**. Giá trị bằng 35 °C hoặc 40 % không kích hoạt cảnh báo tương ứng. Hai điều kiện được xét độc lập, một bản tin có thể có cả hai cảnh báo. JSON sai, thiếu trường, số không hữu hạn hoặc giá trị ngoài khoảng mô phỏng được báo lỗi và bỏ qua; monitor tiếp tục chạy.

Mở rộng nhiều cảm biến: chạy monitor dưới đây thay cho monitor mặc định, sau đó chạy mỗi sensor trong một terminal riêng:

```powershell
.\.venv\Scripts\python.exe monitor_subscriber_bai2.py --all-devices
.\.venv\Scripts\python.exe sensor_publisher_bai2.py --device-id sensor01
.\.venv\Scripts\python.exe sensor_publisher_bai2.py --device-id sensor02
```

Monitor dùng wildcard `iot/lab/+/data` để nhận cả hai thiết bị. Mỗi thiết bị dùng topic và trường `device_id` tương ứng. Nhấn Ctrl+C để dừng các chương trình đang chạy.

## 6. Bài 3 điều khiển đèn thông minh

Terminal 1 chạy thiết bị và chờ dòng trạng thái ban đầu:

```powershell
.\.venv\Scripts\python.exe device_bai3.py
```

Thiết bị khởi động ở `OFF`, subscribe `iot/lab/light01/cmd` và publish trạng thái JSON lên `iot/lab/light01/status`.

Terminal 2 chạy controller:

```powershell
.\.venv\Scripts\python.exe controller_bai3.py
```

Nhập lần lượt `ON`, `OFF`, một lệnh sai như `HELLO`, rồi `EXIT`. Ví dụ phản hồi khi bật đèn (dòng nhận có thể xuất hiện trước dòng xác nhận gửi vì hai luồng chạy đồng thời):

```text
Nhap lenh: ON
Da gui lenh ON toi light01
Trang thai nhan duoc:
{"device_id": "light01", "status": "ON"}
Thiết bị đã phản hồi trạng thái ON.
```

Mỗi lệnh hợp lệ làm thiết bị cập nhật trạng thái và gửi phản hồi, kể cả khi trạng thái không đổi. `ON` là bật, `OFF` là tắt. Lệnh sai được báo lỗi và không gửi từ controller; thiết bị cũng kiểm tra lệnh để từ chối dữ liệu sai từ client khác. Chương trình chấp nhận chữ thường và loại bỏ khoảng trắng đầu/cuối. `EXIT` kết thúc controller, Ctrl+C kết thúc thiết bị.

Trạng thái được publish với `retain=True`: controller mới mở nhận ngay trạng thái lưu trên broker, được gắn nhãn riêng. Lệnh điều khiển dùng `retain=False`; thiết bị bỏ qua retained command cũ. Controller chờ phản hồi **mới** từ thiết bị, không lấy trạng thái retained làm xác nhận điều khiển. Nếu không có phản hồi sau 5 giây, chương trình báo chưa có phản hồi. Đổi thời gian bằng `--response-timeout`.

Mở rộng quạt và máy bơm: chạy một chương trình device cho mỗi ID, rồi chạy controller có ID trùng với thiết bị cần điều khiển:

```powershell
.\.venv\Scripts\python.exe device_bai3.py --device-id fan01
.\.venv\Scripts\python.exe controller_bai3.py --device-id fan01
```

Làm tương tự với `--device-id pump01`. Đèn, quạt và bơm đều được mô phỏng bằng trạng thái ON/OFF; không điều khiển phần cứng thật. Khi chạy nhiều thiết bị cùng lúc, mỗi lệnh trên cần một terminal riêng.

## 7. Thiết bị topic và payload

| Bài | Topic mặc định | Publisher | Subscriber | Payload |
| --- | --- | --- | --- | --- |
| 1 | `iot/lab/message` | Publisher | Subscriber | Lời chào, mã sinh viên, họ tên |
| 2 | `iot/lab/sensor01/data` | Sensor | Monitor | JSON `device_id`, `temperature`, `humidity` |
| 3 điều khiển | `iot/lab/light01/cmd` | Controller | Device | Chuỗi `ON` hoặc `OFF` |
| 3 trạng thái | `iot/lab/light01/status` | Device | Controller | JSON `device_id`, `status` |

Client kết nối broker; publisher gửi lên topic; broker chuyển bản tin cho subscriber đăng ký topic đó. Trong bài 3, cả device và controller đều vừa publish vừa subscribe trên hai topic khác nhau, tạo giao tiếp hai chiều. Mọi bản tin dùng QoS 1; publisher chờ broker xác nhận trước khi thoát. QoS 1 có thể giao trùng bản tin; ON/OFF có thể áp dụng lại an toàn. Trạng thái chỉ thể hiện giá trị ON/OFF, không có mã yêu cầu để đối chiếu khi nhiều controller cùng điều khiển một thiết bị; demo dùng một controller cho mỗi thiết bị.

## 8. Kiểm thử và kết quả

Chạy toàn bộ kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Kiểm thử tự khởi động broker aMQTT trên một cổng cục bộ tạm thời và tự dừng broker sau khi chạy; không cần khởi động broker 1883 trước. Kiểm thử sử dụng tên/mã sinh viên giả để kiểm tra payload và chạy các chương trình như tiến trình riêng.

Các trường hợp gồm: ba lời chào và thời điểm nhận; thông tin trong cấu hình và ưu tiên dòng lệnh; dữ liệu ngẫu nhiên và chu kỳ mặc định 3 giây; ngưỡng đúng tại 35 °C và 40 %; hai cảnh báo độc lập; dữ liệu sai không làm monitor dừng; nhiều cảm biến; ON/OFF/EXIT và lệnh sai; phản hồi cho lệnh hợp lệ lặp lại; retained command cũ; ba thiết bị riêng; thiếu thiết bị; cổng sai và broker không hoạt động. Kết quả thực tế được lưu ở `docs/ket_qua_kiem_thu.txt`.

Subscriber, monitor và device có `--max-messages N` để dừng sau N bản tin hợp lệ hoặc `--duration N` để dừng sau N giây. Mặc định vẫn chạy liên tục đến Ctrl+C. Các tùy chọn này giúp kiểm thử mà không đổi hành vi yêu cầu của đề.

### Xử lý sự cố

- `Connection refused` hoặc `WinError 10061`: khởi động broker, kiểm tra `host`, `port`, và bảo đảm tất cả client dùng cùng broker.
- Subscriber không nhận lời chào: chạy subscriber trước publisher và chờ xác nhận subscribe. Lời chào/cảm biến không retain nên không được gửi lại cho subscriber mở sau.
- `Address already in use`: dùng broker đang hoạt động hoặc đổi cổng cho broker và mọi client.
- `ModuleNotFoundError`: chạy đúng Python trong `.venv` và cài file requirements phù hợp.
- Controller không có phản hồi: chạy device với cùng `--device-id`, giữ terminal device hoạt động và kiểm tra hai chương trình kết nối cùng broker.

## 9. Đối chiếu yêu cầu nộp bài

Đã cung cấp đủ sáu file có tên theo đề; cần nộp kèm `mqtt_common.py`, file requirements và tài liệu hướng dẫn để chạy được. Các phần mở rộng trong đề đã có: nhiều thông điệp, subscriber liên tục, nhiều cảm biến, trình bày từng giá trị, xử lý lệnh sai, EXIT và mô phỏng đèn/quạt/bơm.

Theo đề, nộp qua link GitHub và gửi link vào nhóm Zalo lớp trước **23:59 thứ Bảy 10/10/2026**. Điền thông tin sinh viên trước khi demo/nộp bài. Mã nguồn nằm trong repository hiện tại; để đưa lên GitHub có thể chạy sau khi xem lại các file:

```powershell
git add .
git commit -m "Hoan thanh thuc hanh Python MQTT buoi 1"
git push origin HEAD
```

Không đưa `.venv`, `config.json` chứa thông tin cá nhân/mật khẩu hoặc thư mục tạm lên GitHub. `.gitignore` đã loại các file này. Nếu muốn công khai họ tên/mã sinh viên trong bài nộp, bổ sung thông tin đó vào README theo yêu cầu lớp.

## 10. Tài liệu tham khảo

- [Eclipse Paho MQTT Python](https://eclipse.dev/paho/clients/python/docs/): client, callback API phiên bản 2, vòng lặp mạng và xác nhận publish.
- [aMQTT broker configuration](https://amqtt.readthedocs.io/en/latest/references/broker_config/): listener và plugin broker cục bộ.
- [Eclipse Mosquitto configuration](https://mosquitto.org/man/mosquitto-conf-5.html): cấu hình listener và truy cập broker.

Yêu cầu bài tập lấy từ tài liệu **Thực hành buổi 1 python mqtt.docx**.
