import Link from "next/link";
import { luuPhong } from "@/app/actions";
import type { Phong } from "@/lib/types";

export function PhongForm({ phong, back }: { phong?: Phong; back: string }) {
  return (
    <div className="card">
      <form action={luuPhong} className="f">
        <input type="hidden" name="id" value={phong?.id ?? ""} />
        <input type="hidden" name="back" value={back} />
        <label>Số phòng *<input name="so_phong" required defaultValue={phong?.so_phong} /></label>
        <label>Tầng<input name="tang" type="number" min={0} defaultValue={phong?.tang ?? 1} /></label>
        <label>Diện tích (m²)<input name="dien_tich" type="number" step="0.1" min={0} defaultValue={phong?.dien_tich ?? ""} /></label>
        <label>Giá thuê tháng (đ)<input name="gia_thang" type="number" min={0} defaultValue={phong?.gia_thang ?? ""} /></label>
        <label>Giá thuê ngày (đ)<input name="gia_ngay" type="number" min={0} defaultValue={phong?.gia_ngay ?? ""} /></label>
        <label>Số người tối đa<input name="so_nguoi_toi_da" type="number" min={1} defaultValue={phong?.so_nguoi_toi_da ?? 2} /></label>
        <label className="full">Ghi chú<input name="ghi_chu" defaultValue={phong?.ghi_chu} /></label>
        <div><button>Lưu</button> <Link className="btn sec" href="/phong">Hủy</Link></div>
      </form>
    </div>
  );
}
