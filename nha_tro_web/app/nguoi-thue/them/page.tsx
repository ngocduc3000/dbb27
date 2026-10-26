import { Flash } from "@/components/Flash";
import { NguoiForm } from "@/components/NguoiForm";
import { danhSachPhong } from "@/lib/data";
import { homNay, sp } from "@/lib/format";
import type { SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";

export default async function ThemNguoi({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const phongs = await danhSachPhong(await createClient());
  const phongId = Number(sp(params, "phong_id")) || undefined;
  return (
    <>
      <h1>Thêm người thuê</h1>
      <Flash params={params} />
      <NguoiForm phongs={phongs} phongId={phongId} homNay={homNay()}
        back={`/nguoi-thue/them${phongId ? `?phong_id=${phongId}` : ""}`} />
    </>
  );
}
