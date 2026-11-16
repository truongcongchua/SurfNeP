"use client";
// Mục điều hướng trên header: đánh dấu mục đang mở bằng gạch chân như thanh nav của LeetCode.
import Link from "next/link";
import { usePathname } from "next/navigation";

// `also`: các tiền tố đường dẫn khác thuộc cùng mục (vd. Study Plan nằm trong mục "Bài tập").
export function NavLink({ href, also = [], children }) {
  const path = usePathname();
  const on = [href, ...also].some((x) => path.startsWith(x));
  return <Link href={href} className={on ? "on" : undefined}>{children}</Link>;
}
