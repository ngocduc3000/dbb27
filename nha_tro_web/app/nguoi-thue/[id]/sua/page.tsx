import { notFound } from "next/navigation";
import { Flash } from "@/components/Flash";
import { NguoiForm } from "@/components/NguoiForm";
import { danhSachPhong } from "@/lib/data";
import { homNay } from "@/lib/format";
import type { IdParams, SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { NguoiThue } from "@/lib/types";

export default async function SuaNguoi({ params, searchParams }: { params: IdParams; searchParams: SearchParams }) {
  const { id } = await params;
  const sb = await createClient();
  const [{ data }, phongs] = await Promise.all([
    sb.from("nguoi_thue").select("*").eq("id", id).maybeSingle(),
    danhSachPhong(sb),
  ]);
  if (!data) notFound();
  return (
    <>
      <h1>Sửa người thuê</h1>
      <Flash params={await searchParams} />
      <NguoiForm nguoi={data as NguoiThue} phongs={phongs} homNay={homNay()} back={`/nguoi-thue/${id}/sua`} />
    </>
  );
}
