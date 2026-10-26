import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { supabaseEnv } from "@/lib/supabase/env";

// Chạy trước mọi trang: làm mới session Supabase, chưa đăng nhập thì chuyển về /login.
export async function proxy(request: NextRequest) {
  let response = NextResponse.next({ request });
  const { url, key } = supabaseEnv();

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet, headers) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
        Object.entries(headers ?? {}).forEach(([k, v]) => response.headers.set(k, v));
      },
    },
  });

  const { data } = await supabase.auth.getClaims();
  const daDangNhap = !!data?.claims?.sub;
  const laTrangLogin = request.nextUrl.pathname.startsWith("/login");

  if (!daDangNhap && !laTrangLogin) {
    const u = request.nextUrl.clone();
    u.pathname = "/login";
    u.search = "";
    return NextResponse.redirect(u);
  }
  if (daDangNhap && laTrangLogin) {
    const u = request.nextUrl.clone();
    u.pathname = "/";
    u.search = "";
    return NextResponse.redirect(u);
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
