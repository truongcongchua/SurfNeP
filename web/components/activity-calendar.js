"use client";
// Lịch tháng kiểu LeetCode: chấm đỏ ở ngày có làm bài, bấm ngày để tới bài đã làm hôm đó
// (một bài: mở thẳng; nhiều bài: hiện danh sách ngay dưới lịch).
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Check, ChevronLeft, ChevronRight, X } from "lucide-react";

// Nút chuyển tháng: phẳng, không viền/khung mặc định của trình duyệt; chỉ nền mờ khi rê chuột, vòng focus chỉ hiện khi dùng bàn phím.
const NAV = "flex size-6 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent p-0 text-[var(--icon)] outline-none transition-colors duration-150 hover:bg-[var(--fill-3)] active:bg-[var(--fill-3)] focus-visible:ring-2 focus-visible:ring-[var(--line-strong)] disabled:cursor-default disabled:opacity-30 disabled:hover:bg-transparent";
const DOW =["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const key = (y, m, d) => `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

// days: { "YYYY-MM-DD": [{ id, title, solved }] }, today: "YYYY-MM-DD" (giờ máy chủ)
export function ActivityCalendar({ days, today }) {
  const router = useRouter();
  const [ty, tm] = today.split("-").map(Number);
  const [view, setView] = useState({ y: ty, m: tm - 1 });
  const [picked, setPicked] = useState(null);

  const first = new Date(view.y, view.m, 1);
  const lead = (first.getDay() + 6) % 7; // thứ Hai là cột đầu
  const count = new Date(view.y, view.m + 1, 0).getDate();
  const cells = [...Array(lead).fill(null), ...Array.from({ length: count }, (_, i) => i + 1)];
  const atNow = view.y === ty && view.m === tm - 1;
  const shift = (n) => { setPicked(null); setView((v) => { const d = new Date(v.y, v.m + n, 1); return { y: d.getFullYear(), m: d.getMonth() }; }); };
  const list = picked ? days[picked] || [] : [];

  const open = (k) => {
    const items = days[k];
    if (!items?.length) return;
    if (items.length === 1) router.push(`/problems/${items[0].id}`);
    else setPicked(picked === k ? null : k);
  };

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <b className="text-sm font-medium text-[var(--title)]">Tháng {view.m + 1}<small className="ml-1.5 text-xs font-normal text-[var(--muted)]">{view.y}</small></b>
        <span className="flex items-center gap-0.5">
          <button onClick={() => shift(-1)} aria-label="Tháng trước" className={NAV}><ChevronLeft className="size-4" /></button>
          <button onClick={() => shift(1)} disabled={atNow} aria-label="Tháng sau" className={NAV}><ChevronRight className="size-4" /></button>
        </span>
      </div>
      <div className="cal">
        {DOW.map((w) => <span key={w} className="dow">{w}</span>)}
        {cells.map((d, i) => {
          if (!d) return <span key={`e${i}`} />;
          const k = key(view.y, view.m, d);
          const items = days[k];
          const isToday = k === today;
          const cls = `day${isToday ? " today" : ""}${picked === k ? " picked" : ""}${items ? " has" : ""}`;
          const inner = <>{d}{items && <i style={{ background: items.some((x) => x.solved) ? "var(--green)" : "var(--hard)" }} />}</>;
          return items
            ? <button key={k} onClick={() => open(k)} className={cls} title={`${items.length} bài đã làm`}>{inner}</button>
            : <span key={k} className={`${cls} idle`}>{inner}</span>;
        })}
      </div>
      {picked && (
        <div className="mt-3 rounded-lg bg-[var(--fill-3)] p-2.5 text-sm">
          <div className="mb-1.5 flex items-center justify-between text-xs text-[var(--muted)]">
            <span>Bài đã làm ngày {picked.split("-").reverse().join("/")}</span>
            <button onClick={() => setPicked(null)} aria-label="Đóng" className="hover:text-[var(--title)]"><X className="size-3.5" /></button>
          </div>
          <ul className="m-0 list-none space-y-1 p-0">
            {list.map((p) => (
              <li key={p.id}>
                <Link href={`/problems/${p.id}`} className="flex items-center gap-1.5 text-[var(--text)] hover:text-[var(--accent)]">
                  <Check className={`size-3.5 shrink-0 ${p.solved ? "text-[var(--green)]" : "text-[var(--faint)]"}`} />
                  <span className="truncate">{p.title}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
