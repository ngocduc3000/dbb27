# DBB-27 Serial Test Tool (WPF Desktop)

Ứng dụng desktop Windows (WPF/.NET 8) kết nối máy lọc thận Nikkiso DBB-27 qua
cổng RS-232 (USB↔RS232 adapter) hoặc chế độ Mock, hiển thị đầy đủ 31 thông số
theo Nikkiso Communication Protocol, với cảnh báo hai tầng (cờ alarm chính thức
từ máy + cảnh báo mềm theo khoảng tham khảo).

Đây là bản viết lại (C#/WPF) của công cụ web Python tại `../dbb27_test_tool/`;
xem thiết kế đầy đủ tại
`../docs/superpowers/specs/2026-07-08-dbb27-wpf-desktop-app-design.md`.

## Chạy khi phát triển

```bash
dotnet run --project Dbb27.App/Dbb27.App.csproj
```

## Chạy test

```bash
dotnet test Dbb27.Tests/Dbb27.Tests.csproj
```

## Đóng gói .exe portable

```bash
dotnet publish Dbb27.App/Dbb27.App.csproj -c Release
```

File chạy được nằm tại
`Dbb27.App/bin/Release/net8.0-windows/win-x64/publish/Dbb27.App.exe` — một
file duy nhất, tự chứa .NET runtime, chạy trực tiếp trên Windows không cần cài
thêm gì.

## Đấu nối phần cứng

- Cáp RS-232 9 chân, đấu chéo (cross/null-modem), qua adapter USB↔RS232.
- Cấu hình cổng: 9600 bps, 8 data bit, 1 stop bit, không parity, không điều
  khiển luồng (Xon/Xoff: none).
- Nếu không mở được cổng COM, app sẽ báo lỗi tiếng Việt cụ thể (rút/cắm lại
  adapter, đổi cổng USB, đóng phần mềm khác đang chiếm cổng) thay vì crash.

## Log

Mỗi lần đọc (kể cả frame lỗi) được ghi vào `logs/dbb27-YYYYMMDD.jsonl` cạnh file
`.exe`. Nút "Mở thư mục log" trong app mở thư mục này trực tiếp.
