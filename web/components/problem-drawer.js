"use client";
// Thanh bên "Danh sách bài" trong trang làm bài (giống LeetCode): rộng 600px, trượt từ trái ra trong 300ms,
// nền phía sau tối lại; tìm theo tên/số bài, lọc theo mức độ / trạng thái, sắp xếp; bấm một bài để chuyển sang bài đó.
// Hàng cao 44px bo 8px, hàng lẻ nền nhạt, bài đang làm nền đen chữ trắng; dấu ✓ xanh lá cho bài đã giải.
// Đóng bằng: nút X, bấm ra ngoài, phím Esc, hoặc khi đã chọn bài.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpDown, Check, ChevronRight, CircleDashed, ListFilter, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

const DIFF_COLOR = { easy: "text-[var(--easy)]", medium: "text-[var(--medium)]", hard: "text-[var(--hard)]" };
const DIFF_SHORT = { easy: "Dễ", medium: "TB", hard: "Khó" };
const RING = 2 * Math.PI * 6;
const ORDER = { easy: 0, medium: 1, hard: 2 };

function Menu({ icon: Icon, label, active, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen((v) => !v)} title={label} aria-label={label}
        className={cn("relative flex size-8 items-center justify-center rounded-lg bg-[var(--fill-3)] text-[var(--icon)] hover:bg-[var(--fill-4)] hover:text-[var(--title)]", open && "text-[var(--title)]")}>
        <Icon className="size-4" />
        {active && <span className="absolute right-1 top-1 size-1.5 rounded-full bg-[var(--hard)]" />}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-10 z-20 w-44 rounded-lg bg-[var(--panel)] p-1 text-sm shadow-[var(--pop-shadow)]" onClick={() => setOpen(false)}>{children}</div>
        </>
      )}
    </div>
  );
}
const Opt = ({ on, onClick, children }) => (
  <button onClick={onClick} className="flex h-8 w-full items-center gap-2 rounded px-2 text-left text-[var(--title)] hover:bg-[var(--raised)]">
    <Check className={cn("size-3.5 text-[var(--green)]", !on && "opacity-0")} />{children}
  </button>
);

export function ProblemDrawer({ open, onClose, list, diffLabel, currentId }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [diff, setDiff] = useState("");
  const [state, setState] = useState("");
  const [sort, setSort] = useState("");
  const inputRef = useRef(null);
  const activeRef = useRef(null);

  const solved = list.filter((p) => p.status === "solved").length;
  const shown = useMemo(() => {
    const k = q.trim().toLowerCase();
    const out = list.filter((p) =>
      (!diff || p.difficulty === diff) && (!state || p.status === state) &&
      (!k || p.title.toLowerCase().includes(k) || p.id.includes(k) || String(p.n) === k));
    if (sort === "asc") out.sort((a, b) => ORDER[a.difficulty] - ORDER[b.difficulty]);
    if (sort === "desc") out.sort((a, b) => ORDER[b.difficulty] - ORDER[a.difficulty]);
    return out;
  }, [list, q, diff, state, sort]);

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
      <div onClick={onClose} className={cn("absolute inset-0 bg-black/50 transition-opacity duration-300", open ? "opacity-100" : "opacity-0")} />
      <aside
        role="dialog" aria-label="Danh sách bài"
        className={cn(
          "absolute inset-y-0 left-0 flex w-[min(600px,92vw)] flex-col bg-[var(--panel)]",
          "transition-transform duration-300 ease-[cubic-bezier(.32,.72,0,1)]",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-[69px] shrink-0 items-center gap-3 border-b border-[var(--line)] px-6">
          <Link href="/" onClick={onClose} className="flex items-center gap-1 text-xl font-medium text-[var(--title)] hover:text-[var(--title)]">
            Danh sách bài <ChevronRight className="size-4 text-[var(--icon)]" />
          </Link>
          <span className="ml-auto flex items-center gap-2 text-sm font-medium tabular-nums text-[var(--text)]">
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <circle cx="8" cy="8" r="6" fill="none" stroke="var(--line-strong)" strokeWidth="2" />
              <circle cx="8" cy="8" r="6" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round"
                strokeDasharray={RING} strokeDashoffset={RING * (1 - (list.length ? solved / list.length : 0))} transform="rotate(-90 8 8)" />
            </svg>
            {solved}/{list.length} đã giải
          </span>
          <button onClick={onClose} aria-label="Đóng" className="flex size-8 items-center justify-center rounded-md text-[var(--icon)] hover:bg-[var(--fill-3)] hover:text-[var(--title)]">
            <X className="size-5" />
          </button>
        </div>

        <div className="flex shrink-0 items-center gap-2 px-4 py-4">
          <label className="flex h-8 w-52 items-center gap-2 rounded-full bg-[var(--fill-3)] px-3 focus-within:shadow-[0_0_0_1px_var(--line-strong)]">
            <Search className="size-4 text-[var(--icon)]" />
            <input
              ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm bài"
              className="min-w-0 flex-1 text-sm placeholder:text-[var(--text2)]"
              // style trực tiếp để thắng rule `input {...}` chung trong globals.css (không nằm trong layer).
              style={{ border: 0, outline: "none", background: "transparent", boxShadow: "none", padding: 0, height: "100%", color: "var(--text)" }}
            />
          </label>
          <Menu icon={ArrowUpDown} label="Sắp xếp" active={!!sort}>
            <Opt on={!sort} onClick={() => setSort("")}>Mặc định</Opt>
            <Opt on={sort === "asc"} onClick={() => setSort("asc")}>Dễ → Khó</Opt>
            <Opt on={sort === "desc"} onClick={() => setSort("desc")}>Khó → Dễ</Opt>
          </Menu>
          <Menu icon={ListFilter} label="Lọc" active={!!(diff || state)}>
            <div className="px-2 pb-1 pt-1.5 text-xs text-[var(--muted)]">Mức độ</div>
            <Opt on={!diff} onClick={() => setDiff("")}>Tất cả</Opt>
            {Object.entries(diffLabel).map(([k, v]) => <Opt key={k} on={diff === k} onClick={() => setDiff(k)}>{v}</Opt>)}
            <div className="px-2 pb-1 pt-2 text-xs text-[var(--muted)]">Trạng thái</div>
            <Opt on={!state} onClick={() => setState("")}>Tất cả</Opt>
            <Opt on={state === "solved"} onClick={() => setState("solved")}>Đã giải</Opt>
            <Opt on={state === "attempted"} onClick={() => setState("attempted")}>Đang thử</Opt>
            <Opt on={state === "todo"} onClick={() => setState("todo")}>Chưa làm</Opt>
          </Menu>
        </div>

        <ul className="m-0 flex-1 list-none overflow-y-auto px-4 pb-4">
          {shown.length === 0 && <li className="px-3 py-6 text-center text-sm text-[var(--muted)]">Không có bài nào khớp.</li>}
          {shown.map((p, i) => {
            const on = p.id === currentId;
            return (
              <li key={p.id}>
                <button
                  ref={on ? activeRef : undefined}
                  onClick={() => go(p.id)}
                  className={cn(
                    "flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm transition-colors",
                    on ? "bg-[var(--solid)] font-medium text-[var(--solid-text)]" : cn("text-[var(--text)] hover:bg-[var(--fill-2)]", i % 2 === 0 && "bg-[var(--zebra)]")
                  )}
                >
                  <span className="flex w-4 shrink-0 justify-center">
                    {p.status === "solved" ? <Check className={cn("size-4", on ? "text-[#28c244]" : "text-[var(--submit)]")} strokeWidth={2.2} />
                      : p.status === "attempted" ? <CircleDashed className="size-4 text-[var(--medium)]" strokeWidth={2} /> : null}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{p.n}. {p.title}</span>
                  <span className={cn("shrink-0 text-sm", DIFF_COLOR[p.difficulty])}>{DIFF_SHORT[p.difficulty]}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </aside>
    </div>
  );
}
