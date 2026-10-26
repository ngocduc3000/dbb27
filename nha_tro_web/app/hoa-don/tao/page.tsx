import { taoHoaDon } from "@/app/actions";
import { Flash } from "@/components/Flash";
import { chiSoTruoc, danhSachPhong, donGia } from "@/lib/data";
import { dauCuoiThang, homNay, sp, vnd } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";

const laNgay = (s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s);

export default async function TaoHoaDon({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const sb = await createClient();
  const [macDinhTu, macDinhDen] = dauCuoiThang(homNay());
  const phongId = Number(sp(params, "phong_id")) || undefined;
  const loai = sp(params, "loai") === "ngay" ? "ngay" : "thang";
  const tu = laNgay(sp(params, "tu_ngay")) ? sp(params, "tu_ngay") : macDinhTu;
  const den = laNgay(sp(params, "den_ngay")) ? sp(params, "den_ngay") : macDinhDen;

  const [phongs, gia, cu, moi] = await Promise.all([
    danhSachPhong(sb),
    donGia(sb),
    phongId ? chiSoTruoc(sb, phongId, tu) : null,
    phongId ? chiSoTruoc(sb, phongId, den) : null,
  ]);
  const back = `/hoa-don/tao?phong_id=${phongId ?? ""}&loai=${loai}&tu_ngay=${tu}&den_ngay=${den}`;

  return (
    <>
      <h1>Tạo hóa đơn</h1>
      <Flash params={params} />
      <div className="card">
        <p className="muted">Bước 1: chọn phòng, loại và kỳ → bấm “Lấy chỉ số” để điền sẵn chỉ số cũ/mới từ dữ liệu đã ghi.
          Đơn giá hiện tại: điện {vnd(gia.don_gia_dien)} đ/kWh, nước {vnd(gia.don_gia_nuoc)} đ/m³.</p>
        <form method="get" className="f">
          <label>Phòng
            <select name="phong_id" required defaultValue={phongId ?? ""}>
              <option value="">-- Chọn phòng --</option>
              {phongs.map((p) => (
                <option key={p.id} value={p.id}>{p.so_phong} — {vnd(p.gia_thang)}/tháng, {vnd(p.gia_ngay)}/ngày</option>
              ))}
            </select>
          </label>
          <label>Loại
            <select name="loai" defaultValue={loai}>
              <option value="thang">Theo tháng</option>
              <option value="ngay">Theo ngày</option>
            </select>
          </label>
          <label>Từ ngày<input type="date" name="tu_ngay" defaultValue={tu} required /></label>
          <label>Đến ngày<input type="date" name="den_ngay" defaultValue={den} required /></label>
          <div className="end"><button className="sec">Lấy chỉ số</button></div>
        </form>
      </div>

      {phongId && (
        <div className="card" key={back}>
          <p className="muted">Bước 2: kiểm tra chỉ số, nhập phí khác (nếu có) → Tạo hóa đơn.</p>
          <form action={taoHoaDon} className="f">
            <input type="hidden" name="back" value={back} />
            <input type="hidden" name="phong_id" value={phongId} />
            <input type="hidden" name="loai" value={loai} />
            <input type="hidden" name="tu_ngay" value={tu} />
            <input type="hidden" name="den_ngay" value={den} />
            <label>Điện cũ<input type="number" name="dien_cu" min={0} required defaultValue={cu?.dien ?? ""} /></label>
            <label>Điện mới<input type="number" name="dien_moi" min={0} required defaultValue={moi?.dien ?? ""} /></label>
            <label>Nước cũ<input type="number" name="nuoc_cu" min={0} required defaultValue={cu?.nuoc ?? ""} /></label>
            <label>Nước mới<input type="number" name="nuoc_moi" min={0} required defaultValue={moi?.nuoc ?? ""} /></label>
            <label>Phí khác (rác, wifi, gửi xe...)<input type="number" name="phi_khac" min={0} defaultValue={0} /></label>
            <label>Ghi chú<input name="ghi_chu" /></label>
            <div className="end"><button>Tạo hóa đơn</button></div>
          </form>
        </div>
      )}
    </>
  );
}
