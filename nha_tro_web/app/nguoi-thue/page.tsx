import Link from "next/link";
import { Flash } from "@/components/Flash";
import { kiemTra } from "@/lib/data";
import { dinhDangNgay, sp } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { NguoiThue } from "@/lib/types";

export default async function NguoiList({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const tatCa = sp(params, "tat_ca") === "1";
  const sb = await createClient();
  let q = sb.from("nguoi_thue").select("*, phong(so_phong)");
  if (!tatCa) q = q.is("ngay_ra", null);
  const nguoi = (kiemTra(await q) as (NguoiThue & { phong: { so_phong: string } | null })[])
    .sort((a, b) => (a.phong?.so_phong ?? "").localeCompare(b.phong?.so_phong ?? "", "vi", { numeric: true })
      || a.ho_ten.localeCompare(b.ho_ten, "vi"));

  return (
    <>
      <h1>Người thuê</h1>
      <Flash params={params} />
      <div className="actions">
        <Link className="btn" href="/nguoi-thue/them">+ Thêm người thuê</Link>
        {tatCa
          ? <Link className="btn sec" href="/nguoi-thue">Chỉ người đang ở</Link>
          : <Link className="btn sec" href="/nguoi-thue?tat_ca=1">Xem cả người đã trả phòng</Link>}
      </div>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Phòng</th><th>Họ tên</th><th>CCCD</th><th>SĐT</th><th>Ngày sinh</th><th>Quê quán</th><th>Ngày vào</th><th>Ngày ra</th><th></th></tr>
          </thead>
          <tbody>
            {nguoi.map((n) => (
              <tr key={n.id}>
                <td><Link href={`/phong/${n.phong_id}`}>{n.phong?.so_phong}</Link></td>
                <td>{n.ho_ten}</td><td>{n.cccd}</td><td>{n.sdt}</td><td>{dinhDangNgay(n.ngay_sinh)}</td><td>{n.que_quan}</td>
                <td>{dinhDangNgay(n.ngay_vao)}</td><td>{dinhDangNgay(n.ngay_ra)}</td>
                <td><Link href={`/nguoi-thue/${n.id}/sua`}>Sửa</Link></td>
              </tr>
            ))}
            {nguoi.length === 0 && <tr><td colSpan={9} className="muted">Chưa có người thuê</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
