import "./globals.css";
import Link from "next/link";
import { currentUser } from "@/lib/auth";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { NavLink } from "@/components/nav-link";
import { UserMenu } from "@/components/user-menu";
import { Logo } from "@/components/logo";

export const metadata = { title: "SurfNeP IT4062", description: "Luyện lập trình mạng với bộ chấm tự động" };

export default async function RootLayout({ children }) {
  const user = await currentUser();
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem disableTransitionOnChange>
          {user && (
            <header className="top">
              <div className="bar">
                <Link href="/" className="brand"><span className="logo"><Logo size={22} strokeWidth={2.2} /></span>SurfNeP</Link>
                <nav>
                  <NavLink href="/problems" also={["/plans"]}>Bài tập</NavLink>
                  <NavLink href="/contest">Cuộc thi</NavLink>
                  <NavLink href="/learn">Ôn tập</NavLink>
                </nav>
                <div className="right">
                  <ThemeToggle />
                  <UserMenu name={user.display || user.username} admin={user.role === "admin"} />
                </div>
              </div>
            </header>
          )}
          <main>{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
