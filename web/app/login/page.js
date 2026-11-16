import Link from "next/link";
import { redirect } from "next/navigation";
import { login, currentUser } from "@/lib/auth";
import { Logo } from "@/components/logo";

async function doLogin(formData) {
  "use server";
  const r = await login(formData.get("username"), formData.get("password"));
  redirect(r === "ok" ? "/" : `/login?e=${r}`);
}

const MSG = {
  bad: "Sai tên đăng nhập hoặc mật khẩu.",
  locked: "Sai quá nhiều lần, thử lại sau 15 phút.",
  disabled: "Tài khoản đã bị khoá.",
};

export default async function LoginPage({ searchParams }) {
  if (await currentUser()) redirect("/");
  const { e } = await searchParams;
  return (
    <div className="login-wrap">
      <form action={doLogin} className="login">
        <div className="lg">
          <span className="logo"><Logo size={48} strokeWidth={2} /></span>
          SurfNeP
        </div>
        {e && <div className="err">{MSG[e] || MSG.bad}</div>}
        <input name="username" placeholder="Tên đăng nhập" aria-label="Tên đăng nhập" autoComplete="username" autoFocus required />
        <input name="password" type="password" placeholder="Mật khẩu" aria-label="Mật khẩu" autoComplete="current-password" required />
        <button>Đăng nhập</button>
        {process.env.NJ_SIGNUP !== "0" && (
          <p className="alt">Chưa có tài khoản? <Link href="/register">Đăng ký</Link></p>
        )}
      </form>
    </div>
  );
}
