import { luuNguoiThue } from "@/app/actions";
import type { PhongCoNguoi } from "@/lib/data";
import type { NguoiThue } from "@/lib/types";

export function NguoiForm({ nguoi, phongs, phongId, homNay, back }:
  { nguoi?: NguoiThue; phongs: PhongCoNguoi[]; phongId?: number; homNay: string; back: string }) {
  return (
    <div className="card">
      <form action={luuNguoiThue} className="f">
        <input type="hidden" name="id" value={nguoi?.id ?? ""} />
        <input type="hidden" name="back" value={back} />
        <label>Phòng *
          <select name="phong_id" required defaultValue={nguoi?.phong_id ?? phongId ?? ""}>
            <option value="">-- Chọn phòng --</option>
            {phongs.map((p) => (
              <option key={p.id} value={p.id}>{p.so_phong} ({p.so_nguoi_o}/{p.so_nguoi_toi_da})</option>
            ))}
          </select>
        </label>
        <label>Họ tên *<input name="ho_ten" required defaultValue={nguoi?.ho_ten} /></label>
        <label>CCCD<input name="cccd" defaultValue={nguoi?.cccd} /></label>
        <label>Số điện thoại<input name="sdt" type="tel" defaultValue={nguoi?.sdt} /></label>
        <label>Ngày sinh<input name="ngay_sinh" type="date" defaultValue={nguoi?.ngay_sinh ?? ""} /></label>
        <label>Quê quán<input name="que_quan" defaultValue={nguoi?.que_quan} /></label>
        <label>Ngày vào *<input name="ngay_vao" type="date" required defaultValue={nguoi?.ngay_vao ?? homNay} /></label>
        <label>Ngày ra (trống = đang ở)<input name="ngay_ra" type="date" defaultValue={nguoi?.ngay_ra ?? ""} /></label>
        <label className="full">Ghi chú<input name="ghi_chu" defaultValue={nguoi?.ghi_chu} /></label>
        <div><button>Lưu</button></div>
      </form>
    </div>
  );
}
