"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { BillingError, tinhHoaDon, type LoaiHoaDon } from "@/lib/billing";
import { chiSoTruoc, donGia } from "@/lib/data";
import { createClient } from "@/lib/supabase/server";
import type { ChiSo } from "@/lib/types";

// ---------- Đọc dữ liệu form ----------
class LoiNhap extends Error {}

function chuoi(fd: FormData, k: string): string {
  return String(fd.get(k) ?? "").trim();
}

function soNguyen(fd: FormData, k: string, macDinh?: number): number {
  const v = chuoi(fd, k).replace(/[.,\s]/g, "");
  if (v === "") {
    if (macDinh !== undefined) return macDinh;
    throw new LoiNhap(`Chưa nhập ${k}`);
  }
  if (!/^-?\d+$/.test(v)) throw new LoiNhap(`'${k}' không phải số nguyên: ${v}`);
  return Number(v);
}

function ngay(fd: FormData, k: string, batBuoc = true): string | null {
  const v = chuoi(fd, k);
  if (v === "" && !batBuoc) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new LoiNhap(`Ngày '${k}' không hợp lệ`);
  return v;
}

/** Đường dẫn quay lại: chỉ chấp nhận đường dẫn nội bộ. */
function duongDan(fd: FormData, macDinh: string): string {
  const v = chuoi(fd, "back");
  return v.startsWith("/") && !v.startsWith("//") ? v : macDinh;
}

function kemThongBao(path: string, loai: "loi" | "ok", msg: string): string {
  const u = new URL(path, "http://x");
  u.searchParams.delete("loi");
  u.searchParams.delete("ok");
  u.searchParams.set(loai, msg);
  return u.pathname + u.search;
}

function thongDiepLoi(e: unknown): string {
  if (e instanceof LoiNhap || e instanceof BillingError) return e.message;
  const m = e instanceof Error ? e.message : String(e);
  if (/duplicate key/.test(m) && /so_phong/.test(m)) return "Số phòng đã tồn tại";
  if (/duplicate key/.test(m)) return "Dữ liệu bị trùng";
  if (/violates foreign key/.test(m)) return "Không xóa được vì còn dữ liệu liên quan";
  if (/row-level security/.test(m)) return "Không có quyền thao tác dữ liệu này";
  return m;
}

/** Chạy thao tác ghi; lỗi thì quay lại trang trước kèm thông báo. */
async function chay(fd: FormData, macDinh: string, fn: () => Promise<{ toi: string; ok?: string }>) {
  let dich: string;
  try {
    const kq = await fn();
    revalidatePath("/", "layout");
    dich = kq.ok ? kemThongBao(kq.toi, "ok", kq.ok) : kq.toi;
  } catch (e) {
    dich = kemThongBao(duongDan(fd, macDinh), "loi", thongDiepLoi(e));
  }
  redirect(dich);
}

type KetQua = { data: unknown; error: { message: string } | null };

/** Ném lỗi nếu Supabase trả lỗi. */
function ok(res: KetQua): void {
  if (res.error) throw new Error(res.error.message);
}

/** Một dòng có thể không có. */
function coThe<T>(res: KetQua): T | null {
  ok(res);
  return (res.data as T) ?? null;
}

/** Một dòng bắt buộc phải có. */
function mot<T>(res: KetQua): T {
  const r = coThe<T>(res);
  if (!r) throw new LoiNhap("Không tìm thấy dữ liệu");
  return r;
}

// ---------- Đăng nhập ----------
export async function dangNhap(fd: FormData) {
  const sb = await createClient();
  const { error } = await sb.auth.signInWithPassword({ email: chuoi(fd, "email"), password: chuoi(fd, "password") });
  if (error) redirect(kemThongBao("/login", "loi", "Sai email hoặc mật khẩu"));
  redirect("/");
}

export async function dangXuat() {
  const sb = await createClient();
  await sb.auth.signOut();
  redirect("/login");
}

// ---------- Phòng ----------
export async function luuPhong(fd: FormData) {
  await chay(fd, "/phong", async () => {
    const sb = await createClient();
    const id = soNguyen(fd, "id", 0);
    const v = {
      so_phong: chuoi(fd, "so_phong"),
      tang: soNguyen(fd, "tang", 1),
      dien_tich: Number(chuoi(fd, "dien_tich") || 0),
      gia_thang: soNguyen(fd, "gia_thang", 0),
      gia_ngay: soNguyen(fd, "gia_ngay", 0),
      so_nguoi_toi_da: soNguyen(fd, "so_nguoi_toi_da", 2),
      ghi_chu: chuoi(fd, "ghi_chu"),
    };
    if (!v.so_phong) throw new LoiNhap("Chưa nhập số phòng");
    if (!Number.isFinite(v.dien_tich) || v.dien_tich < 0) throw new LoiNhap("Diện tích không hợp lệ");
    if (id) ok(await sb.from("phong").update(v).eq("id", id));
    else ok(await sb.from("phong").insert(v));
    return { toi: "/phong", ok: "Đã lưu phòng" };
  });
}

// ---------- Người thuê ----------
export async function luuNguoiThue(fd: FormData) {
  await chay(fd, "/nguoi-thue", async () => {
    const sb = await createClient();
    const id = soNguyen(fd, "id", 0);
    const v = {
      phong_id: soNguyen(fd, "phong_id"),
      ho_ten: chuoi(fd, "ho_ten"),
      cccd: chuoi(fd, "cccd"),
      sdt: chuoi(fd, "sdt"),
      ngay_sinh: ngay(fd, "ngay_sinh", false),
      que_quan: chuoi(fd, "que_quan"),
      ngay_vao: ngay(fd, "ngay_vao") as string,
      ngay_ra: ngay(fd, "ngay_ra", false),
      ghi_chu: chuoi(fd, "ghi_chu"),
    };
    if (!v.ho_ten) throw new LoiNhap("Chưa nhập họ tên");
    if (v.ngay_ra && v.ngay_ra < v.ngay_vao) throw new LoiNhap("Ngày ra nhỏ hơn ngày vào");
    if (id) ok(await sb.from("nguoi_thue").update(v).eq("id", id));
    else ok(await sb.from("nguoi_thue").insert(v));
    return { toi: `/phong/${v.phong_id}`, ok: "Đã lưu người thuê" };
  });
}

export async function traPhong(fd: FormData) {
  await chay(fd, "/nguoi-thue", async () => {
    const sb = await createClient();
    const id = soNguyen(fd, "id");
    const ngayRa = ngay(fd, "ngay_ra") as string;
    const n = mot<{ ho_ten: string; phong_id: number; ngay_vao: string }>(await sb.from("nguoi_thue").select("ho_ten, phong_id, ngay_vao").eq("id", id).single());
    if (ngayRa < n.ngay_vao) throw new LoiNhap("Ngày ra nhỏ hơn ngày vào");
    ok(await sb.from("nguoi_thue").update({ ngay_ra: ngayRa }).eq("id", id));
    return { toi: `/phong/${n.phong_id}`, ok: `${n.ho_ten} đã trả phòng` };
  });
}

// ---------- Chỉ số điện nước ----------
export async function ghiChiSo(fd: FormData) {
  await chay(fd, "/chi-so", async () => {
    const sb = await createClient();
    const phongId = soNguyen(fd, "phong_id");
    const ngayGhi = ngay(fd, "ngay_ghi") as string;
    const dien = soNguyen(fd, "dien");
    const nuoc = soNguyen(fd, "nuoc");
    if (dien < 0 || nuoc < 0) throw new LoiNhap("Chỉ số không được âm");

    // Không cho nhỏ hơn lần ghi trước, không lớn hơn lần ghi sau
    const truoc = coThe<ChiSo>(await sb.from("chi_so").select("*").eq("phong_id", phongId).lt("ngay_ghi", ngayGhi)
      .order("ngay_ghi", { ascending: false }).limit(1).maybeSingle());
    if (truoc && (dien < truoc.dien || nuoc < truoc.nuoc)) {
      throw new LoiNhap(`Chỉ số nhỏ hơn lần ghi trước (${truoc.ngay_ghi}: điện ${truoc.dien}, nước ${truoc.nuoc})`);
    }
    const sau = coThe<ChiSo>(await sb.from("chi_so").select("*").eq("phong_id", phongId).gt("ngay_ghi", ngayGhi)
      .order("ngay_ghi", { ascending: true }).limit(1).maybeSingle());
    if (sau && (dien > sau.dien || nuoc > sau.nuoc)) {
      throw new LoiNhap(`Chỉ số lớn hơn lần ghi sau (${sau.ngay_ghi}: điện ${sau.dien}, nước ${sau.nuoc})`);
    }
    ok(await sb.from("chi_so").upsert({ phong_id: phongId, ngay_ghi: ngayGhi, dien, nuoc },
      { onConflict: "phong_id,ngay_ghi" }));
    return { toi: duongDan(fd, "/chi-so"), ok: "Đã ghi chỉ số" };
  });
}

// ---------- Hóa đơn ----------
export async function taoHoaDon(fd: FormData) {
  await chay(fd, "/hoa-don/tao", async () => {
    const sb = await createClient();
    const phongId = soNguyen(fd, "phong_id");
    const loai = chuoi(fd, "loai") as LoaiHoaDon;
    const tuNgay = ngay(fd, "tu_ngay") as string;
    const denNgay = ngay(fd, "den_ngay") as string;
    const phong = mot<{ gia_thang: number; gia_ngay: number }>(await sb.from("phong").select("gia_thang, gia_ngay").eq("id", phongId).single());
    const gia = await donGia(sb);
    const d = {
      dien_cu: soNguyen(fd, "dien_cu"), dien_moi: soNguyen(fd, "dien_moi"),
      nuoc_cu: soNguyen(fd, "nuoc_cu"), nuoc_moi: soNguyen(fd, "nuoc_moi"),
    };
    const kq = tinhHoaDon({
      loai, giaThang: phong.gia_thang, giaNgay: phong.gia_ngay, tuNgay, denNgay,
      dienCu: d.dien_cu, dienMoi: d.dien_moi, nuocCu: d.nuoc_cu, nuocMoi: d.nuoc_moi,
      donGiaDien: gia.don_gia_dien, donGiaNuoc: gia.don_gia_nuoc, phiKhac: soNguyen(fd, "phi_khac", 0),
    });
    const hd = mot<{ id: number }>(await sb.from("hoa_don").insert({
      phong_id: phongId, loai, tu_ngay: tuNgay, den_ngay: denNgay, so_ngay: kq.soNgay, ...d,
      don_gia_dien: gia.don_gia_dien, don_gia_nuoc: gia.don_gia_nuoc,
      tien_phong: kq.tienPhong, tien_dien: kq.tienDien, tien_nuoc: kq.tienNuoc,
      phi_khac: kq.phiKhac, tong: kq.tong, ghi_chu: chuoi(fd, "ghi_chu"),
    }).select("id").single());
    return { toi: `/hoa-don/${hd.id}`, ok: "Đã tạo hóa đơn" };
  });
}

export async function thanhToan(fd: FormData) {
  await chay(fd, "/hoa-don", async () => {
    const sb = await createClient();
    const id = soNguyen(fd, "id");
    const huy = chuoi(fd, "huy") === "1";
    ok(await sb.from("hoa_don").update(huy
      ? { da_thanh_toan: false, ngay_thanh_toan: null }
      : { da_thanh_toan: true, ngay_thanh_toan: ngay(fd, "ngay_thanh_toan") }).eq("id", id));
    return { toi: `/hoa-don/${id}`, ok: huy ? "Đã hủy thanh toán" : "Đã ghi nhận thanh toán" };
  });
}

export async function xoaHoaDon(fd: FormData) {
  await chay(fd, "/hoa-don", async () => {
    const sb = await createClient();
    ok(await sb.from("hoa_don").delete().eq("id", soNguyen(fd, "id")));
    return { toi: "/hoa-don", ok: "Đã xóa hóa đơn" };
  });
}

// ---------- Đơn giá ----------
export async function luuDonGia(fd: FormData) {
  await chay(fd, "/cau-hinh", async () => {
    const sb = await createClient();
    const v = { don_gia_dien: soNguyen(fd, "don_gia_dien"), don_gia_nuoc: soNguyen(fd, "don_gia_nuoc") };
    if (v.don_gia_dien < 0 || v.don_gia_nuoc < 0) throw new LoiNhap("Đơn giá không được âm");
    const { data } = await sb.auth.getClaims();
    const uid = data?.claims?.sub;
    if (!uid) throw new LoiNhap("Chưa đăng nhập");
    ok(await sb.from("cau_hinh").upsert({ owner_id: uid, ...v }, { onConflict: "owner_id" }));
    return { toi: "/cau-hinh", ok: "Đã lưu đơn giá" };
  });
}
