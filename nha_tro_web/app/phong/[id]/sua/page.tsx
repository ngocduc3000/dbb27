import { notFound } from "next/navigation";
import { Flash } from "@/components/Flash";
import { PhongForm } from "@/components/PhongForm";
import type { IdParams, SearchParams } from "@/lib/page";
import { createClient } from "@/lib/supabase/server";
import type { Phong } from "@/lib/types";

export default async function SuaPhong({ params, searchParams }: { params: IdParams; searchParams: SearchParams }) {
  const { id } = await params;
  const sb = await createClient();
  const { data } = await sb.from("phong").select("*").eq("id", id).maybeSingle();
  if (!data) notFound();
  const phong = data as Phong;
  return (
    <>
      <h1>Sửa phòng {phong.so_phong}</h1>
      <Flash params={await searchParams} />
      <PhongForm phong={phong} back={`/phong/${id}/sua`} />
    </>
  );
}
