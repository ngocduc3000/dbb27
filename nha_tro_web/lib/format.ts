/** 3680000 → "3.680.000" */
export function vnd(n: number | null | undefined): string {
  return Math.trunc(Number(n ?? 0)).toLocaleString("vi-VN");
}

/** Ngày hôm nay theo giờ Việt Nam, dạng YYYY-MM-DD (server Vercel chạy giờ UTC). */
export function homNay(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Ho_Chi_Minh" }).format(new Date());
}

/** Ngày đầu và cuối của tháng chứa ngày d (YYYY-MM-DD). */
export function dauCuoiThang(d: string): [string, string] {
  const [y, m] = d.split("-").map(Number);
  const cuoi = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const mm = String(m).padStart(2, "0");
  return [`${y}-${mm}-01`, `${y}-${mm}-${String(cuoi).padStart(2, "0")}`];
}

export function dinhDangNgay(d: string | null | undefined): string {
  if (!d) return "";
  const [y, m, day] = d.slice(0, 10).split("-");
  return `${day}/${m}/${y}`;
}

type SP = Record<string, string | string[] | undefined>;
export function sp(params: SP, key: string): string {
  const v = params[key];
  return (Array.isArray(v) ? v[0] : v) ?? "";
}
