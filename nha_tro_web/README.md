# Quản lý nhà trọ — Next.js + Supabase

Web quản lý nhà trọ: Next.js 16 (App Router, Server Actions) + Supabase (PostgreSQL, Auth, Row Level Security).
Triển khai miễn phí: Supabase Free + Vercel Hobby.

## Kiến trúc

```
Trình duyệt (PC / điện thoại)
   │ HTTPS
   ▼
Next.js trên Vercel
   ├─ proxy.ts        : kiểm tra đăng nhập, chưa đăng nhập → /login
   ├─ app/**/page.tsx : trang (render phía server)
   ├─ app/actions.ts  : ghi dữ liệu (Server Actions) + kiểm tra đầu vào
   └─ lib/billing.ts  : công thức tính tiền (hàm thuần, có unit test)
   │ supabase-js (quyền của user đang đăng nhập)
   ▼
Supabase
   ├─ Auth : email + mật khẩu
   └─ Postgres : phong, nguoi_thue, chi_so, hoa_don, cau_hinh
                 RLS: mỗi tài khoản chỉ thấy dữ liệu của mình
                 CHECK: chỉ số mới >= cũ, tổng = phòng + điện + nước + phí khác
```

## Tính năng

| Mục | Nội dung |
|---|---|
| Phòng | Số phòng, tầng, diện tích, giá **tháng**, giá **ngày**, số người tối đa, trống / có người |
| Người ở trọ | Họ tên, CCCD, SĐT, ngày sinh, quê quán, ngày vào, ngày ra (trả phòng) |
| Chỉ số điện nước | Ghi theo ngày; chặn chỉ số nhỏ hơn lần ghi trước / lớn hơn lần ghi sau |
| Hóa đơn tháng | Giá tháng + (điện mới − cũ) × đơn giá + (nước mới − cũ) × đơn giá + phí khác |
| Hóa đơn ngày | Giá ngày × số ngày (tính cả ngày đầu và cuối) + điện + nước + phí khác |
| Thu tiền | Xác nhận đã thu / hủy, lọc theo tháng và trạng thái, in hóa đơn |
| Đơn giá | Đơn giá điện, nước; lưu cố định vào từng hóa đơn lúc tạo |

## Triển khai — từng bước

### Bước 1. Tạo project Supabase
1. Vào https://supabase.com → **New project** (Free). Region gần VN: Singapore.
2. **SQL Editor** → **New query** → dán toàn bộ `supabase/schema.sql` → **Run**.
   - Kiểm tra: **Table Editor** thấy 5 bảng `cau_hinh, phong, nguoi_thue, chi_so, hoa_don`, mỗi bảng có nhãn RLS enabled.

### Bước 2. Tạo tài khoản đăng nhập
1. **Authentication → Users → Add user → Create new user**: nhập email + mật khẩu, tick *Auto Confirm User*.
2. Tắt đăng ký công khai: **Authentication → Sign In / Providers** → tắt *Allow new users to sign up*.
   (App không có trang đăng ký; tắt mục này để người lạ không tự tạo tài khoản qua API.)

### Bước 3. Chạy trên máy
```bash
cd nha_tro_web
npm install
cp .env.example .env.local     # Windows: copy .env.example .env.local
```
Điền `.env.local` từ **Project Settings → API Keys** (và Project URL):
```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...   # hoặc anon key (legacy)
```
```bash
npm run dev        # http://localhost:3000
```
- Kiểm tra: mở `/` → tự chuyển `/login` → đăng nhập bằng tài khoản ở Bước 2 → vào Tổng quan.

### Bước 4. Đưa lên Vercel (miễn phí)
1. https://vercel.com → **Add New → Project** → chọn repo GitHub này.
2. **Root Directory**: `nha_tro_web`.
3. **Environment Variables**: thêm 2 biến như `.env.local`.
4. **Deploy** → mở URL Vercel cấp, đăng nhập.

## Quy trình hằng tháng
1. **Đơn giá**: đặt giá điện, nước (1 lần).
2. **Phòng** → thêm phòng → vào phòng → **Thêm người ở**.
3. Cuối kỳ: ghi **chỉ số điện nước** từng phòng.
4. **Tạo hóa đơn**: chọn phòng, loại, kỳ → *Lấy chỉ số* (cũ = lần ghi gần nhất ≤ ngày bắt đầu, mới = lần ghi gần nhất ≤ ngày kết thúc) → kiểm tra → tạo.
5. Thu tiền → **Xác nhận đã thu** → **In hóa đơn** nếu cần.

## Kiểm tra mã nguồn
```bash
npm test           # unit test công thức tính tiền
npm run typecheck  # TypeScript
npm run build      # build production
```

## Lưu ý gói miễn phí
- Theo chính sách Supabase hiện tại, project Free có thể bị **tạm dừng khi không hoạt động** một thời gian; vào Dashboard bấm *Restore* để chạy lại. Kiểm tra điều khoản mới nhất tại https://supabase.com/pricing.
- **Sao lưu**: tự xuất định kỳ. Lấy connection string ở **Connect** trên Dashboard:
  ```bash
  pg_dump "postgresql://postgres.<ref>:<password>@<host>:5432/postgres" -n public -Fc -f nhatro_YYYYMMDD.dump
  ```

## Cấu trúc thư mục
```
nha_tro_web/
├── supabase/schema.sql      # bảng, ràng buộc, RLS
├── proxy.ts                 # bảo vệ trang, làm mới session
├── app/
│   ├── actions.ts           # Server Actions (ghi dữ liệu)
│   ├── layout.tsx, globals.css
│   ├── login/  phong/  nguoi-thue/  chi-so/  hoa-don/  cau-hinh/
├── components/              # form, bảng hóa đơn, nút
└── lib/
    ├── billing.ts (+ .test.ts)
    ├── data.ts              # truy vấn dùng chung
    ├── format.ts            # tiền VNĐ, ngày giờ VN
    └── supabase/            # client phía server
```
