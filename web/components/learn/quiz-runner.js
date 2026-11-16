"use client";
// Chạy một lượt quiz: mcq (chọn 1) · order (bấm lần lượt để xếp thứ tự) · fill (điền chỗ trống trong code).
import Link from "next/link";
import { useMemo, useState } from "react";
import { marked } from "marked";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

const norm = (s) => String(s).trim().replace(/\s+/g, " ");
const md = (s) => marked.parse(String(s), { async: false });
const mdi = (s) => marked.parseInline(String(s), { async: false });

function shuffled(arr, seed) {
  const a = arr.map((v, i) => [v, i]);
  // Xáo trộn có hạt giống (ổn định giữa các lần render), bảo đảm không trùng thứ tự đúng.
  let s = seed;
  const rnd = () => ((s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296);
  for (let k = 0; k < 4; k++) {
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    if (a.some(([, idx], pos) => idx !== pos)) break;
  }
  return a;
}

function Mcq({ q, done, onAnswer }) {
  const [pick, setPick] = useState(null);
  return (
    <ul className="space-y-2">
      {q.options.map((o, i) => {
        const chosen = pick === i;
        const right = done && i === q.answer;
        const wrong = done && chosen && i !== q.answer;
        return (
          <li key={i}>
            <button
              disabled={done}
              onClick={() => { setPick(i); onAnswer(i === q.answer); }}
              className={cn(
                "flex w-full items-start gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors",
                !done && "border-[var(--line)] hover:bg-[var(--raised)]",
                right && "border-[var(--easy)] bg-[color-mix(in_srgb,var(--easy)_14%,transparent)]",
                wrong && "border-[var(--hard)] bg-[color-mix(in_srgb,var(--hard)_14%,transparent)]",
                done && !right && !wrong && "border-[var(--line)] opacity-60"
              )}
            >
              <span className="mt-px w-5 shrink-0 font-mono text-xs text-[var(--muted)]">{String.fromCharCode(65 + i)}.</span>
              <span className="lc-inline" dangerouslySetInnerHTML={{ __html: mdi(o) }} />
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function Order({ q, done, onAnswer }) {
  const items = useMemo(() => shuffled(q.items, q.id.length * 7919 + q.items.length * 31), [q]);
  const [seq, setSeq] = useState([]);
  const used = new Set(seq);
  const submit = (list) => onAnswer(list.every((k, p) => items[k][1] === p));

  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1 text-xs text-[var(--muted)]">Thứ tự của bạn (bấm vào mục để bỏ):</div>
        <ol className="min-h-10 space-y-1.5 rounded-md border border-dashed border-[var(--line)] p-2">
          {seq.length === 0 && <li className="px-1 text-xs text-[var(--faint)]">Bấm các mục bên dưới theo đúng thứ tự…</li>}
          {seq.map((k, p) => {
            const ok = done && items[k][1] === p;
            return (
              <li key={k}>
                <button
                  disabled={done}
                  onClick={() => setSeq((s) => s.filter((x) => x !== k))}
                  className={cn("flex w-full items-center gap-2 rounded px-2 py-1 text-left font-mono text-[13px]", !done && "bg-[var(--chip)] hover:bg-[var(--raised)]", done && (ok ? "bg-[color-mix(in_srgb,var(--easy)_16%,transparent)]" : "bg-[color-mix(in_srgb,var(--hard)_16%,transparent)]"))}
                >
                  <span className="w-5 text-xs text-[var(--muted)]">{p + 1}.</span>{items[k][0]}
                </button>
              </li>
            );
          })}
        </ol>
      </div>
      {!done && (
        <>
          <div className="flex flex-wrap gap-1.5">
            {items.map(([text], k) => (
              <button key={k} disabled={used.has(k)} onClick={() => setSeq((s) => [...s, k])}
                className="rounded-md border border-[var(--line)] px-2.5 py-1 font-mono text-[13px] hover:bg-[var(--raised)] disabled:opacity-30">{text}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <button disabled={seq.length !== items.length} onClick={() => submit(seq)} className="rounded-md bg-[var(--brand)] px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40">Kiểm tra</button>
            <button disabled={!seq.length} onClick={() => setSeq([])} className="rounded-md bg-[var(--chip)] px-3 py-1.5 text-sm text-[var(--title)] disabled:opacity-40">Xếp lại</button>
          </div>
        </>
      )}
      {done && (
        <div className="text-sm">
          <div className="mb-1 text-xs text-[var(--muted)]">Thứ tự đúng:</div>
          <ol className="list-decimal space-y-0.5 pl-6 font-mono text-[13px]">{q.items.map((t, i) => <li key={i}>{t}</li>)}</ol>
        </div>
      )}
    </div>
  );
}

function Fill({ q, done, onAnswer }) {
  // Đoạn code chứa {{1}}, {{2}}... là chỗ trống; mỗi chỗ có danh sách đáp án chấp nhận.
  const parts = q.code.split(/(\{\{\d+\}\})/);
  const [vals, setVals] = useState({});
  const [marks, setMarks] = useState({});
  const submit = () => {
    const m = {};
    q.blanks.forEach((acc, i) => { m[i + 1] = acc.some((a) => norm(a) === norm(vals[i + 1] || "")); });
    setMarks(m);
    onAnswer(Object.values(m).every(Boolean));
  };
  const ready = q.blanks.every((_, i) => norm(vals[i + 1] || ""));

  return (
    <div className="space-y-3">
      <pre className="overflow-x-auto rounded-md border border-[var(--line)] bg-[var(--bg)] p-3 font-mono text-[13px] leading-6">
        {parts.map((p, i) => {
          const m = /^\{\{(\d+)\}\}$/.exec(p);
          if (!m) return <span key={i}>{p}</span>;
          const n = Number(m[1]);
          return (
            <span key={i} className="inline-block align-baseline">
              <input
                value={vals[n] || ""}
                disabled={done}
                onChange={(e) => setVals((v) => ({ ...v, [n]: e.target.value }))}
                onKeyDown={(e) => { if (e.key === "Enter" && ready && !done) submit(); }}
                size={Math.max(6, (vals[n] || "").length + 1)}
                aria-label={`Chỗ trống ${n}`}
                placeholder={`(${n})`}
                className={cn("rounded border bg-[var(--panel)] px-1.5 py-0 font-mono text-[13px] outline-none focus:border-[var(--brand)]",
                  done ? (marks[n] ? "border-[var(--easy)]" : "border-[var(--hard)]") : "border-[var(--line)]")}
              />
            </span>
          );
        })}
      </pre>
      {!done ? (
        <button disabled={!ready} onClick={submit} className="rounded-md bg-[var(--brand)] px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40">Kiểm tra</button>
      ) : (
        <ul className="space-y-0.5 text-sm">
          {q.blanks.map((acc, i) => (
            <li key={i} className="flex items-center gap-1.5">
              {marks[i + 1] ? <Check className="size-3.5 text-[var(--easy)]" /> : <X className="size-3.5 text-[var(--hard)]" />}
              <span className="text-[var(--muted)]">({i + 1})</span> <code>{acc[0]}</code>
              {acc.length > 1 && <span className="text-xs text-[var(--muted)]">cũng chấp nhận: {acc.slice(1).join(", ")}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const KIND = { mcq: Mcq, order: Order, fill: Fill };

export function QuizRunner({ questions }) {
  const [i, setI] = useState(0);
  const [results, setResults] = useState({});   // qid -> true/false
  const q = questions[i];
  const done = q && results[q.id] !== undefined;
  const total = questions.length;
  const score = Object.values(results).filter(Boolean).length;
  const finished = i >= total;

  const answer = (ok) => {
    setResults((r) => ({ ...r, [q.id]: ok }));
    fetch("/api/learn/quiz", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ qid: q.id, ok }) }).catch(() => {});
  };

  if (finished) {
    return (
      <div className="mt-6 rounded-lg border border-[var(--line)] bg-[var(--panel)] p-6 text-center">
        <div className="text-sm text-[var(--muted)]">Kết quả</div>
        <div className="mt-1 text-4xl font-medium text-[var(--title)]">{score}/{total}</div>
        <div className="mt-4 flex justify-center gap-2">
          <Link href="/learn/quiz" className="rounded-md bg-[var(--chip)] px-4 py-2 text-sm text-[var(--title)]">Chọn bộ khác</Link>
          <Link href="/learn/progress" className="rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white">Xem điểm yếu</Link>
        </div>
      </div>
    );
  }

  const Kind = KIND[q.type] || Mcq;
  return (
    <div className="mt-3">
      <div className="mb-4 flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--chip)]"><div className="h-full bg-[var(--brand)]" style={{ width: `${(100 * i) / total}%` }} /></div>
        <span className="text-xs text-[var(--muted)]">Câu {i + 1}/{total}</span>
      </div>
      <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4 sm:p-5">
        <div className="mb-1 text-xs text-[var(--muted)]">
          {{ mcq: "Trắc nghiệm", order: "Sắp xếp", fill: "Điền chỗ trống" }[q.type]}
        </div>
        <div className="lc-prose mb-4" dangerouslySetInnerHTML={{ __html: md(q.q) }} />
        <Kind key={q.id} q={q} done={done} onAnswer={answer} />
        {done && (
          <div className={cn("mt-4 rounded-md border p-3 text-sm", results[q.id] ? "border-[var(--easy)]" : "border-[var(--hard)]")}>
            <div className={cn("mb-1 font-medium", results[q.id] ? "text-[var(--easy)]" : "text-[var(--hard)]")}>{results[q.id] ? "Chính xác" : "Chưa đúng"}</div>
            <div className="lc-prose" dangerouslySetInnerHTML={{ __html: md(q.why || "") }} />
          </div>
        )}
      </div>
      {done && (
        <div className="mt-4 flex justify-end">
          <button onClick={() => setI((n) => n + 1)} className="rounded-md bg-[var(--brand)] px-5 py-2 text-sm font-medium text-white">
            {i + 1 === total ? "Xem kết quả" : "Câu tiếp theo"}
          </button>
        </div>
      )}
    </div>
  );
}
