"use client";
// Tab "Gợi ý" (HintsPanel: mở từng bậc một) và tab "Kiến thức" (KnowledgePanel: thẻ khái niệm theo chương / lecture note).
import { useState } from "react";
import { BookOpen, ChevronDown, Lightbulb, Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLocal } from "@/components/workspace/use-settings";

const LEVEL = ["Hướng nghĩ", "Hàm và cấu trúc cần dùng", "Chi tiết dễ sai"];

export function HintsPanel({ problemId, hints }) {
  // Số bậc đã mở lưu theo từng bài; mở rồi thì giữ lại để xem lại.
  const [shown, setShown] = useLocal(`nj-hints-${problemId}`, 0);
  const n = Math.min(Math.max(Number(shown) || 0, 0), hints.length);

  return (
    <div className="px-4 pb-6 pt-5">
    <section className="rounded-lg border border-[var(--line)] bg-[var(--panel)]">
      <div className="flex items-center gap-2 px-3 py-2.5">
        <Lightbulb className="size-4 shrink-0 text-[var(--brand)]" />
        <span className="flex-1 text-sm font-medium text-[var(--title)]">Gợi ý theo bậc</span>
        <span className="text-xs text-[var(--muted)]">{n}/{hints.length} đã mở</span>
      </div>
      <ol className="flex flex-col gap-2 border-t border-[var(--line)] p-3">
        {hints.map((h, i) => (
          <li key={i} className={cn("rounded-md border border-[var(--line)] px-3", i < n ? "bg-[var(--bg)]" : "bg-transparent")}>
            {i < n ? (
              <>
                <div className="pt-2 text-xs font-medium text-[var(--muted)]">Bậc {i + 1}: {LEVEL[i] || "Gợi ý"}</div>
                <div className="lc-prose pt-1" dangerouslySetInnerHTML={{ __html: h }} />
              </>
            ) : (
              <div className="flex items-center gap-2 py-2 text-xs text-[var(--muted)]">
                <Lock className="size-3.5" />
                <span className="flex-1">Bậc {i + 1}: {LEVEL[i] || "Gợi ý"}</span>
                {i === n && (
                  <button
                    onClick={() => setShown(i + 1)}
                    className="rounded-md bg-[var(--chip)] px-2 py-1 text-xs font-medium text-[var(--title)] hover:bg-[var(--raised)]"
                  >
                    Mở gợi ý
                  </button>
                )}
              </div>
            )}
          </li>
        ))}
      </ol>
      {n > 0 && (
        <div className="border-t border-[var(--line)] px-3 py-1.5 text-right">
          <button onClick={() => setShown(0)} className="text-xs text-[var(--muted)] hover:text-[var(--title)]">Ẩn lại tất cả</button>
        </div>
      )}
    </section>
    </div>
  );
}

export function KnowledgePanel({ cards }) {
  // Thẻ đầu mở sẵn; còn lại gập lại cho gọn.
  const [open, setOpen] = useState(() => ({ [cards[0]?.id]: true }));
  const toggle = (id) => setOpen((o) => ({ ...o, [id]: !o[id] }));
  const allOpen = cards.every((c) => open[c.id]);

  return (
    <div className="px-4 pb-6 pt-5">
      {cards.length > 0 && (
        <>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-base font-medium text-[var(--title)]">Kiến thức cần dùng</h2>
            <button
              onClick={() => setOpen(Object.fromEntries(cards.map((c) => [c.id, !allOpen])))}
              className="text-xs text-[var(--muted)] hover:text-[var(--title)]"
            >
              {allOpen ? "Thu gọn tất cả" : "Mở tất cả"}
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {cards.map((c) => (
              <section key={c.id} className="rounded-lg border border-[var(--line)] bg-[var(--panel)]">
                <button
                  onClick={() => toggle(c.id)}
                  aria-expanded={!!open[c.id]}
                  className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
                >
                  <BookOpen className="size-4 shrink-0 text-[var(--accent)]" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-[var(--title)]">{c.title}</span>
                    {c.ref && <span className="block truncate text-xs text-[var(--muted)]">{c.ref}</span>}
                  </span>
                  <ChevronDown className={cn("size-4 shrink-0 text-[var(--muted)] transition-transform", open[c.id] && "rotate-180")} />
                </button>
                {open[c.id] && <div className="lc-prose border-t border-[var(--line)] px-3 pb-1 pt-1" dangerouslySetInnerHTML={{ __html: c.html }} />}
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
