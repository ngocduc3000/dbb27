# Quản lý nhà trọ

Web app quản lý nhà trọ chạy cục bộ: Python + Flask + SQLite (một file `nhatro.db`, không cần cài database server).

## Tính năng

| Mục | Nội dung |
|---|---|
| Phòng | Số phòng, tầng, diện tích, giá thuê **tháng** và **ngày**, số người tối đa, trạng thái trống/có người |
| Người ở trọ | Họ tên, CCCD, SĐT, ngày sinh, quê quán, ngày vào, ngày ra (trả phòng) |
| Chỉ số điện nước | Ghi chỉ số đồng hồ theo ngày; chặn chỉ số nhỏ hơn lần ghi trước |
| Hóa đơn | Theo **tháng** (giá tháng) hoặc theo **ngày** (giá ngày × số ngày, tính cả ngày đầu và cuối); tiền điện = (mới − cũ) × đơn giá; tiền nước tương tự; phí khác |
| Thu tiền | Đánh dấu đã thu / hủy, lọc theo tháng và trạng thái, in hóa đơn |
| Đơn giá | Đơn giá điện, nước; được lưu cố định vào từng hóa đơn lúc tạo |

## Cài đặt và chạy

```bash
cd quan_ly_nha_tro
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Mở http://127.0.0.1:5000

Truy cập từ điện thoại trong cùng mạng LAN:

```bash
# Windows PowerShell: $env:NHATRO_HOST="0.0.0.0"; python run.py
NHATRO_HOST=0.0.0.0 python run.py
```

Biến môi trường:

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `NHATRO_DB` | `quan_ly_nha_tro/nhatro.db` | Đường dẫn file database |
| `NHATRO_HOST` | `127.0.0.1` | Địa chỉ lắng nghe |
| `NHATRO_PORT` | `5000` | Cổng |
| `NHATRO_SECRET` | (chuỗi mặc định) | Khóa phiên Flask — đổi khi triển khai |

## Quy trình sử dụng hằng tháng

1. **Đơn giá**: đặt giá điện, nước (1 lần).
2. **Phòng** → thêm phòng.
3. Vào phòng → **Thêm người ở**.
4. Cuối kỳ → ghi **chỉ số điện nước** cho từng phòng.
5. **Tạo hóa đơn**: chọn phòng, loại (tháng/ngày), kỳ → "Lấy chỉ số" (tự điền chỉ số cũ = lần ghi gần nhất ≤ ngày bắt đầu, chỉ số mới = lần ghi gần nhất ≤ ngày kết thúc) → kiểm tra → tạo.
6. Thu tiền → **Xác nhận đã thu**.

## Cấu trúc

```
quan_ly_nha_tro/
├── run.py              # điểm chạy
├── nhatro/
│   ├── billing.py      # công thức tính tiền (hàm thuần, có test)
│   ├── db.py           # kết nối SQLite, truy vấn dùng chung
│   ├── schema.sql      # bảng: phong, nguoi_thue, chi_so, hoa_don, cau_hinh
│   └── app.py          # route Flask
├── templates/          # giao diện HTML
└── tests/              # pytest: test_billing.py, test_app.py
```

## Kiểm tra

```bash
python -m pytest -q
```

## Sao lưu

Toàn bộ dữ liệu nằm trong một file `nhatro.db`. Sao lưu = copy file này (nên tắt app trước khi copy).

## Giới hạn hiện tại

- Chưa có đăng nhập. Chỉ nên chạy trong mạng nội bộ tin cậy.
- Chưa có giá điện bậc thang; dùng một đơn giá cố định.
