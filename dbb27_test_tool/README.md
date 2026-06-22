# DBB-27 Serial Test Tool

Công cụ web đọc & giải mã dữ liệu máy lọc thận Nikkiso DBB-27 qua USB↔RS232.
Có chế độ Mock để dev khi không có máy.

## Cài đặt

```
cd dbb27_test_tool
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Chạy

```
uvicorn backend.server:app --reload --port 8000
```

Mở http://localhost:8000

- **Mock**: chọn Nguồn = Mock, chọn scenario, bấm Kết nối.
- **Serial thật**: cắm adapter USB↔RS232, chọn Nguồn = Serial, chọn COM port, Baud 9600, Kết nối.

## Test

```
python -m pytest -v
```

## Đấu cáp RS232 (máy ↔ PC)

9600 8N1, no flow control. Dùng cáp RS232 9-pin **cross** (null-modem):
PC RXD(2) ↔ máy TXD(3), PC TXD(3) ↔ máy RXD(2), GND(5) ↔ GND(5).

## Giao thức (tóm tắt)

- PC gửi: `K` `CR` `LF`.
- Máy trả: `K2` + LEN(3) + RES-DATA + SUM(2 hex) + CR LF.
- 31 trường theo Table-2 (xem `backend/protocol.py`).
- **Điểm cần verify với máy thật:** cách tính checksum, định dạng treatment time, BP time — UI hiện raw + checksum nhận/tính để đối chiếu.

## Cấu trúc

```
backend/
  protocol.py   # build_command, parse_frame, checksum, FIELD_REGISTRY (pure logic)
  transport.py  # Transport base, SerialTransport, MockTransport
  mock.py       # sinh frame giả lập + scenarios + fault injection
  poller.py     # vòng lặp poll async, retry 3 lần
  logger.py     # ghi JSONL theo ngày
  server.py     # FastAPI: REST + WebSocket
frontend/
  index.html    # 1 trang hiển thị (HTML/JS thuần)
tests/          # pytest
```
