# DBB-27 Serial Test Tool — Design Spec

- **Ngày:** 2026-06-22
- **Tác giả:** nngocduc87 (với Claude Code)
- **Trạng thái:** Đã duyệt thiết kế, chờ review spec

## 1. Bối cảnh & mục tiêu

Hệ thống tổng thể (định hướng tương lai): máy lọc thận **Nikkiso DBB-27** → gateway RS232↔WiFi → TCP qua router → máy tính bác sĩ chạy dashboard quản lý nhiều máy.

**Phạm vi của spec này là Phase 1:** một **công cụ web chạy trên máy tính cá nhân** để kết nối trực tiếp với máy DBB-27 qua adapter **USB↔RS232**, nhằm **xác minh đọc và giải mã đúng dữ liệu** theo Nikkiso Communication Protocol.

Mục tiêu chính (đã chốt với người dùng):
- Đây là **công cụ kiểm thử/giải mã (test/decode tool)**, không phải dashboard cuối.
- Người dùng **có máy thật nhưng không truy cập liên tục** → cần **bộ giả lập (mock)** để dev hằng ngày và **chế độ serial thật** để verify.
- Hướng kỹ thuật đã chọn: **FastAPI + WebSocket + một trang web tĩnh**.

### Tiêu chí thành công
- Gửi đúng lệnh `K␍␊` và nhận được frame phản hồi từ máy thật.
- Parse được 31 trường theo Table-2; hiển thị **raw hex song song giá trị đã giải mã**.
- Đối chiếu được **checksum nhận vs tính** để phát hiện sai lệch.
- Chạy được hoàn toàn ở chế độ **mock** khi không có máy.
- Ghi log mọi lần đọc (kể cả frame lỗi) để phân tích protocol.

## 2. Tóm tắt giao thức (nguồn: Nikkiso Communication Protocol for DBB-27, 2019-09-12)

**Cấu hình serial:** RS-232C, 9600 bps, 8 data bit, 1 stop bit, no parity, no flow control (Xon/Xoff none), ASCII, half-duplex. Cáp RS232 9-pin **cross**. (Máy cũng có cổng RJ45 TCP/IP — dùng cho phase sau.)

**Mô hình:** PC gửi command → máy trả response (request/response).

**Command (PC → máy):** 3 byte — `"K"` `CR` `LF` (0x4B 0x0D 0x0A).

**Response (máy → PC):** độ dài thay đổi:

| Vùng | Nội dung |
|------|----------|
| STX | 2 byte: `"K"` `"2"` (start code + version number) |
| LEN | 3 byte ASCII thập phân = tổng số byte của vùng RES-DATA (tất cả "ID"+"DATA") |
| RES-DATA | độ dài thay đổi: chuỗi các trường `ID(1 byte) + DATA` |
| SUM | 2 byte checksum (xem mục mơ hồ bên dưới) |
| ETX | 2 byte: `CR` `LF` |

**Quy ước dữ liệu (Appendix):**
- Mục 1–12: 5 chữ số thập phân có dấu chấm. Âm thì ký tự đầu là `-`. VD UF goal 2.35L → `0 2 . 3 5`; áp lực -146mmHg → `- 0 1 4 6`.
- Treatment time < 479 phút.
- Cảnh báo (13–20, 31): `1` = alarm, `0` = không.
- Mục 20 "Other alarm" = mọi alarm ngoài 13–19 và 31.
- Under treatment flag (ID `M`): `1` đang điều trị (Connection/Treatment/Disconnect), `0` không.
- Treatment mode (ID `N`): HD = `0`, ECUM = `1`.
- *Lưu ý:* tài liệu gốc đánh số lệch — Appendix (5) gọi "No.22" là Under treatment flag, nhưng Table-2 ghi No.21=`M` (Under treatment flag), No.22=`N` (Treatment mode). **Spec này lấy ID code (`M`,`N`) làm chuẩn**, không dựa vào số thứ tự, nên không ảnh hưởng parser.
- BP measurement time: ký pháp 24 giờ.
- Mục 23–26 (substitution): xuất `0x30` vì máy không dùng.
- Kết quả huyết áp mới nhất ở mục 27–30.

**Bảng trường (Table-2):**

| No | Tên | ID | Size | Đơn vị |
|----|-----|----|------|--------|
| 1 | UF goal | A | 5 | L |
| 2 | UF volume | B | 5 | L |
| 3 | UF rate | C | 5 | L/hr |
| 4 | Blood pump flow rate | D | 5 | mL/min |
| 5 | Infusion (Heparin) pump rate | E | 5 | mL/hr |
| 6 | Dialysate temperature | F | 5 | °C |
| 7 | Dialysate conductivity | G | 5 | mS/cm |
| 8 | Venous pressure | H | 5 | mmHg |
| 9 | Dialysate pressure | I | 5 | mmHg |
| 10 | TMP | J | 5 | mmHg |
| 11 | Treatment time | K | 5 | min |
| 12 | Dialysate flow rate | L | 5 | mL/min |
| 13 | Dialysate temperature alarm | a | 1 | — |
| 14 | Conductivity alarm | b | 1 | — |
| 15 | Venous pressure alarm | c | 1 | — |
| 16 | Dialysate pressure alarm | d | 1 | — |
| 17 | TMP alarm | e | 1 | — |
| 18 | Air alarm | f | 1 | — |
| 19 | Blood leak alarm | g | 1 | — |
| 20 | Other alarm | h | 1 | — |
| 21 | Under treatment flag | M | 1 | — |
| 22 | Treatment mode | N | 1 | — |
| 23 | Substitution goal | O | 5 | L (unused) |
| 24 | Substitution volume | P | 5 | L (unused) |
| 25 | Substitution rate | Q | 5 | L/hr (unused) |
| 26 | Substitution temperature | R | 5 | °C (unused) |
| 27 | Blood pressure measurement time | S | 5 | HHMMSS |
| 28 | Systolic blood pressure | T | 5 | mmHg |
| 29 | Diastolic blood pressure | U | 5 | mmHg |
| 30 | Pulse | V | 5 | bpm |
| 31 | Blood pressure alarm | i | 1 | — |

### Điểm mơ hồ cần xác minh với máy thật (lý do tồn tại của công cụ)
1. **Checksum (SUM):** tài liệu ghi "cộng tất cả data size trừ CR,LF, lấy 2 chữ số HEX cuối, mã hóa ASCII". Cách tính chính xác (cộng giá trị byte nào, phạm vi từ đâu đến đâu) cần đối chiếu thực tế. → Công cụ **luôn hiển thị checksum nhận vs tính** để lộ sai lệch; logic tính tách riêng, dễ chỉnh.
2. **Treatment time (K):** ghi "5 chữ số có dấu thập phân" nhưng đơn vị phút (<479) — định dạng thực cần xem frame thật.
3. **BP time (S):** `HHMMSS` là 6 ký tự nhưng tài liệu liệt kê 5 byte — cần xác minh; parser sẽ đọc theo độ dài thực tế quan sát được và cảnh báo nếu lệch.

Triết lý: **không tin tuyệt đối tài liệu**; hiển thị raw để con người xác nhận, parser chỉnh theo dữ liệu thật của máy người dùng.

## 3. Kiến trúc

```
Máy DBB-27 ──USB↔RS232──► Backend (FastAPI) ──WebSocket(JSON)──► Trang web
                            │
                            ├─ transport: SerialTransport | MockTransport
                            ├─ protocol:  build_command / parse_frame / checksum / FIELD_REGISTRY
                            ├─ poller:    vòng lặp poll ~1s + retry 3 lần
                            └─ logger:    ghi raw + decoded (JSONL/CSV)
```

Nguyên tắc: mỗi module một nhiệm vụ, giao tiếp qua interface rõ ràng, test độc lập.

### 3.1 `protocol.py` (lõi, thuần logic, không I/O)
- `build_command() -> bytes`: trả `b"K\r\n"`.
- `FIELD_REGISTRY`: ánh xạ `ID -> {name, size, unit, kind}` với `kind ∈ {decimal5, flag1, bptime, unused}`.
- `parse_frame(raw: bytes) -> ParsedFrame`: tách STX/LEN/RES-DATA/SUM/ETX; duyệt RES-DATA theo ID (không phụ thuộc thứ tự); giải mã từng trường; tính checksum và so với nhận; trả về cấu trúc gồm: `decoded` (dict), `raw_hex`, `len_recv`, `checksum_recv`, `checksum_calc`, `ok`, `field_count`, `errors[]`.
- Không raise khi frame hỏng — gom lỗi vào `errors[]` để UI hiển thị và logger ghi lại.

### 3.2 `transport.py`
- `Transport` (base): `open()`, `close()`, `send(bytes)`, `read_frame(timeout) -> bytes`.
- `SerialTransport`: dùng `pyserial` (9600 8N1, no flow control). Đọc đến `CR LF` kết thúc frame hoặc timeout.
- `MockTransport`: gọi `mock.generate_frame(scenario)`.

### 3.3 `mock.py`
- `generate_frame(scenario) -> bytes`: dựng frame hợp lệ với `LEN`/`SUM` **tính thật**.
- Sinh 31 trường trong khoảng sinh lý hợp lý, có tương quan (TMP ≈ áp lực TM − áp lực dịch; UF volume tăng theo treatment time; treatment time tăng dần).
- Scenarios: `normal`, `treatment_hd`, `treatment_ecum`, `alarm` (bật cờ air/blood-leak/áp lực…), `bp_measure`, `bad_frame`.
- Fault injection: chèn byte rác / sai checksum / LEN sai / cắt ngắn frame theo xác suất cấu hình.

### 3.4 `poller.py`
- Vòng lặp async: `send(command)` → `read_frame()` → `parse_frame()` → phát kết quả qua callback (server đẩy WebSocket) → `logger.write()`.
- Retry tối đa **3 lần** khi timeout/đọc lỗi (theo khuyến nghị tài liệu) trước khi đánh dấu frame lỗi.
- Chu kỳ poll cấu hình được (mặc định 1000 ms).

### 3.5 `logger.py`
- Ghi JSONL: `logs/dbb27-YYYYMMDD.jsonl`, một bản ghi mỗi lần poll (gồm cả frame lỗi).
- Xuất CSV tùy chọn (mỗi trường một cột).
- Xoay log theo ngày; hỗ trợ tải về từ UI.

Mẫu bản ghi:
```json
{"ts":"2026-06-22T14:32:06.512","source":"serial","raw_hex":"4B32...","len_recv":156,
 "checksum_recv":"5a","checksum_calc":"5a","ok":true,"decoded":{"uf_goal":2.35},"error":null}
```

### 3.6 `server.py` (FastAPI)
- REST:
  - `GET /api/ports` — liệt kê COM port (`pyserial.tools.list_ports`).
  - `POST /api/connect` — `{source: serial|mock, port, baud, poll_ms, scenario}` → khởi động poller.
  - `POST /api/disconnect` — dừng poller, đóng transport.
  - `GET /api/log/download` — tải file log.
- WebSocket `/ws` — đẩy mỗi kết quả parse (raw + decoded + checksum + đếm frame/lỗi).
- Phục vụ `frontend/index.html` tĩnh.

### 3.7 `frontend/index.html`
- HTML + JS thuần, không build step. Mặc định tiếng Việt.
- Khối: thanh kết nối; bảng 12 thông số đo; bảng 9 cảnh báo; khối huyết áp; khối trạng thái điều trị; khối RAW/debug (hex+ASCII, checksum nhận/tính, LEN, số trường, bộ đếm frame/lỗi); log cuộn + nút tải log; điều khiển mock (scenario, fault injection).

## 4. Xử lý lỗi
- **Timeout đọc:** retry ≤3 lần, sau đó đánh dấu frame lỗi và tiếp tục poll (không crash).
- **Sai checksum / LEN lệch / thiếu byte / byte rác:** bắt trong `parse_frame`, báo lý do cụ thể lên UI + ghi log, vẫn hiển thị raw.
- **Cổng COM bận / không tồn tại / rút cáp giữa chừng:** báo lỗi rõ, cho phép kết nối lại, không treo server.
- **Trường thiếu/thừa:** hiển thị `field_count` (vd `28/31`) để biết frame có khớp Table-2 không.

## 5. Kiểm thử
- `tests/test_protocol.py`: test `parse_frame` với frame mẫu hợp lệ và các frame lỗi (sai checksum, LEN sai, thiếu byte, byte rác), test `build_command`, test giải mã từng `kind` (decimal5 âm/dương/có chấm, flag1, bptime).
- Mock + parser dùng chung định nghĩa frame nên giả lập là phép thử end-to-end của parser.

## 6. Cấu trúc dự án
```
dbb27_test_tool/
├── backend/
│   ├── protocol.py
│   ├── transport.py
│   ├── mock.py
│   ├── poller.py
│   ├── logger.py
│   └── server.py
├── frontend/
│   └── index.html
├── tests/
│   └── test_protocol.py
├── logs/                  # tự tạo khi chạy
├── requirements.txt       # fastapi, uvicorn, pyserial
└── README.md              # cách chạy + sơ đồ cáp RS232 9-pin cross
```
App Streamlit cũ (`filtration_dashboard/`) giữ nguyên; đây là dự án độc lập.

## 7. Ngoài phạm vi (YAGNI cho Phase 1)
- Gateway RS232↔WiFi, transport TCP/IP (Phase sau — `protocol.py` tái dùng được, chỉ thêm `TcpTransport`).
- Quản lý nhiều máy, đăng nhập/người dùng, cơ sở dữ liệu lâu dài, biểu đồ lịch sử dài hạn.
- Cảnh báo qua âm thanh/đẩy thông báo, in báo cáo.

## 8. Định hướng tái dùng cho Phase sau
`protocol.py` (parse/checksum/registry) và data model độc lập transport → khi chuyển sang TCP qua gateway chỉ cần thêm `TcpTransport` cùng interface `Transport`, phần giải mã và UI tái dùng gần như nguyên vẹn.
