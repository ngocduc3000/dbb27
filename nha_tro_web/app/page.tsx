import Link from "next/link";
import { Flash } from "@/components/Flash";
import { danhSachPhong, kiemTra } from "@/lib/data";
import { dauCuoiThang, homNay, vnd } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";

export default async function TongQuan({ searchParams }: { searchParams: SearchParams }) {
  const sb = await createClient();
  const thang = homNay().slice(0, 7);
  const [dauThang, cuoiThang] = dauCuoiThang(homNay());
  const [phongs, chuaThu, daThu] = await Promise.all([
    danhSachPhong(sb),
    sb.from("hoa_don").select("tong").eq("da_thanh_toan", false),
    sb.from("hoa_don").select("tong").eq("da_thanh_toan", true)
      .gte("ngay_thanh_toan", dauThang).lte("ngay_thanh_toan", cuoiThang),
  ]);
  const no = kiemTra(chuaThu) as { tong: number }[];
  const thu = kiemTra(daThu) as { tong: number }[];
  const dangO = phongs.filter((p) => p.so_nguoi_o > 0).length;
  const tong = (rs: { tong: number }[]) => rs.reduce((s, r) => s + Number(r.tong), 0);

  return (
    <>
      <h1>Tổng quan</h1>
      <Flash params={await searchParams} />
      <div className="grid">
        <div className="card stat"><span className="muted">Tổng số phòng</span><b>{phongs.length}</b></div>
        <div className="card stat"><span className="muted">Phòng có người</span><b>{dangO}</b></div>
        <div className="card stat"><span className="muted">Phòng trống</span><b>{phongs.length - dangO}</b></div>
        <div className="card stat"><span className="muted">Hóa đơn chưa thu</span><b>{no.length} · {vnd(tong(no))} đ</b></div>
        <div className="card stat"><span className="muted">Đã thu tháng {thang.slice(5)}/{thang.slice(0, 4)}</span><b>{vnd(tong(thu))} đ</b></div>
      </div>
      <h2>Sơ đồ phòng</h2>
      <div className="grid">
        {phongs.map((p) => (
          <Link key={p.id} className="card roomcard" href={`/phong/${p.id}`}>
            <b>Phòng {p.so_phong}</b> <span className="muted">· Tầng {p.tang}</span><br />
            {p.so_nguoi_o > 0
              ? <span className="tag ok">{p.so_nguoi_o}/{p.so_nguoi_toi_da} người</span>
              : <span className="tag free">Trống</span>}
            <div className="muted" style={{ marginTop: 6 }}>{vnd(p.gia_thang)} đ/tháng · {vnd(p.gia_ngay)} đ/ngày</div>
          </Link>
        ))}
        {phongs.length === 0 && <p className="muted">Chưa có phòng. <Link href="/phong/them">Thêm phòng</Link></p>}
      </div>
    </>
  );
}
