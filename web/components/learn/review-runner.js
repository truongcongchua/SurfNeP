"use client";
// Phiên ôn flashcard: lật thẻ, tự chấm Lại / Khó / Được / Dễ. "Lại" đưa thẻ về cuối hàng đợi của phiên này.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { marked } from "marked";
import { cn } from "@/lib/utils";

const GRADES = [
  { g: 0, label: "Lại", hint: "Quên", cls: "border-[var(--hard)] text-[var(--hard)]" },
  { g: 1, label: "Khó", hint: "Nhớ chậm", cls: "border-[var(--medium)] text-[var(--medium)]" },
  { g: 2, label: "Được", hint: "Nhớ", cls: "border-[var(--line)] text-[var(--title)]" },
  { g: 3, label: "Dễ", hint: "Nhớ ngay", cls: "border-[var(--easy)] text-[var(--easy)]" },
];
const md = (s) => marked.parse(String(s), { async: false });

export function ReviewRunner({ cards, stats }) {
  const [queue, setQueue] = useState(cards);
  const [flip, setFlip] = useState(false);
  const [done, setDone] = useState(0);
  const [again, setAgain] = useState(0);
  const [busy, setBusy] = useState(false);
  const total = useRef(cards.length);
  const cur = queue[0];

  const rate = async (g) => {
    if (busy || !cur) return;
    setBusy(true);
    try {
      await fetch("/api/learn/review", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ card: cur.id, grade: g }) });
    } catch {}
    setQueue((q) => (g === 0 ? [...q.slice(1), q[0]] : q.slice(1)));
    if (g === 0) setAgain((n) => n + 1); else setDone((n) => n + 1);
    setFlip(false);
    setBusy(false);
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.closest?.("input, textarea")) return;
      if (e.code === "Space") { e.preventDefault(); setFlip((f) => !f); }
      else if (flip && ["1", "2", "3", "4"].includes(e.key)) rate(Number(e.key) - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!total.current) {
    return (
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-8 text-center">
        <div className="text-lg font-medium text-[var(--title)]">Hôm nay không còn thẻ nào</div>
        <p className="mt-1 text-sm text-[var(--muted)]">Bạn đã học {stats.learned}/{stats.total} thẻ. Quay lại vào ngày mai để ôn các thẻ đến hạn.</p>
        <div className="mt-4 flex justify-center gap-2">
          <Link href="/learn/quiz" className="rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white">Làm quiz</Link>
          <Link href="/learn/progress" className="rounded-md bg-[var(--chip)] px-4 py-2 text-sm text-[var(--title)]">Xem điểm yếu</Link>
        </div>
      </div>
    );
  }

  if (!cur) {
    return (
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-8 text-center">
        <div className="text-lg font-medium text-[var(--title)]">Xong phiên ôn</div>
        <p className="mt-1 text-sm text-[var(--muted)]">{done} thẻ hoàn thành{again > 0 && `, ${again} lần bấm "Lại"`}.</p>
        <div className="mt-4 flex justify-center gap-2">
          <Link href="/learn/progress" className="rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white">Xem điểm yếu</Link>
          <Link href="/learn" className="rounded-md bg-[var(--chip)] px-4 py-2 text-sm text-[var(--title)]">Về tổng quan</Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--chip)]">
          <div className="h-full bg-[var(--brand)]" style={{ width: `${(100 * done) / total.current}%` }} />
        </div>
        <span className="text-xs text-[var(--muted)]">Còn {queue.length} thẻ</span>
      </div>

      <div
        onClick={() => setFlip((f) => !f)}
        role="button"
        tabIndex={0}
        className="flex min-h-56 cursor-pointer flex-col justify-center rounded-lg border border-[var(--line)] bg-[var(--panel)] p-6"
      >
        <div className="mb-3 text-xs text-[var(--muted)]">{flip ? "Đáp án" : "Câu hỏi"}</div>
        <div className="lc-prose" dangerouslySetInnerHTML={{ __html: md(flip ? cur.a : cur.q) }} />
        {!flip && <div className="mt-4 text-xs text-[var(--faint)]">Bấm vào thẻ hoặc phím Space để xem đáp án</div>}
      </div>

      <div className={cn("mt-4 grid grid-cols-4 gap-2", !flip && "pointer-events-none opacity-40")}>
        {GRADES.map((x) => (
          <button key={x.g} onClick={() => rate(x.g)} disabled={busy || !flip} className={cn("rounded-md border bg-[var(--panel)] px-2 py-2.5 text-center hover:bg-[var(--raised)]", x.cls)}>
            <div className="text-sm font-medium">{x.label}</div>
            <div className="text-[11px] text-[var(--muted)]">{x.hint} · {x.g + 1}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
