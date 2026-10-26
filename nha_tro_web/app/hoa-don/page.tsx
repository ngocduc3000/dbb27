import Link from "next/link";
import { Flash } from "@/components/Flash";
import { HoaDonTable } from "@/components/HoaDonTable";
import { kiemTra } from "@/lib/data";
import { dauCuoiThang, sp, vnd } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { HoaDonCoPhong } from "@/lib/types";

export default async function HoaDonList({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const thang = /^\d{4}-\d{2}$/.test(sp(params, "thang")) ? sp(params, "thang") : "";
  const trangThai = sp(params, "trang_thai");
  const sb = await createClient();
  let q = sb.from("hoa_don").select("*, phong(so_phong)");
  if (thang) {
    const [dau, cuoi] = dauCuoiThang(`${thang}-01`);
    q = q.gte("den_ngay", dau).lte("den_ngay", cuoi);
  }
  if (trangThai === "0" || trangThai === "1") q = q.eq("da_thanh_toan", trangThai === "1");
  const rows = kiemTra(await q.order("den_ngay", { ascending: false })) as HoaDonCoPhong[];
  const tong = rows.reduce((s, r) => s + Number(r.tong), 0);

  return (
    <>
      <h1>Hóa đơn</h1>
      <Flash params={params} />
      <form className="actions" method="get">
        <label>Tháng (theo ngày kết thúc)<input type="month" name="thang" defaultValue={thang} /></label>
        <label>Trạng thái
          <select name="trang_thai" defaultValue={trangThai}>
            <option value="">Tất cả</option>
            <option value="0">Chưa thu</option>
            <option value="1">Đã thu</option>
          </select>
        </label>
        <button className="sec">Lọc</button>
        <Link className="btn" href="/hoa-don/tao">+ Tạo hóa đơn</Link>
      </form>
      <HoaDonTable rows={rows} hienPhong />
      <p><b>Tổng cộng: {vnd(tong)} đ</b> ({rows.length} hóa đơn)</p>
    </>
  );
}
