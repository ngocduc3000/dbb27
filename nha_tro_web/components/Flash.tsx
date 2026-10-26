import { sp } from "@/lib/format";

export function Flash({ params }: { params: Record<string, string | string[] | undefined> }) {
  const loi = sp(params, "loi");
  const ok = sp(params, "ok");
  return (
    <>
      {loi && <div className="flash loi">{loi}</div>}
      {ok && <div className="flash ok">{ok}</div>}
    </>
  );
}
