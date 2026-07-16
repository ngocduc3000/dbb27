# DBB-27 Fleet HL7/TCP Gateway + Realtime Dashboard — Design

**Goal:** Thu thập dữ liệu realtime từ ~50 máy lọc máu DBB-27 (Nikkiso) qua kết nối TCP/IP (mỗi máy gắn bộ chuyển đổi RS-232→Ethernet Moxa NPort), chuẩn hoá dữ liệu theo cấu trúc HL7 v2.x, lưu trữ và hiển thị realtime trên dashboard web.

**Bối cảnh:** Repo hiện có `dbb27_test_tool/` (Python, đọc 1 máy qua serial COM, dashboard local) và một plan chưa triển khai cho WPF desktop app (1 máy/serial, chưa scaffold). Dự án này là một hệ thống mới, quy mô nhiều máy qua mạng, không thay thế 2 dự án trên.

**Phạm vi giai đoạn này:**
- Theo dõi theo **Máy/Giường** (Device/Bed), **chưa** gắn bệnh nhân cụ thể — PID trong HL7 dùng DeviceId/BedId làm định danh tạm.
- HL7 là **chuẩn nội bộ** để chuẩn hoá & lưu trữ/API — chưa cần gửi ra HIS/EMR bên ngoài qua MLLP (cấu trúc sẵn sàng cho việc đó sau này nhưng không xây dựng transport MLLP thật trong phạm vi này).
- Chưa cần cảnh báo chủ động (email/SMS/âm thanh) — chỉ hiển thị trực quan trên dashboard qua realtime.

**Tech stack:** .NET 10 (ASP.NET Core, minimal hosting), Entity Framework Core, SignalR, Angular 17+ (không phải AngularJS 1.x), TypeScript, SQL Server hoặc PostgreSQL (tuỳ hạ tầng sẵn có của bệnh viện — quyết định khi viết plan).

---

## 1. Kiến trúc tổng thể

```
[Máy DBB-27] --RS232--> [Moxa NPort, cấu hình TCP Client]
   (×50)                        │
                                 │ TCP — mỗi NPort tự kết nối đến 1 IP:port cố định của server
                                 ▼
                    ┌─────────────────────────────────────┐
                    │   Dbb27.Api (ASP.NET Core / .NET 10) │
                    │                                       │
                    │  ┌─ Dbb27.Gateway (BackgroundService) │
                    │  │   TcpListener, 1 task/kết nối      │
                    │  │   → Dbb27.Protocol (parse frame)   │
                    │  ├─ Dbb27.Hl7 (map → ORU^R01)         │
                    │  ├─ Dbb27.Data (EF Core)              │
                    │  ├─ REST API (fleet, history, HL7)    │
                    │  └─ SignalR Hub (FleetHub)            │
                    └───────────────┬───────────────────────┘
                                    │ WebSocket (SignalR) + REST
                                    ▼
                        [Angular 17+ Dashboard SPA]
```

Kiến trúc là **modular monolith**: một ASP.NET Core host duy nhất, chia thành các project/module rõ trách nhiệm (không phải microservices). Được chọn thay vì tách tiến trình ingestion/API riêng hay microservices theo bounded-context, vì ở quy mô 50 thiết bị, một process là đủ đơn giản để build/vận hành mà không cần thêm hạ tầng (queue, service discovery, Redis backplane). TCP Gateway được tách thành `BackgroundService` độc lập trong process để dễ tách ra tiến trình riêng sau này nếu nhu cầu scale tăng.

**Đánh đổi đã chấp nhận:** redeploy API sẽ làm rớt tạm thời các kết nối TCP đang mở; NPort tự động reconnect nên không mất dữ liệu, chỉ gián đoạn vài giây.

### Nhận diện thiết bị

Mỗi NPort cấu hình trỏ về **1 IP:port duy nhất** của server (server là TCP Server, NPort là TCP Client — được chọn vì dễ mở rộng thêm máy, chỉ cần mở 1 cổng firewall phía server, không cần quản lý IP tĩnh của từng NPort trước). Gateway phân biệt máy nào dựa trên **IP nguồn của kết nối TCP đến**: bảng `Devices` ánh xạ `NPortIp → DeviceId/BedId`, admin cấu hình 1 lần khi lắp đặt máy mới.

---

## 2. Thành phần & trách nhiệm

| Project | Vai trò |
|---|---|
| `Dbb27.Protocol` | Port thuần C# (không phụ thuộc UI) của `dbb27_test_tool/backend/protocol.py` + `transport.py`: `FieldRegistry` (31 trường protocol DBB-27), `FrameParser` (STX/LEN/RES-DATA/SUM/ETX, checksum, decode giá trị), `ReferenceRanges` (khoảng tham khảo soft-alarm). Logic này đã được thiết kế và kiểm chứng chi tiết trong `docs/superpowers/plans/2026-07-08-dbb27-wpf-desktop-app.md` (Task 2-5) dù project đó chưa scaffold — lấy lại code đã verify từ plan đó, không viết lại từ đầu. |
| `Dbb27.Gateway` | `TcpListener` lắng nghe kết nối từ các NPort. Với mỗi kết nối: tra `Devices` theo IP nguồn để xác định DeviceId; vòng lặp gửi lệnh `K` mỗi ~1000ms (giữ nguyên chu kỳ poll gốc của protocol), đọc frame phản hồi, gọi `Dbb27.Protocol` để parse, cập nhật `DeviceState` vào cache trong bộ nhớ (`ConcurrentDictionary<DeviceId, DeviceState>`). Phát hiện mất kết nối (đọc lỗi liên tục / socket đóng) → đánh dấu máy Offline trong cache. |
| `Dbb27.Hl7` | Nhận `ParsedFrame` + `DeviceId` + timestamp, dựng message HL7 v2.x `ORU^R01` (chi tiết mục 3). |
| `Dbb27.Data` | EF Core `DbContext` với 3 bảng chính (chi tiết mục 4): `DeviceLatestState`, `ObservationHistory`, `AlarmEvents`, cộng bảng cấu hình `Devices`. |
| `Dbb27.Api` | ASP.NET Core host: REST endpoints (fleet overview, chi tiết máy, lịch sử, export HL7 thô), `FleetHub` (SignalR) broadcast mỗi khi cache đổi, và host `Dbb27.Gateway` như 1 hosted service. |
| `Dbb27.Api.Contracts` | DTO dùng chung, nguồn sự thật duy nhất cho REST + SignalR payload (chi tiết mục 6). |
| `dbb27-dashboard` (Angular 17+) | Lưới tổng quan 50 máy (trạng thái, cảnh báo nổi bật) + trang chi tiết từng máy (biểu đồ realtime các thông số). Nhận cập nhật qua SignalR client, gọi REST cho lịch sử/export. |

---

## 3. Ánh xạ HL7 v2.x

Mỗi khung DBB-27 giải mã hợp lệ (`ParsedFrame.Ok == true`) sinh 1 message `ORU^R01`:

- **MSH** — timestamp, định danh hệ thống gửi (`DBB27GW`), message control ID.
- **PID** — `DeviceId`/`BedId` làm định danh tạm thời (placeholder). Đây **không phải** patient ID thật — thiết kế để không phá cấu trúc PID khi sau này hệ thống gắn bệnh nhân thật, chỉ cần thay giá trị.
- **OBR** — mã phiên đo, tổ hợp timestamp + DeviceId.
- **OBX × 31** — mỗi trường trong `FieldRegistry` (UF goal, UF volume, UF rate, bơm máu, heparin, nhiệt độ dịch, độ dẫn điện, áp lực TM, áp lực dịch, TMP, thời gian điều trị, lưu lượng dịch, huyết áp, 9 cờ cảnh báo chính thức, chế độ điều trị...) → 1 `OBX` segment, mã định danh dùng **bảng mã nội bộ** (không phải LOINC chuẩn, vì không phải tất cả 31 trường có mã LOINC tương ứng), kèm đơn vị đo theo đúng protocol gốc (L, L/hr, mL/min, mmHg, °C, mS/cm...).

Message HL7 được build **theo mỗi frame hợp lệ nhận được** (không phải on-demand khi có request API), và lưu dạng text HL7 kèm frame gốc (raw hex) trong `ObservationHistory` — phục vụ audit/export qua API. Không xây dựng MLLP transport thật trong phạm vi này vì chưa có HIS đích cụ thể để gửi tới.

---

## 4. Lưu trữ & tần suất ghi

| Bảng | Mục đích | Tần suất ghi |
|---|---|---|
| `Devices` | Cấu hình tĩnh: DeviceId, BedId/tên hiển thị, NPortIp | Chỉ khi admin thêm/sửa máy |
| `DeviceLatestState` | 1 dòng/máy, luôn là trạng thái mới nhất — phục vụ nạp lại dashboard khi refresh trang | Upsert liên tục (mỗi frame hợp lệ, ~1s/máy) |
| `ObservationHistory` | Lịch sử số liệu + HL7 text + frame gốc, phục vụ báo cáo/audit | Ghi khi **giá trị đổi đáng kể** HOẶC snapshot định kỳ mỗi 30-60s (tránh mất dấu nền mà không ghi tràn lan mọi frame) |
| `AlarmEvents` | Lịch sử chuyển trạng thái của 9 cờ cảnh báo chính thức | Ghi **mọi lần chuyển trạng thái** (0→1 hoặc 1→0) — không bỏ sót, đây là dữ liệu an toàn quan trọng nhất |

Cache trong bộ nhớ (`ConcurrentDictionary`) luôn là nguồn cho SignalR broadcast (cập nhật mỗi giây, không chờ ghi DB xong), tách biệt hoàn toàn với chu kỳ ghi persistent — đảm bảo realtime dashboard không bị chậm bởi I/O database.

Với ~50 máy × 1 frame/giây, chọn chiến lược "ghi khi đổi + snapshot định kỳ" thay vì ghi mọi frame (sẽ ra ~4+ triệu dòng/ngày) để giảm tải DB mà vẫn đủ dữ liệu cho báo cáo/audit ở giai đoạn này.

---

## 5. Realtime & API

- **SignalR (`FleetHub`)**: broadcast `DeviceStateDto` mỗi khi cache của 1 máy đổi (giá trị số hoặc trạng thái alarm/online-offline). Angular client subscribe theo nhóm (group) hoặc nhận toàn bộ fleet tuỳ thiết kế chi tiết ở plan.
- **REST API** (indicative, chi tiết route ở plan):
  - `GET /api/fleet` — danh sách 50 máy + trạng thái mới nhất (`DeviceLatestState`).
  - `GET /api/devices/{id}` — chi tiết 1 máy.
  - `GET /api/devices/{id}/history?from=&to=` — lịch sử từ `ObservationHistory`.
  - `GET /api/devices/{id}/alarms` — lịch sử `AlarmEvents`.
  - `GET /api/devices/{id}/hl7/{observationId}` — export text HL7 thô của 1 bản ghi (audit/tích hợp sau này).

---

## 6. Model dùng chung frontend/backend

`Dbb27.Api.Contracts` định nghĩa DTO chuẩn (`DeviceStateDto`, `AlarmEventDto`, `FleetSummaryDto`, v.v.) làm nguồn sự thật duy nhất cho cả REST response và SignalR payload. Dùng OpenAPI (Swashbuckle) + codegen (NSwag hoặc `openapi-typescript`) để sinh TypeScript interface tương ứng cho Angular — đảm bảo model đồng bộ 2 phía, tránh phải duy trì tay 2 lần khi thêm/sửa field.

---

## 7. Xử lý lỗi & resilience

- **Frame lỗi** (checksum sai/timeout/thiếu byte): không crash — tăng bộ đếm lỗi của máy đó, giữ nguyên giá trị hiển thị cũ, đánh dấu "dữ liệu cũ" trên UI nếu không có frame mới hợp lệ sau N giây (giữ đúng tinh thần "ignore stale data khi không có dữ liệu mới" đã áp dụng trong `dbb27_test_tool` hiện có).
- **Mất kết nối TCP** từ 1 NPort: Gateway đánh dấu máy đó Offline trong cache, broadcast ngay qua SignalR; NPort tự động reconnect theo cấu hình của nó, Gateway nhận lại và map đúng DeviceId theo IP như cũ — không cần can thiệp thủ công.
- **Gateway/API restart**: toàn bộ kết nối TCP đang mở bị đóng; NPort tự retry kết nối lại; dashboard hiển thị "Đang kết nối lại" cho từng máy cho đến khi nhận frame đầu tiên sau restart.

---

## 8. Kiểm thử

- `Dbb27.Protocol`: xUnit, tái sử dụng bộ test đã thiết kế trong plan WPF trước đó (thuần logic, không phụ thuộc I/O).
- `Dbb27.Hl7`: test build ORU^R01 từ `ParsedFrame` mẫu, so khớp cấu trúc segment (MSH/PID/OBR/OBX) và số lượng OBX = số trường decode được.
- `Dbb27.Gateway`: test map DeviceId theo IP nguồn (giả lập), test hành vi khi mất kết nối (đánh dấu Offline, không crash vòng lặp các kết nối khác).
- `Dbb27.Data`: test logic "ghi khi đổi giá trị / snapshot định kỳ" — đảm bảo không ghi tràn lan, không bỏ sót alarm.
- Angular: test component lưới fleet hiển thị đúng theo `DeviceStateDto`, test xử lý mất/khôi phục kết nối SignalR.

---

## Ngoài phạm vi (out of scope) giai đoạn này

- Gắn bệnh nhân thật vào phiên đo (PID thật) — để giai đoạn sau.
- Gửi HL7 qua MLLP tới HIS/EMR bên ngoài thật sự — cấu trúc sẵn sàng nhưng transport chưa xây.
- Cảnh báo chủ động qua email/SMS/âm thanh — chỉ hiển thị trực quan trên dashboard.
- Chọn cụ thể SQL Server hay PostgreSQL — quyết định khi viết implementation plan tuỳ hạ tầng sẵn có.
