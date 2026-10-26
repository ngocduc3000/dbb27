import Link from "next/link";
import { dinhDangNgay, vnd } from "@/lib/format";
import type { HoaDonCoPhong } from "@/lib/types";

export function HoaDonTable({ rows, hienPhong }: { rows: HoaDonCoPhong[]; hienPhong?: boolean }) {
  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            {hienPhong && <th>Phòng</th>}
            <th>Loại</th><th>Kỳ</th><th className="num">Tiền phòng</th><th className="num">Điện</th>
            <th className="num">Nước</th><th className="num">Phí khác</th><th className="num">Tổng</th><th>Trạng thái</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((h) => (
            <tr key={h.id}>
              {hienPhong && <td>{h.phong?.so_phong}</td>}
              <td>{h.loai === "thang" ? "Tháng" : `Ngày (${h.so_ngay})`}</td>
              <td><Link href={`/hoa-don/${h.id}`}>{dinhDangNgay(h.tu_ngay)} → {dinhDangNgay(h.den_ngay)}</Link></td>
              <td className="num">{vnd(h.tien_phong)}</td>
              <td className="num">{vnd(h.tien_dien)}</td>
              <td className="num">{vnd(h.tien_nuoc)}</td>
              <td className="num">{vnd(h.phi_khac)}</td>
              <td className="num"><b>{vnd(h.tong)}</b></td>
              <td>{h.da_thanh_toan
                ? <span className="tag ok">Đã thu {dinhDangNgay(h.ngay_thanh_toan)}</span>
                : <span className="tag no">Chưa thu</span>}</td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={9} className="muted">Chưa có hóa đơn</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
