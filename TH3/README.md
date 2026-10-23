# Thực hành buổi 3 Python với CoAP

Bài làm gồm 7 chương trình của 3 bài trong đề: GET/POST thông điệp, GET dữ liệu cảm biến định kỳ,
và GET/PUT điều khiển đèn kết hợp CoAP Observe. Dùng `aiocoap==0.4.17`, truyền qua UDP,
không cần MQTT broker hoặc RabbitMQ. Cấu trúc file đặt trực tiếp trong TH3 giống TH1 và TH2.

## 1. Chuẩn bị và thông tin sinh viên

Yêu cầu Python 3.10 trở lên. Môi trường kiểm thử thực tế: Windows, Python 3.13.7.
Từ thư mục gốc repository:

```powershell
cd TH3
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.json config.json
```

Nếu chưa có môi trường ảo, chạy `python -m venv ..\.venv` trước khi cài thư viện.
Mọi lệnh bên dưới chạy trong **TH3**; mỗi server/client cần một terminal riêng.
Trên Linux/macOS, thay đường dẫn Python bằng `../.venv/bin/python`.

Điền thông tin người thực hiện trong `config.json` trước khi demo hoặc nộp:

| Trường | Giá trị cần điền |
| --- | --- |
| `student_name` | Họ và tên sinh viên hoặc đại diện nhóm |
| `student_id` | Mã sinh viên |

Không gán sẵn thông tin sinh viên giả vào cấu hình. Nếu để trống, client bài 1 hỏi khi chạy.
Các ví dụ dùng `TEST001` và `Sinh vien test` chỉ là thông tin kiểm thử.
File `config.json` được Git bỏ qua; thông tin nhóm cần công khai có thể bổ sung tại đây trước khi nộp.

Mặc định cấu hình là `host=127.0.0.1`, `port=5683`, `timeout=5` giây. File cấu hình được đọc
theo vị trí mã nguồn, không phụ thuộc thư mục hiện tại. Có thể ghi đè bằng `--host`, `--port`,
`--timeout`. Dùng `--help` để xem tùy chọn riêng của từng chương trình.

## 2. Địa chỉ và tài nguyên

| Bài | URI mặc định | Phương thức | Payload phản hồi |
| --- | --- | --- | --- |
| 1 | `coap://127.0.0.1:5683/iot/lab/message` | GET, POST | Văn bản UTF-8 |
| 2 | `coap://127.0.0.1:5683/iot/lab/sensor01/data` | GET | JSON cảm biến |
| 3 | `coap://127.0.0.1:5683/iot/lab/light01/status` | GET, PUT, Observe | JSON trạng thái |

**Chạy lần lượt từng bài:** dừng server bài trước bằng Ctrl+C rồi mở server bài tiếp theo,
vì cả ba mặc định cùng dùng UDP 5683. Muốn chạy đồng thời, đặt `--port` khác nhau cho mỗi server
và dùng cổng tương ứng trên client.

Transport server là `simplesocketserver`, client là `simple6` để chạy được trên Windows.
Server cần bind vào địa chỉ IP cụ thể; không dùng `0.0.0.0` hoặc `::`.
Khi chạy trên hai máy, server dùng `--host <IP-LAN-cua-server>`, client dùng cùng IP và cổng;
tường lửa máy server cần cho phép UDP cổng đó. Các chương trình chỉ mô phỏng thiết bị bằng phần mềm.

## 3. Bài 1 Gửi và nhận thông điệp

Terminal 1:

```powershell
..\.venv\Scripts\python.exe coap_server_bai1.py
```

Đợi `SERVER READY 127.0.0.1:5683 (UDP)`, rồi mở terminal 2:

```powershell
..\.venv\Scripts\python.exe coap_client_bai1.py
```

Client GET lời chào rồi POST lời chào chứa mã sinh viên và họ tên. Server in payload, thời điểm
nhận thật, trả `2.04 Changed`. GET ban đầu trả `2.05 Content` và `Xin chao tu CoAP Server`.
Server lưu thông điệp POST gần nhất trong bộ nhớ; GET sau đó trả thông điệp này.
Khởi động lại server sẽ đặt lại lời chào ban đầu.

Gửi ba thông điệp với thông tin minh họa:

```powershell
..\.venv\Scripts\python.exe coap_client_bai1.py --name "Sinh vien test" --student-id TEST001 --count 3
```

Phản hồi POST:

```text
Code: 2.04 Changed
Payload: Server da nhan thong diep
```

URI không tồn tại trả `4.04 Not Found`; phương thức không hỗ trợ trả `4.05 Method Not Allowed`.
POST rỗng hoặc không phải UTF-8 trả `4.00 Bad Request`. Client báo lỗi và thoát với mã 1
nếu không kết nối được hoặc hết thời gian chờ.

## 4. Bài 2 Cảm biến và giám sát định kỳ

Dừng server bài 1, mở terminal 1:

```powershell
..\.venv\Scripts\python.exe sensor_server_bai2.py
```

Terminal 2:

```powershell
..\.venv\Scripts\python.exe monitor_client_bai2.py
```

Server tự cập nhật mỗi **3 giây**, độc lập với yêu cầu GET. Nhiệt độ ngẫu nhiên 20–40 °C,
độ ẩm 30–80 %, làm tròn một chữ số thập phân. GET trả mẫu mới nhất,
Content-Format `application/json` (50), gồm đúng ba trường:

```json
{"device_id": "sensor01", "temperature": 28.5, "humidity": 65.2}
```

Client GET mỗi **3 giây**, in mã thiết bị, nhiệt độ, độ ẩm và thời điểm nhận.
Nhiệt độ **> 35** in `CANH BAO: Nhiet do cao`; độ ẩm **< 40** in `CANH BAO: Do am thap`.
Hai cảnh báo độc lập; giá trị bằng 35 và 40 không kích hoạt cảnh báo tương ứng.
Nếu không có cảnh báo, in `Trang thai: Binh thuong`.
Client báo lỗi và tiếp tục thử lại nếu mất phản hồi hoặc nhận dữ liệu sai.
Ctrl+C kết thúc giám sát.

Demo chắc chắn cả hai cảnh báo: dừng server cảm biến cũ rồi chạy lại:

```powershell
..\.venv\Scripts\python.exe sensor_server_bai2.py --temperature 36.1 --humidity 38.7
```

Kiểm tra hữu hạn bằng `monitor_client_bai2.py --count 2`; `--count 0` là chạy liên tục.
`--count` đếm số lần truy vấn, gồm cả lần bị lỗi. Có thể đổi chu kỳ bằng `--interval` ở server/client.
Giá trị cố định chỉ phục vụ demo; bỏ hai tùy chọn này để sinh dữ liệu ngẫu nhiên.

Có thể chọn cảm biến khác bằng `--device-id sensor02` ở **cả server và client**.
Muốn mô phỏng nhiều cảm biến cùng lúc, chạy mỗi server trên một cổng riêng rồi chọn đúng cổng và ID ở client.

## 5. Bài 3 Điều khiển đèn và Observe

Dừng server bài 2. Terminal 1:

```powershell
..\.venv\Scripts\python.exe light_server_bai3.py
```

Đợi server in `CoAP Smart Light Server started...`, rồi mở terminal 2 đăng ký giám sát:

```powershell
..\.venv\Scripts\python.exe light_monitor_bai3.py
```

Đợi `Observe registration successful`. Monitor nhận trạng thái ban đầu `OFF`.
Terminal 3 chạy controller:

```powershell
..\.venv\Scripts\python.exe light_controller_bai3.py
```

Nhập `ON`, `STATUS`, `OFF`, một lệnh sai như `HELLO`, rồi `EXIT`.

| Lệnh | Hành vi |
| --- | --- |
| `ON`, `OFF` | PUT JSON, in `Response Code: 2.04 Changed` và `Da bat den`/`Da tat den` |
| `STATUS` | GET trạng thái hiện tại, in JSON trạng thái |
| `EXIT` | Kết thúc controller |
| Lệnh khác | Báo lỗi đầu vào và tiếp tục chờ lệnh |

Controller chấp nhận chữ thường và bỏ khoảng trắng đầu/cuối. EOF cũng kết thúc controller.
Lỗi giao tiếp (server không chạy, hết thời gian chờ, mã lỗi CoAP) được báo rõ và controller tiếp tục chờ lệnh.

PUT gửi `application/json`:

```json
{"device_id": "light01", "command": "ON"}
```

GET, phản hồi PUT và thông báo Observe trả JSON trạng thái:

```json
{"device_id": "light01", "status": "ON"}
```

Monitor gửi **một GET với Observe=0**, rồi chờ thông báo trên đăng ký đó bằng async iterator;
không có vòng lặp GET định kỳ. Server dùng `ObservableResource` và gọi `updated_state()`
chỉ khi trạng thái thực sự thay đổi. PUT cùng trạng thái vẫn thành công nhưng không phát thông báo thừa.
Monitor in ID, trạng thái và thời điểm nhận thật cho trạng thái ban đầu và mỗi thay đổi.

Có thể mở nhiều terminal chạy `light_monitor_bai3.py`; tất cả đều nhận thay đổi.
Ctrl+C kết thúc monitor và hủy đăng ký cục bộ. Server dọn đăng ký khi phát hiện peer không còn nhận;
với CON, CoAP có thể gửi lại thông báo nếu chưa được xác nhận.
Nếu server chủ động kết thúc Observe hoặc có lỗi giao tiếp, monitor báo lỗi và thoát; chạy lại để đăng ký mới.
Không có thông báo mới khi đèn giữ nguyên trạng thái là hành vi bình thường.

Tùy chọn `--max-notifications 3` giúp demo hữu hạn: nhận trạng thái ban đầu và hai thay đổi rồi dừng.
Giá trị mặc định 0 là chạy đến Ctrl+C. Có thể mô phỏng `fan01` hoặc `pump01` bằng `--device-id`
ở cả ba chương trình. Mỗi server quản lý một thiết bị; dùng các cổng khác nhau khi chạy đồng thời.

Server từ chối JSON sai, sai ID hoặc lệnh khác ON/OFF bằng `4.00 Bad Request`,
và từ chối Content-Format khác JSON bằng `4.15 Unsupported Content Format`.
Các lỗi này không thay đổi trạng thái thiết bị.

## 6. Kiểm thử và kết quả

Chạy tại TH3:

```powershell
..\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
```

Bộ kiểm thử mở từng server bằng tiến trình riêng trên cổng UDP tạm thời, dùng client aiocoap
để trao đổi qua loopback rồi tự dừng các tiến trình. Không cần mở server 5683 trước.
Các trường hợp gồm GET/POST và lưu thông điệp; payload và thời điểm nhận; nhiều POST;
URI/phương thức sai; cảm biến ngẫu nhiên, tự cập nhật và chu kỳ GET mặc định 3 giây;
chọn sensor02; hai cảnh báo và ngưỡng bằng; dữ liệu cảm biến sai;
hai client Observe đồng thời; ON/OFF, GET trạng thái và PUT lặp không thông báo;
PUT sai JSON/ID/lệnh/Content-Format; chạy controller và monitor thực tế; server không hoạt động.

Đã chạy thành công **8 kiểm thử**. Log kiểm thử và log demo các chương trình thật được lưu tại
[docs/ket_qua_kiem_thu.txt](docs/ket_qua_kiem_thu.txt). Các timestamp trong log là thời gian chạy thực tế
theo đồng hồ máy kiểm thử; thông tin sinh viên trong log chỉ là dữ liệu thử.

## 7. File nộp và xử lý sự cố

Nộp 7 chương trình theo tên đề cùng `coap_common.py`, `requirements.txt`, `config.example.json`,
README và log minh chứng. `tests/` cung cấp cách tái hiện kiểm tra. Đề yêu cầu nộp qua GitHub.

- `Address already in use`: dừng server bài trước hoặc chọn cổng mới cho cả server/client.
- Không có phản hồi: kiểm tra server báo `SERVER READY` (bài 3: `CoAP Smart Light Server started...`), IP, cổng **UDP**, tường lửa và timeout.
- `4.04 Not Found`: kiểm tra `--device-id` và URI của server đang chạy.
- `ModuleNotFoundError`: chạy đúng Python trong `.venv` và cài `requirements.txt`.
- Không nhận Observe: chạy đúng `light_server_bai3.py`, đợi đăng ký thành công rồi đổi trạng thái đèn.

Tham khảo API: [aiocoap Resource và ObservableResource](https://aiocoap.readthedocs.io/en/latest/module/aiocoap.resource.html),
[transport UDP cho server](https://aiocoap.readthedocs.io/en/0.4.12/module/aiocoap.transports.simplesocketserver.html).
Phiên bản thư viện đã được cố định trong requirements; aiocoap 0.4.17 dùng các hàm `render_get`,
`render_post`, `render_put` viết thường khi định nghĩa tài nguyên.
