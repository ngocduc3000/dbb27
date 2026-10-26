import type { Metadata } from "next";
import Link from "next/link";
import { dangXuat } from "./actions";
import { createClient } from "@/lib/supabase/server";
import "./globals.css";

export const metadata: Metadata = { title: "Quản lý nhà trọ" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const sb = await createClient();
  const { data } = await sb.auth.getClaims();
  const email = data?.claims?.email as string | undefined;

  return (
    <html lang="vi">
      <body>
        {email && (
          <nav>
            <Link href="/">Tổng quan</Link>
            <Link href="/phong">Phòng</Link>
            <Link href="/nguoi-thue">Người thuê</Link>
            <Link href="/chi-so">Chỉ số điện nước</Link>
            <Link href="/hoa-don">Hóa đơn</Link>
            <Link href="/cau-hinh">Đơn giá</Link>
            <form action={dangXuat}>
              <button title={email}>Đăng xuất</button>
            </form>
          </nav>
        )}
        <main>{children}</main>
      </body>
    </html>
  );
}
