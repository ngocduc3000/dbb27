import { luuDonGia } from "../actions";
import { Flash } from "@/components/Flash";
import { donGia } from "@/lib/data";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";

export default async function CauHinh({ searchParams }: { searchParams: SearchParams }) {
  const gia = await donGia(await createClient());
  return (
    <>
      <h1>Đơn giá điện nước</h1>
      <Flash params={await searchParams} />
      <div className="card" style={{ maxWidth: 520 }}>
        <form action={luuDonGia} className="f">
          <input type="hidden" name="back" value="/cau-hinh" />
          <label>Đơn giá điện (đ/kWh)<input type="number" name="don_gia_dien" min={0} defaultValue={gia.don_gia_dien} required /></label>
          <label>Đơn giá nước (đ/m³)<input type="number" name="don_gia_nuoc" min={0} defaultValue={gia.don_gia_nuoc} required /></label>
          <div><button>Lưu</button></div>
        </form>
        <p className="muted">Đơn giá được lưu cố định vào từng hóa đơn lúc tạo. Đổi đơn giá không làm thay đổi hóa đơn cũ.</p>
      </div>
    </>
  );
}
