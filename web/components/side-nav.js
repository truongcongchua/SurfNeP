// Thanh bên trái của trang Bài tập / Study Plan (giống Library · Study Plan của LeetCode).
// `lists` (tuỳ chọn): mục "Danh sách của tôi" — lọc theo trạng thái làm bài.
import Link from "next/link";
import { Library, GraduationCap } from "lucide-react";

export function SideNav({ active, lists }) {
  return (
    <nav className="side-nav" aria-label="Điều hướng">
      <Link href="/" className={active === "problems" ? "on" : undefined}><Library /> Bài tập</Link>
      <Link href="/plans" className={active === "plans" ? "on" : undefined}><GraduationCap /> Study Plan</Link>
      {lists && (
        <>
          <hr />
          <div className="grp">Danh sách của tôi</div>
          <div className="sm">
            {lists.map((x) => (
              <Link key={x.key} href={x.href} className={x.on ? "on" : undefined}>{x.icon} {x.label} <span className="n">{x.count}</span></Link>
            ))}
          </div>
        </>
      )}
    </nav>
  );
}
