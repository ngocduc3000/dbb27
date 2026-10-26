import { Flash } from "@/components/Flash";
import { PhongForm } from "@/components/PhongForm";
import type { SearchParams } from "@/lib/page";

export default async function ThemPhong({ searchParams }: { searchParams: SearchParams }) {
  return (
    <>
      <h1>Thêm phòng</h1>
      <Flash params={await searchParams} />
      <PhongForm back="/phong/them" />
    </>
  );
}
