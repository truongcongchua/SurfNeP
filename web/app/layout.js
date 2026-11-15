import "./globals.css";
import Link from "next/link";
import { currentUser, logout } from "@/lib/auth";
import { redirect } from "next/navigation";

export const metadata = { title: "NetJudge IT4062", description: "Luyện lập trình mạng với bộ chấm tự động" };

async function doLogout() {
  "use server";
  await logout();
  redirect("/login");
}

export default async function RootLayout({ children }) {
  const user = await currentUser();
  return (
    <html lang="vi">
      <body>
        <header className="top">
          <div className="container">
            <Link href="/" className="brand">NetJudge · IT4062</Link>
            {user && (
              <>
                <nav>
                  <Link href="/">Bài tập</Link>
                  <Link href="/plans">Study Plan</Link>
                </nav>
                <form action={doLogout} className="who">
                  <span>{user.display || user.username}</span>
                  <button className="btn ghost">Đăng xuất</button>
                </form>
              </>
            )}
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
