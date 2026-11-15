import "./globals.css";
import Link from "next/link";
import { currentUser, logout } from "@/lib/auth";
import { redirect } from "next/navigation";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { NavLink } from "@/components/nav-link";
import { Logo } from "@/components/logo";

const inter = Inter({ subsets: ["latin", "vietnamese"], axes: ["opsz"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin", "vietnamese"], variable: "--font-jetbrains", display: "swap" });

export const metadata = { title: "SurfNeP IT4062", description: "Luyện lập trình mạng với bộ chấm tự động" };

async function doLogout() {
  "use server";
  await logout();
  redirect("/login");
}

export default async function RootLayout({ children }) {
  const user = await currentUser();
  return (
    <html lang="vi" suppressHydrationWarning className={`${inter.variable} ${mono.variable}`}>
      <body>
        <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem disableTransitionOnChange>
        <header className="top">
          <div className="container">
            <Link href="/" className="brand"><span className="logo"><Logo size={14} strokeWidth={2} /></span>SurfNeP</Link>
            {!user && <span style={{ flex: 1 }} />}
            {user && (
              <>
                <nav>
                  <NavLink href="/">Bài tập</NavLink>
                  <NavLink href="/plans">Study Plan</NavLink>
                </nav>
                <form action={doLogout} className="who">
                  <span>{user.display || user.username}</span>
                  <button className="btn ghost">Đăng xuất</button>
                </form>
              </>
            )}
            <ThemeToggle />
          </div>
        </header>
        <main className="container" style={{ paddingTop: 8 }}>{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
