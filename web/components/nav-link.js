"use client";
// Mục điều hướng trên header: đánh dấu mục đang mở bằng gạch chân như thanh nav của LeetCode.
import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLink({ href, children }) {
  const path = usePathname();
  const on = href === "/" ? path === "/" || path.startsWith("/problems") : path.startsWith(href);
  return <Link href={href} className={on ? "on" : undefined}>{children}</Link>;
}
