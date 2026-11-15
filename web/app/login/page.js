import { redirect } from "next/navigation";
import { login, currentUser } from "@/lib/auth";
import { Logo } from "@/components/logo";

async function doLogin(formData) {
  "use server";
  const ok = await login(formData.get("username"), formData.get("password"));
  redirect(ok ? "/" : "/login?e=1");
}

export default async function LoginPage({ searchParams }) {
  if (await currentUser()) redirect("/");
  const { e } = await searchParams;
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <form action={doLogin} className="card login">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <Logo size={24} color="var(--accent)" />
          <span style={{ fontWeight: 700, fontSize: 18 }}>SurfNeP</span>
        </div>
        <h1 style={{ marginTop: 0, marginBottom: 4 }}>Đăng nhập</h1>
        <p className="sub" style={{ margin: '0 0 20px' }}>Nền tảng luyện lập trình mạng</p>
        {e && <div className="err">Sai tên đăng nhập hoặc mật khẩu.</div>}
        <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--muted)' }}>Tên đăng nhập<input name="username" autoComplete="username" autoFocus required /></label>
        <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--muted)' }}>Mật khẩu<input name="password" type="password" autoComplete="current-password" required /></label>
        <button className="btn" style={{ width: '100%', marginTop: 6, padding: '9px 16px' }}>Đăng nhập</button>
      </form>
    </div>
  );
}
