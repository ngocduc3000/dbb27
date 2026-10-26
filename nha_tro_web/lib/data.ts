import type { SupabaseClient } from "@supabase/supabase-js";
import type { ChiSo, Phong } from "./types";

export type PhongCoNguoi = Phong & { so_nguoi_o: number };

function kiemTra<T>(res: { data: T | null; error: { message: string } | null }): T {
  if (res.error) throw new Error(res.error.message);
  return res.data as T;
}

/** Danh sách phòng kèm số người đang ở. */
export async function danhSachPhong(sb: SupabaseClient): Promise<PhongCoNguoi[]> {
  const [phong, dangO] = await Promise.all([
    sb.from("phong").select("*").order("so_phong"),
    sb.from("nguoi_thue").select("phong_id").is("ngay_ra", null),
  ]);
  const dem = new Map<number, number>();
  for (const r of kiemTra(dangO) as { phong_id: number }[]) dem.set(r.phong_id, (dem.get(r.phong_id) ?? 0) + 1);
  return (kiemTra(phong) as Phong[]).map((p) => ({ ...p, so_nguoi_o: dem.get(p.id) ?? 0 }));
}

export async function donGia(sb: SupabaseClient): Promise<{ don_gia_dien: number; don_gia_nuoc: number }> {
  const res = await sb.from("cau_hinh").select("don_gia_dien, don_gia_nuoc").maybeSingle();
  if (res.error) throw new Error(res.error.message);
  // Chưa lưu lần nào → dùng mặc định giống schema.sql
  return res.data ?? { don_gia_dien: 3500, don_gia_nuoc: 20000 };
}

/** Chỉ số gần nhất có ngày ghi <= ngay. */
export async function chiSoTruoc(sb: SupabaseClient, phongId: number, ngay: string): Promise<ChiSo | null> {
  const res = await sb.from("chi_so").select("*").eq("phong_id", phongId).lte("ngay_ghi", ngay)
    .order("ngay_ghi", { ascending: false }).limit(1).maybeSingle();
  if (res.error) throw new Error(res.error.message);
  return res.data as ChiSo | null;
}

export { kiemTra };
