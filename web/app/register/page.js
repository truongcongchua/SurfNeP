import Link from "next/link";
import { redirect } from "next/navigation";
import { register, currentUser } from "@/lib/auth";
import { Logo } from "@/components/logo";

async function doRegister(formData) {
  "use server";
  const r = await register({
    username: formData.get("username"),
    password: formData.get("password"),
    confirm: formData.get("confirm"),
    invite: formData.get("invite"),
  });
  if (r.ok) redirect("/");
  redirect(`/register?e=${encodeURIComponent(r.error)}`);
}

export default async function RegisterPage({ searchParams }) {
  if (await currentUser()) redirect("/");
  const { e } = await searchParams;
  const closed = process.env.NJ_SIGNUP === "0";
  return (
    <div className="login-wrap">
      <form action={doRegister} className="login">
        <div className="lg">
          <span className="logo"><Logo size={48} strokeWidth={2} /></span>
          Tạo tài khoản
        </div>
        {closed ? (
          <div className="err">Đăng ký đang tạm đóng.</div>
        ) : (
          <>
            {e && <div className="err">{e}</div>}
            <input name="username" placeholder="Tên đăng nhập (a–z, 0–9, _)" aria-label="Tên đăng nhập" autoComplete="username" minLength={3} maxLength={20} pattern="[a-zA-Z0-9_]{3,20}" autoFocus required />
            <input name="password" type="password" placeholder="Mật khẩu (≥ 8 ký tự)" aria-label="Mật khẩu" autoComplete="new-password" minLength={8} maxLength={128} required />
            <input name="confirm" type="password" placeholder="Nhập lại mật khẩu" aria-label="Nhập lại mật khẩu" autoComplete="new-password" required />
            {process.env.NJ_INVITE_CODE && <input name="invite" placeholder="Mã mời" aria-label="Mã mời" required />}
            <button>Đăng ký</button>
          </>
        )}
        <p className="alt">Đã có tài khoản? <Link href="/login">Đăng nhập</Link></p>
      </form>
    </div>
  );
}
