"use client";
// Tab "Ghi chú" (nút Note của LeetCode): soạn Markdown, thanh công cụ chèn định dạng, nút mắt để xem trước.
// Lưu tự động theo từng bài trong localStorage.
import { useRef, useState } from "react";
import { marked } from "marked";
import { Bold, Braces, Eye, Heading, Image as ImageIcon, Italic, Link2, List, ListOrdered, Pencil, Quote } from "lucide-react";
import { cn } from "@/lib/utils";

const TOOLS = [
  [Heading, "Tiêu đề", "### ", ""],
  [Bold, "Đậm", "**", "**"],
  [Italic, "Nghiêng", "_", "_"],
  [ListOrdered, "Danh sách số", "1. ", ""],
  [List, "Danh sách", "- ", ""],
  [Quote, "Trích dẫn", "> ", ""],
  [Braces, "Code", "`", "`"],
  [Link2, "Liên kết", "[", "](https://)"],
  [ImageIcon, "Ảnh", "![", "](https://)"],
];

export function NoteEditor({ value, onChange }) {
  const [preview, setPreview] = useState(false);
  const ta = useRef(null);
  const wrap = (pre, post) => {
    const el = ta.current;
    if (!el) return;
    const { selectionStart: a, selectionEnd: b } = el;
    const next = value.slice(0, a) + pre + value.slice(a, b) + post + value.slice(b);
    onChange(next);
    requestAnimationFrame(() => { el.focus(); el.setSelectionRange(a + pre.length, b + pre.length); });
  };
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-10 shrink-0 items-center gap-0.5 border-b border-[var(--line)] px-3">
        {TOOLS.map(([Icon, label, pre, post]) => (
          <button key={label} title={label} aria-label={label} disabled={preview} onClick={() => wrap(pre, post)}
            className="inline-flex size-7 items-center justify-center rounded text-[var(--muted)] hover:bg-[var(--raised)] hover:text-[var(--title)] disabled:opacity-40">
            <Icon className="size-4" />
          </button>
        ))}
        <span className="mx-1.5 h-4 w-px bg-[var(--line)]" />
        <button title={preview ? "Soạn" : "Xem trước"} aria-label={preview ? "Soạn" : "Xem trước"} onClick={() => setPreview((v) => !v)}
          className={cn("inline-flex size-7 items-center justify-center rounded hover:bg-[var(--raised)]", preview ? "text-[var(--accent)]" : "text-[var(--muted)] hover:text-[var(--title)]")}>
          {preview ? <Pencil className="size-4" /> : <Eye className="size-4" />}
        </button>
      </div>
      {preview
        ? <div className="lc-prose min-h-0 flex-1 overflow-y-auto px-4 py-3" dangerouslySetInnerHTML={{ __html: value.trim() ? marked.parse(value, { async: false }) : "<p style='color:var(--muted)'>Chưa có ghi chú.</p>" }} />
        : <textarea ref={ta} value={value} onChange={(e) => onChange(e.target.value)} placeholder="Gõ ghi chú ở đây… (hỗ trợ Markdown)"
            className="min-h-0 flex-1 resize-none border-0 bg-transparent px-4 py-3 text-sm leading-6 text-[var(--text)] outline-none placeholder:text-[var(--faint)]" />}
    </div>
  );
}
