import { dangNhap } from "../actions";
import { Flash } from "@/components/Flash";
import type { SearchParams } from "@/lib/page";

export default async function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <div className="card login">
      <h1>Quản lý nhà trọ</h1>
      <Flash params={await searchParams} />
      <form action={dangNhap} className="f" style={{ gridTemplateColumns: "1fr" }}>
        <label>Email<input name="email" type="email" required autoComplete="username" /></label>
        <label>Mật khẩu<input name="password" type="password" required autoComplete="current-password" /></label>
        <button>Đăng nhập</button>
      </form>
    </div>
  );
}
