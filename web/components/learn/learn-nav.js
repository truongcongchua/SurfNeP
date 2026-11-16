"use client";
// Thanh tab của khu vực Ôn tập.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  ["/learn", "Tổng quan", true],
  ["/learn/review", "Flashcard"],
  ["/learn/quiz", "Quiz"],
  ["/learn/bugs", "Tìm bug"],
  ["/learn/cheatsheet", "Cheat sheet"],
  ["/learn/progress", "Điểm yếu"],
];

export function LearnNav({ due = 0 }) {
  const path = usePathname();
  return (
    <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-[var(--line)]" aria-label="Ôn tập">
      {TABS.map(([href, label, exact]) => {
        const on = exact ? path === href || path.startsWith("/learn/c/") : path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm transition-colors",
              on ? "border-[var(--brand)] font-medium text-[var(--title)]" : "border-transparent text-[var(--muted)] hover:text-[var(--title)]"
            )}
          >
            {label}
            {href === "/learn/review" && due > 0 && (
              <span className="rounded-full bg-[var(--brand)] px-1.5 text-[11px] font-medium leading-4 text-white">{due}</span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
