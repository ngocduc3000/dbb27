// Tính tiền phòng / điện / nước. Hàm thuần, không đụng database.

export class BillingError extends Error {}

export type LoaiHoaDon = "thang" | "ngay";

export interface DauVaoHoaDon {
  loai: LoaiHoaDon;
  giaThang: number;
  giaNgay: number;
  tuNgay: string; // YYYY-MM-DD
  denNgay: string; // YYYY-MM-DD
  dienCu: number;
  dienMoi: number;
  nuocCu: number;
  nuocMoi: number;
  donGiaDien: number;
  donGiaNuoc: number;
  phiKhac?: number;
}

export interface KetQuaHoaDon {
  soNgay: number;
  tienPhong: number;
  soDien: number;
  tienDien: number;
  soNuoc: number;
  tienNuoc: number;
  phiKhac: number;
  tong: number;
}

/** Đổi 'YYYY-MM-DD' thành số ngày kể từ epoch (UTC, không lệch múi giờ). */
function ngayUTC(s: string): number {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) throw new BillingError(`Ngày không hợp lệ: ${s}`);
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const t = Date.UTC(y, mo - 1, d);
  const dt = new Date(t);
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) {
    throw new BillingError(`Ngày không hợp lệ: ${s}`);
  }
  return t / 86_400_000;
}

/** Số ngày tính tiền, tính cả ngày đầu và ngày cuối. */
export function soNgayO(tuNgay: string, denNgay: string): number {
  const n = ngayUTC(denNgay) - ngayUTC(tuNgay);
  if (n < 0) throw new BillingError("Ngày kết thúc nhỏ hơn ngày bắt đầu");
  return n + 1;
}

/** Số tiêu thụ = mới - cũ. */
export function tieuThu(cu: number, moi: number, ten: string): number {
  if (!Number.isInteger(cu) || !Number.isInteger(moi)) throw new BillingError(`Chỉ số ${ten} phải là số nguyên`);
  if (cu < 0 || moi < 0) throw new BillingError(`Chỉ số ${ten} không được âm`);
  if (moi < cu) throw new BillingError(`Chỉ số ${ten} mới (${moi}) nhỏ hơn chỉ số cũ (${cu})`);
  return moi - cu;
}

export function tinhHoaDon(v: DauVaoHoaDon): KetQuaHoaDon {
  if (v.loai !== "thang" && v.loai !== "ngay") throw new BillingError("Loại hóa đơn phải là 'thang' hoặc 'ngay'");
  const phiKhac = v.phiKhac ?? 0;
  for (const x of [v.giaThang, v.giaNgay, v.donGiaDien, v.donGiaNuoc, phiKhac]) {
    if (!Number.isInteger(x) || x < 0) throw new BillingError("Giá / phí phải là số nguyên không âm");
  }
  const soNgay = soNgayO(v.tuNgay, v.denNgay);
  const tienPhong = v.loai === "thang" ? v.giaThang : v.giaNgay * soNgay;
  const soDien = tieuThu(v.dienCu, v.dienMoi, "điện");
  const soNuoc = tieuThu(v.nuocCu, v.nuocMoi, "nước");
  const tienDien = soDien * v.donGiaDien;
  const tienNuoc = soNuoc * v.donGiaNuoc;
  return {
    soNgay,
    tienPhong,
    soDien,
    tienDien,
    soNuoc,
    tienNuoc,
    phiKhac,
    tong: tienPhong + tienDien + tienNuoc + phiKhac,
  };
}
