import { redirect } from "next/navigation";
import { login, currentUser } from "@/lib/auth";

async function doLogin(formData) {
  "use server";
  const ok = await login(formData.get("username"), formData.get("password"));
  redirect(ok ? "/" : "/login?e=1");
}

export default async function LoginPage({ searchParams }) {
  if (await currentUser()) redirect("/");
  const { e } = await searchParams;
  return (
    <form action={doLogin} className="card login">
      <h1 style={{ marginTop: 0 }}>Đăng nhập</h1>
      {e && <div className="err">Sai tên đăng nhập hoặc mật khẩu.</div>}
      <label>Tên đăng nhập<input name="username" autoComplete="username" autoFocus required /></label>
      <label>Mật khẩu<input name="password" type="password" autoComplete="current-password" required /></label>
      <button className="btn" style={{ width: "100%" }}>Đăng nhập</button>
    </form>
  );
}
