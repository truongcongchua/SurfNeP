"use client";
// Chọn dòng nghi ngờ trong lời giải sai, bấm Kiểm tra: server chấm và trả về dòng gây lỗi + giải thích.
import Link from "next/link";
import { useState } from "react";
import { marked } from "marked";
import { Check, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function BugRunner({ bugId, code, next }) {
  const lines = code.split("\n");
  const [sel, setSel] = useState([]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const toggle = (n) => {
    if (res) return;
    setSel((s) => (s.includes(n) ? s.filter((x) => x !== n) : [...s, n]));
  };

  const check = async () => {
    setBusy(true);
    setErr("");
    try {
      const r = await fetch("/api/learn/bug", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ id: bugId, lines: sel }) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "Lỗi");
      setRes(j);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => { setSel([]); setRes(null); };
  const truth = new Set(res?.lines || []);

  return (
    <div className="mt-4">
      <div className="mb-2 flex flex-wrap items-center gap-3 text-sm">
        <span className="text-[var(--muted)]">Bấm vào số dòng hoặc nội dung dòng để chọn (tối đa 5 dòng).</span>
        <span className="ml-auto text-xs text-[var(--muted)]">Đã chọn {sel.length}</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-[var(--line)] bg-[var(--panel)] py-2 font-mono text-[13px] leading-5">
        {lines.map((text, i) => {
          const n = i + 1;
          const picked = sel.includes(n);
          const right = res && truth.has(n);
          const wrong = res && picked && !truth.has(n);
          return (
            <div
              key={n}
              onClick={() => toggle(n)}
              role="button"
              aria-pressed={picked}
              className={cn(
                "flex min-w-max cursor-pointer select-none",
                !res && "hover:bg-[var(--raised)]",
                res && "cursor-default",
                picked && !res && "bg-[color-mix(in_srgb,var(--brand)_18%,transparent)]",
                right && "bg-[color-mix(in_srgb,var(--easy)_22%,transparent)]",
                wrong && "bg-[color-mix(in_srgb,var(--hard)_22%,transparent)]"
              )}
            >
              <span className="w-12 shrink-0 pr-3 text-right text-[var(--faint)]">{n}</span>
              <span className="w-5 shrink-0 text-center">
                {right ? <Check className="inline size-3.5 text-[var(--easy)]" /> : wrong ? <X className="inline size-3.5 text-[var(--hard)]" /> : picked ? <span className="text-[var(--brand)]">●</span> : null}
              </span>
              <span className="whitespace-pre pr-4 text-[var(--text)]">{text || " "}</span>
            </div>
          );
        })}
      </div>

      {err && <p className="mt-3 text-sm text-[var(--hard)]">{err}</p>}

      {!res ? (
        <div className="mt-4 flex gap-2">
          <button
            onClick={check}
            disabled={busy || sel.length === 0 || sel.length > 5}
            className="flex items-center gap-1.5 rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {busy && <Loader2 className="size-4 animate-spin" />} Kiểm tra
          </button>
          <button onClick={() => setSel([])} disabled={!sel.length} className="rounded-md bg-[var(--chip)] px-3 py-2 text-sm text-[var(--title)] disabled:opacity-40">Bỏ chọn</button>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <div className={cn("rounded-lg border p-4", res.ok ? "border-[var(--easy)]" : "border-[var(--hard)]")}>
            <div className={cn("text-sm font-medium", res.ok ? "text-[var(--easy)]" : "text-[var(--hard)]")}>
              {res.ok ? "Đúng, bạn đã tìm ra bug" : res.hit > 0 ? "Chưa gọn: bạn chọn dòng thừa" : "Chưa đúng"}
            </div>
            <h2 className="mt-1.5 text-base font-medium text-[var(--title)]">{res.title}</h2>
            <div className="lc-prose mt-2" dangerouslySetInnerHTML={{ __html: marked.parse(res.explain, { async: false }) }} />
            {res.fix && (
              <div className="mt-3 text-sm">
                <span className="text-[var(--muted)]">Cách sửa: </span>
                <span dangerouslySetInnerHTML={{ __html: marked.parseInline(res.fix, { async: false }) }} />
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={reset} className="rounded-md bg-[var(--chip)] px-3 py-2 text-sm text-[var(--title)] hover:bg-[var(--raised)]">Thử lại</button>
            {next && <Link href={`/learn/bugs/${next}`} className="rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-medium text-white">Bug tiếp theo</Link>}
          </div>
        </div>
      )}
    </div>
  );
}
