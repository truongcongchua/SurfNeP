"use client";
// Thanh bên "Danh sách bài" trong trang làm bài (giống LeetCode): trượt từ trái ra trong 300ms,
// nền phía sau tối lại; tìm theo tên/số bài, lọc theo mức độ, bấm một bài để chuyển sang bài đó.
// Đóng bằng: nút X, bấm ra ngoài, phím Esc, hoặc khi đã chọn bài.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronRight, CircleDashed, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

const DIFF_COLOR = { easy: "text-[var(--easy)]", medium: "text-[var(--medium)]", hard: "text-[var(--hard)]" };
const RING = 2 * Math.PI * 7;

export function ProblemDrawer({ open, onClose, list, diffLabel, currentId }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [diff, setDiff] = useState("");
  const inputRef = useRef(null);
  const activeRef = useRef(null);

  const solved = list.filter((p) => p.status === "solved").length;
  const shown = useMemo(() => {
    const k = q.trim().toLowerCase();
    return list.filter((p) =>
      (!diff || p.difficulty === diff) &&
      (!k || p.title.toLowerCase().includes(k) || p.id.includes(k) || String(p.n) === k));
  }, [list, q, diff]);

  // Mở ra: focus ô tìm và cuộn tới bài đang làm. Esc để đóng.
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      inputRef.current?.focus({ preventScroll: true });
      activeRef.current?.scrollIntoView({ block: "center" });
    }, 50);
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => { clearTimeout(t); window.removeEventListener("keydown", onKey); };
  }, [open, onClose]);

  const go = (id) => {
    onClose();
    if (id !== currentId) router.push(`/problems/${id}`);
  };

  return (
    <div className={cn("fixed inset-0 z-50", !open && "pointer-events-none")} inert={!open}>
      {/* nền tối phía sau */}
      <div
        onClick={onClose}
        className={cn("absolute inset-0 bg-black/40 transition-opacity duration-300", open ? "opacity-100" : "opacity-0")}
      />
      <aside
        role="dialog" aria-label="Danh sách bài"
        className={cn(
          "absolute inset-y-0 left-0 flex w-[min(520px,92vw)] flex-col border-r border-[var(--line)] bg-[var(--panel)] shadow-2xl",
          "transition-transform duration-300 ease-[cubic-bezier(.32,.72,0,1)]",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 shrink-0 items-center gap-3 border-b border-[var(--line)] px-5">
          <Link href="/" onClick={onClose} className="flex items-center gap-1 text-[15px] font-semibold text-foreground hover:text-[var(--accent)] hover:no-underline">
            Danh sách bài <ChevronRight className="size-4" />
          </Link>
          <span className="ml-auto flex items-center gap-2 text-sm text-muted-foreground tabular-nums">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <circle cx="9" cy="9" r="7" fill="none" stroke="var(--raised)" strokeWidth="2.5" />
              <circle cx="9" cy="9" r="7" fill="none" stroke="var(--green)" strokeWidth="2.5" strokeLinecap="round"
                strokeDasharray={RING} strokeDashoffset={RING * (1 - (list.length ? solved / list.length : 0))} transform="rotate(-90 9 9)" />
            </svg>
            {solved}/{list.length} đã giải
          </span>
          <button onClick={onClose} aria-label="Đóng" className="flex size-8 items-center justify-center rounded-md text-muted-foreground hover:bg-[var(--raised)] hover:text-foreground">
            <X className="size-4" />
          </button>
        </div>

        <div className="flex shrink-0 items-center gap-2 px-4 py-3">
          <label className="flex h-8 flex-1 items-center gap-2 rounded-lg border border-[var(--line-strong)] bg-[var(--panel)] px-2.5 focus-within:border-[var(--accent)] focus-within:shadow-[0_0_0_3px_var(--accent-soft)]">
            <Search className="size-4 text-[var(--faint)]" />
            <input
              ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm theo tên hoặc số bài…"
              className="flex-1 text-sm"
              // style trực tiếp để thắng rule `input {...}` chung trong globals.css (không nằm trong layer).
              style={{ border: 0, background: "transparent", boxShadow: "none", padding: 0, height: "100%", minWidth: 0 }}
            />
          </label>
          <div className="flex h-8 items-center rounded-lg border border-[var(--line-strong)] p-0.5">
            {[["", "Tất cả"], ...Object.entries(diffLabel)].map(([k, v]) => (
              <button key={k} onClick={() => setDiff(k)}
                className={cn("h-full rounded-md px-2 text-xs font-medium transition-colors",
                  diff === k ? "bg-[var(--raised)] text-foreground" : "text-muted-foreground hover:text-foreground")}>
                {k === "medium" ? "TB" : v}
              </button>
            ))}
          </div>
        </div>

        <ul className="m-0 flex-1 list-none overflow-y-auto px-2 pb-3">
          {shown.length === 0 && <li className="px-3 py-6 text-center text-sm text-muted-foreground">Không có bài nào khớp.</li>}
          {shown.map((p) => {
            const on = p.id === currentId;
            return (
              <li key={p.id}>
                <button
                  ref={on ? activeRef : undefined}
                  onClick={() => go(p.id)}
                  className={cn(
                    "flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm transition-colors",
                    on ? "bg-[var(--solid)] text-[var(--solid-text)]" : "text-foreground hover:bg-[var(--raised)]"
                  )}
                >
                  <span className="flex w-4 shrink-0 justify-center">
                    {p.status === "solved" ? <Check className="size-4 text-[var(--green)]" strokeWidth={2.2} />
                      : p.status === "attempted" ? <CircleDashed className="size-4 text-[var(--medium)]" strokeWidth={2} /> : null}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-medium">
                    <span className={cn("mr-1.5 tabular-nums", on ? "opacity-60" : "text-[var(--faint)]")}>{p.n}.</span>{p.title}
                  </span>
                  <span className={cn("shrink-0 text-xs font-medium", DIFF_COLOR[p.difficulty])}>{diffLabel[p.difficulty]}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </aside>
    </div>
  );
}
