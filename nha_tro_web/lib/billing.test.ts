import { describe, expect, it } from "vitest";
import { BillingError, soNgayO, tieuThu, tinhHoaDon } from "./billing";

const co_ban = {
  giaThang: 3_000_000, giaNgay: 150_000, donGiaDien: 3_500, donGiaNuoc: 20_000,
};

describe("billing", () => {
  it("tiêu thụ = mới - cũ", () => {
    expect(tieuThu(100, 150, "điện")).toBe(50);
    expect(tieuThu(0, 0, "nước")).toBe(0);
  });

  it("chặn chỉ số mới < cũ", () => {
    expect(() => tieuThu(150, 100, "điện")).toThrow(BillingError);
  });

  it("số ngày tính cả hai đầu, qua tháng và năm nhuận", () => {
    expect(soNgayO("2026-10-01", "2026-10-01")).toBe(1);
    expect(soNgayO("2026-10-01", "2026-10-10")).toBe(10);
    expect(soNgayO("2028-02-01", "2028-03-01")).toBe(30);
    expect(soNgayO("2026-12-30", "2027-01-02")).toBe(4);
  });

  it("chặn ngày sai", () => {
    expect(() => soNgayO("2026-10-10", "2026-10-01")).toThrow(BillingError);
    expect(() => soNgayO("2026-02-30", "2026-03-01")).toThrow(BillingError);
  });

  it("hóa đơn tháng", () => {
    const kq = tinhHoaDon({ ...co_ban, loai: "thang", tuNgay: "2026-10-01", denNgay: "2026-10-31",
      dienCu: 1000, dienMoi: 1120, nuocCu: 50, nuocMoi: 58, phiKhac: 100_000 });
    expect(kq.tienPhong).toBe(3_000_000);
    expect(kq.tienDien).toBe(420_000);
    expect(kq.tienNuoc).toBe(160_000);
    expect(kq.tong).toBe(3_680_000);
  });

  it("hóa đơn ngày", () => {
    const kq = tinhHoaDon({ ...co_ban, loai: "ngay", tuNgay: "2026-10-01", denNgay: "2026-10-05",
      dienCu: 10, dienMoi: 20, nuocCu: 1, nuocMoi: 2 });
    expect(kq.soNgay).toBe(5);
    expect(kq.tienPhong).toBe(750_000);
    expect(kq.tong).toBe(805_000);
  });

  it("chặn phí âm", () => {
    expect(() => tinhHoaDon({ ...co_ban, loai: "thang", tuNgay: "2026-10-01", denNgay: "2026-10-31",
      dienCu: 0, dienMoi: 0, nuocCu: 0, nuocMoi: 0, phiKhac: -1 })).toThrow(BillingError);
  });
});
