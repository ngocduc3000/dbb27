# DBB-27 Windows Desktop App (WPF) — Design Spec

- **Ngày:** 2026-07-08
- **Tác giả:** nngocduc87 (với Claude Code)
- **Trạng thái:** Đã duyệt thiết kế, chờ review spec

## 1. Bối cảnh & mục tiêu

Bản Phase 1 hiện có (`dbb27_test_tool/`) là công cụ **web** (Python FastAPI + WebSocket + HTML tĩnh) để kết nối trực tiếp máy lọc thận **Nikkiso DBB-27** qua adapter USB↔RS232, xác minh đọc/giải mã dữ liệu theo Nikkiso Communication Protocol. Toàn bộ logic giao thức (`backend/protocol.py`, `transport.py`, `mock.py`, `poller.py`, `logger.py`) đã viết và test xong, đã verify với máy thật (nhiều commit fix: STX parsing, disconnect state, stale-data khi mất kết nối, banner lỗi serial...).

**Mục tiêu của spec này:** viết lại thành một **ứng dụng desktop Windows native (WPF/.NET 8)**, giao diện hiện đại (Fluent/Windows 11 style), hiển thị đầy đủ 31 thông số, có nghiệp vụ cảnh báo hai tầng (cứng + mềm), kết nối qua serial (COM) hoặc chế độ Mock để dev/demo khi không có máy thật.

Đây là **viết lại (rewrite) sang C#**, không phải wrapper của bản Python — quyết định đã chốt với người dùng (đánh đổi: mất thời gian hơn nhưng .exe gọn nhẹ, giao diện WPF native mượt hơn). Toàn bộ logic giao thức/mock/parser phải được port và test lại từ đầu bằng C#, đối chiếu với hành vi đã xác nhận của bản Python (dùng làm tài liệu tham chiếu, không dùng lại code).

### Tiêu chí thành công
- Gửi đúng lệnh `K\r\n` và nhận, giải mã đúng frame phản hồi từ máy thật DBB-27 qua cổng COM.
- Parse đủ 31 trường theo Table-2; hiển thị đầy đủ trên giao diện, nhóm theo khối chức năng.
- Đối chiếu checksum nhận vs tính, hiển thị ở khối debug.
- Chạy được hoàn toàn ở chế độ Mock khi không có máy (dev/demo).
- Cảnh báo cứng (9 cờ từ máy) và cảnh báo mềm (12 thông số số vượt khoảng tham khảo) hiển thị tách biệt, rõ ràng, không gây nhầm lẫn lâm sàng.
- Ghi log mọi lần đọc (kể cả frame lỗi) ra file JSONL.
- Build ra 1 file `.exe` portable, tự chứa (self-contained), chạy trực tiếp trên Windows không cần cài .NET runtime riêng.

## 2. Giao thức (nguồn: Nikkiso Communication Protocol for DBB-27, 2019-09-12 — xem chi tiết đầy đủ trong `docs/superpowers/specs/2026-06-22-dbb27-serial-test-tool-design.md` mục 2, và bảng giới hạn tham khảo trong `dbb27_test_tool/tools/gen_param_doc.py`)

Tóm tắt (không lặp lại chi tiết, tham chiếu file trên):
- RS-232C, 9600 8N1, no parity, no flow control, ASCII, half-duplex.
- Command PC→máy: `"K" CR LF` (3 byte).
- Response: `STX(2: "K""2") + LEN(3 ascii digit) + RES-DATA(chuỗi ID+DATA) + SUM(2 hex ascii) + ETX(CR LF)`.
- 31 trường theo Table-2, đọc bằng ID (1 ký tự ASCII), không phụ thuộc thứ tự.
- Các điểm mơ hồ cần xác minh với máy thật (checksum, treatment time, BP time) giữ nguyên triết lý: **hiển thị raw để đối chiếu**, không tin tuyệt đối tài liệu.
- Bảng khoảng tham khảo (dùng cho cảnh báo mềm) lấy từ `PARAMS` trong `gen_param_doc.py` (12 thông số số: UF goal/volume/rate, blood pump flow, heparin rate, dialysate temp/conductivity/pressure, venous pressure, TMP, treatment time, dialysate flow, BP systolic/diastolic/pulse).

## 3. Kiến trúc

```
Máy DBB-27 ──USB↔RS232──► Dbb27.Core (Transport/Protocol/Poller) ──event──► Dbb27.App (WPF, MVVM)
```

```
Dbb27.Core/              (class library .NET 8, không phụ thuộc UI)
├── Protocol/
│   ├── FieldRegistry.cs      # 31 Field: Id, Key, NameVi, Size, Unit, Kind, Decimals
│   ├── FrameParser.cs        # BuildCommand(), ParseFrame(), ComputeChecksum(), DecodeValue()
│   └── ReferenceRanges.cs    # (Key -> (min,max)) cho 12 thông số số, dùng cho cảnh báo mềm
├── Transport/
│   ├── ITransport.cs         # Open/Close/Send/ReadFrame(timeout)/Abort
│   ├── SerialTransport.cs    # System.IO.Ports.SerialPort, 9600 8N1, dịch lỗi mở cổng thân thiện
│   └── MockTransport.cs
├── Mock/
│   └── MockFrameGenerator.cs # scenarios: normal, treatment_hd, treatment_ecum, alarm, bp_measure, bad_frame; fault injection (checksum/truncate/garbage)
├── Polling/
│   └── FramePoller.cs        # vòng lặp: send -> read (retry <=3) -> parse -> log -> event kết quả; đếm frames_total/frames_error
└── Logging/
    └── FrameLogger.cs        # JSONL, 1 dòng/lần poll, xoay file theo ngày (dbb27-YYYYMMDD.jsonl)

Dbb27.App/                (WPF, .NET 8, MVVM: CommunityToolkit.Mvvm + WPF-UI cho Fluent/Windows 11 UI)
├── Views/                 # MainWindow + UserControl theo khối (ConnectionBar, MeasurementGrid, AlarmPanel, TreatmentBlock, BloodPressureBlock, RawDebugPanel, LogPanel, MockControls)
├── ViewModels/
└── Assets/

Dbb27.Tests/               (xUnit)
```

Nguyên tắc: mỗi lớp một nhiệm vụ, `Dbb27.Core` không có dependency lên WPF, test độc lập được. `Dbb27.App` chỉ subscribe event từ `FramePoller` và bind dữ liệu lên UI qua ViewModel.

### 3.1 Protocol (Core)
- `BuildCommand()` → `byte[] { 'K', '\r', '\n' }`.
- `FieldRegistry`: danh sách tĩnh 31 `Field` record (id, key, tên VI, size, đơn vị, kind ∈ {Decimal5, Flag1, BpTime, Unused}, decimals).
- `ParseFrame(byte[] raw) -> ParsedFrame`: tách STX/LEN/RES-DATA/SUM/ETX, duyệt RES-DATA theo ID, giải mã từng trường, tính checksum so với nhận. Không throw khi frame hỏng — gom lỗi vào `Errors` (list string tiếng Việt, y hệt nội dung thông báo bản Python) để UI và logger dùng chung.
- `ReferenceRanges`: dict tra `(min, max)` theo `Key`; hàm `IsOutOfRange(key, value)` dùng cho cảnh báo mềm.

### 3.2 Transport (Core)
- `SerialTransport`: mở cổng COM (9600, 8, None, One, không flow control), đọc đến khi gặp `\r\n` hoặc hết timeout (đọc theo lát ngắn để `Abort()` phản hồi nhanh khi ngắt kết nối). Dịch lỗi mở cổng (PermissionError/"not functioning"/"access denied" trên Windows) thành hướng dẫn tiếng Việt cụ thể (rút cắm lại adapter, đổi cổng USB, đóng phần mềm khác đang chiếm cổng).
- `MockTransport`: gọi `MockFrameGenerator.GenerateFrame(scenario, faultRate, alarms)`.

### 3.3 Mock (Core)
- Sinh 31 trường giá trị hợp lý về mặt sinh lý (venous pressure, TMP = venous − dialysate pressure, v.v., như bản Python).
- Scenarios: `normal`, `treatment_hd`, `treatment_ecum`, `alarm`, `bp_measure`, `bad_frame`.
- Cho phép UI chọn bật từng cờ alarm riêng lẻ (checkbox) + tỷ lệ fault injection (checksum sai / cắt ngắn / byte rác).
- Mock tự tính LEN/SUM thật (không hard-code) để làm test round-trip cho parser.

### 3.4 Poller (Core)
- Vòng lặp trên background thread (`Task.Run`): gửi lệnh → đọc frame (retry tối đa 3 lần khi timeout) → `ParseFrame` → phát event kết quả (kèm `FramesTotal`/`FramesError`) → ghi log. Chu kỳ poll cấu hình được (mặc định 1000ms).
- Khi không nhận được dữ liệu sau retry: phát record "không có dữ liệu" (không phải lỗi phân tích), tiếp tục poll, không dừng.
- `Stop()` gọi `Transport.Abort()` để không race với `Close()` khi đang đọc dở dang trên thread khác.

### 3.5 Logger (Core)
- Ghi JSONL `logs/dbb27-YYYYMMDD.jsonl`, 1 bản ghi mỗi lần poll (kể cả lỗi/no-data), giữ đúng field set bản Python (`ts, source, raw_hex, len_recv, len_calc, checksum_recv, checksum_calc, ok, field_count, decoded, error, frames_total, frames_error, connection_error`) để tương thích công cụ phân tích log đã quen dùng.
- Nút "Tải log" trong UI mở thư mục log hoặc export ra vị trí người dùng chọn.

## 4. Giao diện (Dbb27.App)

Một cửa sổ chính duy nhất (không cần multi-page navigation — app nhỏ, ưu tiên nhìn thấy mọi thứ ngay), dùng WPF-UI (Fluent Design: card, theme sáng/tối, bo góc, backdrop Mica) cho cảm giác Windows 11 hiện đại:

- **Thanh trên:** tên app, chấm trạng thái kết nối (xanh=đã kết nối / xám=chưa / đỏ=lỗi kết nối), toggle theme sáng/tối.
- **Thanh kết nối:** chọn nguồn Serial (dropdown cổng COM, baud cố định 9600) hoặc Mock (dropdown scenario, slider fault-rate, checkbox từng alarm); nút Kết nối/Ngắt kết nối; bộ đếm khung tổng/lỗi.
- **Khối thông số đo (12 stat tile dạng lưới):** nhãn nhỏ phía trên, số lớn, đơn vị bên cạnh — glanceable, viền vàng khi ngoài khoảng tham khảo (cảnh báo mềm).
- **Khối cảnh báo (9 chip):** xanh = bình thường, đỏ đậm + icon = alarm đang bật (cờ chính thức từ máy), luôn ưu tiên hiển thị rõ nhất bất kể theme.
- **Khối điều trị:** badge "Đang điều trị"/"Không điều trị", chế độ HD/ECUM, thời gian điều trị.
- **Khối huyết áp:** tâm thu/tâm trương/mạch, giờ đo gần nhất, chip cảnh báo huyết áp riêng.
- **Khối RAW/DEBUG (thu gọn được):** hex thô, LEN nhận/tính, SUM nhận/tính, field_count dạng "28/31", danh sách lỗi parse (nếu có).
- **Khối nhật ký:** log cuộn theo thời gian thực + nút tải log.

Khi mất kết nối: dừng poll ngay, reset toàn bộ card về trạng thái "--" (không giữ số liệu cũ gây hiểu nhầm là dữ liệu mới).

## 5. Nghiệp vụ cảnh báo

Hai tầng, hiển thị tách biệt để không gây nhầm lẫn lâm sàng:

1. **Cảnh báo cứng (chính thức từ máy):** 9 cờ `a,b,c,d,e,f,g,h,i` — `1` = alarm. Ưu tiên hiển thị cao nhất, không thể tắt/ẩn trên UI. Cờ `h` ("Cảnh báo khác") gộp mọi alarm ngoài 13-19,31 — kèm ghi chú "không rõ nguyên nhân cụ thể, xem thêm ở máy".
2. **Cảnh báo mềm (ước tính của app):** so 12 thông số số với `ReferenceRanges`; luôn kèm nhãn rõ ràng "khoảng tham khảo lâm sàng/kỹ thuật, KHÔNG phải ngưỡng cảnh báo chính thức của máy" (giữ đúng tinh thần cảnh báo ⚠ đã có trong `DBB-27_Thong_so_va_gioi_han.docx`).

`M` (under treatment) và `N` (treatment mode) hiển thị dạng badge trạng thái, không phải alarm, nhưng ảnh hưởng cách đọc số khác (VD UF rate chỉ có ý nghĩa khi đang điều trị).

## 6. Xử lý lỗi

- **Timeout đọc:** retry ≤3 lần, sau đó phát record "không có dữ liệu", tiếp tục poll, không crash.
- **Sai checksum / LEN lệch / thiếu byte / byte rác:** bắt trong `ParseFrame`, thông báo cụ thể bằng tiếng Việt ở khối debug + ghi log kèm hex thô.
- **Cổng COM bận / không tồn tại / rút cáp giữa chừng:** thông báo thân thiện, cho phép kết nối lại ngay không cần khởi động lại app.
- **Trường thiếu/thừa:** hiển thị `field_count` dạng "28/31".

## 7. Kiểm thử

`Dbb27.Tests` (xUnit), port lại `test_protocol.py`:
- `ParseFrame` với frame hợp lệ và các frame lỗi (sai checksum, LEN sai, thiếu byte, byte rác).
- `BuildCommand` đúng 3 byte.
- Giải mã từng `kind`: Decimal5 (âm/dương/có chấm), Flag1, BpTime.
- `MockFrameGenerator` sinh frame tự parse lại được (round-trip), trừ scenario `bad_frame`.
- `SerialTransport`/`FramePoller`: test logic retry và abort bằng transport giả lập (không cần cổng COM thật).

## 8. Đóng gói

`dotnet publish -r win-x64 --self-contained true -p:PublishSingleFile=true -c Release` → một file `.exe` portable duy nhất, không cần cài .NET runtime, chạy trực tiếp để test với máy DBB-27 thật. Chưa cần installer (MSIX/Setup.exe) ở giai đoạn này.

## 9. Ngoài phạm vi (YAGNI)

- Gateway RS232↔WiFi, transport TCP/IP (giữ `ITransport` để thêm `TcpTransport` sau này không đổi phần còn lại).
- Quản lý nhiều máy, đăng nhập/người dùng, cơ sở dữ liệu lâu dài, biểu đồ lịch sử dài hạn.
- Cảnh báo qua âm thanh/đẩy thông báo, in báo cáo, installer chuyên nghiệp.
- Bản Python `dbb27_test_tool/` (web) và `filtration_dashboard/` (Streamlit) giữ nguyên, không xóa — dự án WPF này độc lập, nằm ở thư mục mới (đề xuất: `dbb27_desktop_app/`).

## 10. Định hướng tái dùng cho Phase sau

`Dbb27.Core` độc lập với UI và với loại transport cụ thể → khi chuyển sang TCP qua gateway chỉ cần thêm `TcpTransport` cùng interface `ITransport`; phần parser/mock/logger và phần lớn UI tái dùng gần như nguyên vẹn.
