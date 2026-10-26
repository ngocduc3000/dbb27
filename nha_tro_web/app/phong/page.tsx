import Link from "next/link";
import { Flash } from "@/components/Flash";
import { danhSachPhong } from "@/lib/data";
import { vnd } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";

export default async function PhongList({ searchParams }: { searchParams: SearchParams }) {
  const phongs = await danhSachPhong(await createClient());
  return (
    <>
      <h1>Phòng</h1>
      <Flash params={await searchParams} />
      <div className="actions"><Link className="btn" href="/phong/them">+ Thêm phòng</Link></div>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Số phòng</th><th>Tầng</th><th className="num">Diện tích</th><th className="num">Giá tháng</th>
              <th className="num">Giá ngày</th><th>Người ở</th><th>Ghi chú</th><th></th></tr>
          </thead>
          <tbody>
            {phongs.map((p) => (
              <tr key={p.id}>
                <td><Link href={`/phong/${p.id}`}><b>{p.so_phong}</b></Link></td>
                <td>{p.tang}</td>
                <td className="num">{p.dien_tich} m²</td>
                <td className="num">{vnd(p.gia_thang)}</td>
                <td className="num">{vnd(p.gia_ngay)}</td>
                <td>{p.so_nguoi_o > 0
                  ? <span className="tag ok">{p.so_nguoi_o}/{p.so_nguoi_toi_da}</span>
                  : <span className="tag free">Trống</span>}</td>
                <td>{p.ghi_chu}</td>
                <td><Link href={`/phong/${p.id}/sua`}>Sửa</Link></td>
              </tr>
            ))}
            {phongs.length === 0 && <tr><td colSpan={8} className="muted">Chưa có phòng</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
