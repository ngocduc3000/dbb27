import Link from "next/link";
import { notFound } from "next/navigation";
import { thanhToan, xoaHoaDon } from "@/app/actions";
import { ConfirmButton, PrintButton } from "@/components/ConfirmButton";
import { Flash } from "@/components/Flash";
import { dinhDangNgay, homNay, vnd } from "@/lib/format";
import type { IdParams, SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { HoaDonCoPhong } from "@/lib/types";

export default async function XemHoaDon({ params, searchParams }: { params: IdParams; searchParams: SearchParams }) {
  const { id } = await params;
  const sb = await createClient();
  const { data } = await sb.from("hoa_don").select("*, phong(so_phong)").eq("id", id).maybeSingle();
  if (!data) notFound();
  const h = data as HoaDonCoPhong;
  const back = `/hoa-don/${id}`;

  return (
    <>
      <Flash params={await searchParams} />
      <div className="card" style={{ maxWidth: 640 }}>
        <h1 style={{ textAlign: "center" }}>HÓA ĐƠN TIỀN PHÒNG</h1>
        <p style={{ textAlign: "center" }}>
          Phòng <b>{h.phong?.so_phong}</b> · {h.loai === "thang" ? "Theo tháng" : "Theo ngày"} ·
          Từ {dinhDangNgay(h.tu_ngay)} đến {dinhDangNgay(h.den_ngay)}
        </p>
        <table>
          <thead><tr><th>Khoản</th><th>Chi tiết</th><th className="num">Thành tiền (đ)</th></tr></thead>
          <tbody>
            <tr><td>Tiền phòng</td><td>{h.loai === "thang" ? "1 tháng" : `${h.so_ngay} ngày`}</td><td className="num">{vnd(h.tien_phong)}</td></tr>
            <tr><td>Tiền điện</td><td>{h.dien_cu} → {h.dien_moi} = {h.dien_moi - h.dien_cu} kWh × {vnd(h.don_gia_dien)}</td><td className="num">{vnd(h.tien_dien)}</td></tr>
            <tr><td>Tiền nước</td><td>{h.nuoc_cu} → {h.nuoc_moi} = {h.nuoc_moi - h.nuoc_cu} m³ × {vnd(h.don_gia_nuoc)}</td><td className="num">{vnd(h.tien_nuoc)}</td></tr>
            <tr><td>Phí khác</td><td>{h.ghi_chu}</td><td className="num">{vnd(h.phi_khac)}</td></tr>
            <tr><th colSpan={2}>TỔNG CỘNG</th><th className="num">{vnd(h.tong)}</th></tr>
          </tbody>
        </table>
        <p>Trạng thái:{" "}
          {h.da_thanh_toan
            ? <span className="tag ok">Đã thanh toán ngày {dinhDangNgay(h.ngay_thanh_toan)}</span>
            : <span className="tag no">Chưa thanh toán</span>}
        </p>
      </div>
      <div className="actions noprint">
        <form action={thanhToan} className="inline">
          <input type="hidden" name="id" value={h.id} />
          <input type="hidden" name="back" value={back} />
          {h.da_thanh_toan ? (
            <><input type="hidden" name="huy" value="1" /><button className="sec">Hủy thanh toán</button></>
          ) : (
            <><input type="date" name="ngay_thanh_toan" defaultValue={homNay()} required /><button>Xác nhận đã thu</button></>
          )}
        </form>
        <PrintButton />
        <Link className="btn sec" href={`/phong/${h.phong_id}`}>Về phòng</Link>
        <form action={xoaHoaDon} className="inline">
          <input type="hidden" name="id" value={h.id} />
          <input type="hidden" name="back" value={back} />
          <ConfirmButton className="del" message="Xóa hóa đơn này?">Xóa</ConfirmButton>
        </form>
      </div>
    </>
  );
}
