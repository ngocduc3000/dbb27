import Link from "next/link";
import { ghiChiSo } from "../actions";
import { Flash } from "@/components/Flash";
import { danhSachPhong, kiemTra } from "@/lib/data";
import { dinhDangNgay, homNay } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { ChiSo } from "@/lib/types";

export default async function ChiSoPage({ searchParams }: { searchParams: SearchParams }) {
  const sb = await createClient();
  const [phongs, res] = await Promise.all([
    danhSachPhong(sb),
    sb.from("chi_so").select("*, phong(so_phong)").order("ngay_ghi", { ascending: false }).limit(200),
  ]);
  const rows = kiemTra(res) as (ChiSo & { phong: { so_phong: string } | null })[];
  return (
    <>
      <h1>Chỉ số điện nước</h1>
      <Flash params={await searchParams} />
      <div className="card">
        <form action={ghiChiSo} className="f">
          <input type="hidden" name="back" value="/chi-so" />
          <label>Phòng
            <select name="phong_id" required defaultValue="">
              <option value="">-- Chọn phòng --</option>
              {phongs.map((p) => <option key={p.id} value={p.id}>{p.so_phong}</option>)}
            </select>
          </label>
          <label>Ngày ghi<input type="date" name="ngay_ghi" defaultValue={homNay()} required /></label>
          <label>Chỉ số điện (kWh)<input type="number" name="dien" min={0} required /></label>
          <label>Chỉ số nước (m³)<input type="number" name="nuoc" min={0} required /></label>
          <div className="end"><button>Ghi chỉ số</button></div>
        </form>
        <p className="muted">Ghi lại cùng phòng, cùng ngày sẽ ghi đè lần trước.</p>
      </div>
      <div className="scroll">
        <table>
          <thead><tr><th>Ngày ghi</th><th>Phòng</th><th className="num">Điện (kWh)</th><th className="num">Nước (m³)</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id}>
                <td>{dinhDangNgay(c.ngay_ghi)}</td>
                <td><Link href={`/phong/${c.phong_id}`}>{c.phong?.so_phong}</Link></td>
                <td className="num">{c.dien}</td><td className="num">{c.nuoc}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={4} className="muted">Chưa có dữ liệu</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
