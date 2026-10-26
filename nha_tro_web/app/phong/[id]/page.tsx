import Link from "next/link";
import { notFound } from "next/navigation";
import { ghiChiSo, traPhong } from "@/app/actions";
import { Flash } from "@/components/Flash";
import { HoaDonTable } from "@/components/HoaDonTable";
import { kiemTra } from "@/lib/data";
import { dinhDangNgay, homNay, vnd } from "@/lib/format";
import type { IdParams, SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { ChiSo, HoaDonCoPhong, NguoiThue, Phong } from "@/lib/types";

export default async function ChiTietPhong({ params, searchParams }: { params: IdParams; searchParams: SearchParams }) {
  const { id } = await params;
  const sb = await createClient();
  const { data } = await sb.from("phong").select("*").eq("id", id).maybeSingle();
  if (!data) notFound();
  const phong = data as Phong;
  const [nguoiRes, chiSoRes, hdRes] = await Promise.all([
    sb.from("nguoi_thue").select("*").eq("phong_id", id).order("ngay_ra", { ascending: false, nullsFirst: true })
      .order("ngay_vao", { ascending: false }),
    sb.from("chi_so").select("*").eq("phong_id", id).order("ngay_ghi", { ascending: false }).limit(24),
    sb.from("hoa_don").select("*, phong(so_phong)").eq("phong_id", id).order("tu_ngay", { ascending: false }),
  ]);
  const nguoi = kiemTra(nguoiRes) as NguoiThue[];
  const chiSo = kiemTra(chiSoRes) as ChiSo[];
  const hoaDon = kiemTra(hdRes) as HoaDonCoPhong[];
  const today = homNay();
  const back = `/phong/${id}`;

  return (
    <>
      <h1>Phòng {phong.so_phong}{" "}
        <span className="muted" style={{ fontSize: 15 }}>
          · Tầng {phong.tang} · {phong.dien_tich} m² · {vnd(phong.gia_thang)} đ/tháng · {vnd(phong.gia_ngay)} đ/ngày
        </span>
      </h1>
      <Flash params={await searchParams} />
      <div className="actions">
        <Link className="btn sec" href={`/phong/${id}/sua`}>Sửa phòng</Link>
        <Link className="btn sec" href={`/nguoi-thue/them?phong_id=${id}`}>+ Thêm người ở</Link>
        <Link className="btn" href={`/hoa-don/tao?phong_id=${id}`}>Tạo hóa đơn</Link>
      </div>

      <h2>Người ở trọ</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr><th>Họ tên</th><th>CCCD</th><th>SĐT</th><th>Ngày sinh</th><th>Quê quán</th><th>Ngày vào</th><th>Ngày ra</th><th></th></tr>
          </thead>
          <tbody>
            {nguoi.map((n) => (
              <tr key={n.id}>
                <td>{n.ho_ten}</td><td>{n.cccd}</td><td>{n.sdt}</td><td>{dinhDangNgay(n.ngay_sinh)}</td><td>{n.que_quan}</td>
                <td>{dinhDangNgay(n.ngay_vao)}</td>
                <td>{n.ngay_ra ? dinhDangNgay(n.ngay_ra) : <span className="tag ok">Đang ở</span>}</td>
                <td>
                  <Link href={`/nguoi-thue/${n.id}/sua`}>Sửa</Link>{" "}
                  {!n.ngay_ra && (
                    <form action={traPhong} className="inline">
                      <input type="hidden" name="id" value={n.id} />
                      <input type="hidden" name="back" value={back} />
                      <input type="date" name="ngay_ra" defaultValue={today} required />
                      <button className="sec">Trả phòng</button>
                    </form>
                  )}
                </td>
              </tr>
            ))}
            {nguoi.length === 0 && <tr><td colSpan={8} className="muted">Chưa có người ở</td></tr>}
          </tbody>
        </table>
      </div>

      <h2>Ghi chỉ số điện nước</h2>
      <div className="card">
        <form action={ghiChiSo} className="f">
          <input type="hidden" name="phong_id" value={phong.id} />
          <input type="hidden" name="back" value={back} />
          <label>Ngày ghi<input type="date" name="ngay_ghi" defaultValue={today} required /></label>
          <label>Chỉ số điện (kWh)<input type="number" name="dien" min={0} required /></label>
          <label>Chỉ số nước (m³)<input type="number" name="nuoc" min={0} required /></label>
          <div className="end"><button>Ghi</button></div>
        </form>
      </div>
      <div className="scroll">
        <table>
          <thead><tr><th>Ngày ghi</th><th className="num">Điện</th><th className="num">Nước</th></tr></thead>
          <tbody>
            {chiSo.map((c) => (
              <tr key={c.id}><td>{dinhDangNgay(c.ngay_ghi)}</td><td className="num">{c.dien}</td><td className="num">{c.nuoc}</td></tr>
            ))}
            {chiSo.length === 0 && <tr><td colSpan={3} className="muted">Chưa có chỉ số</td></tr>}
          </tbody>
        </table>
      </div>

      <h2>Hóa đơn</h2>
      <HoaDonTable rows={hoaDon} />
    </>
  );
}
