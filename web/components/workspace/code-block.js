"use client";
// Khối code chỉ đọc kiểu LeetCode: tô màu cú pháp C, đánh số dòng, thu gọn còn vài dòng + "View more",
// nút sao chép và nút nạp vào editor. Không dùng thư viện ngoài (bộ tách từ nhỏ viết tay bên dưới).
import { useMemo, useState } from "react";
import { Check, ChevronDown, ChevronUp, Copy, Repeat2 } from "lucide-react";
import { cn } from "@/lib/utils";

const KEYWORDS = new Set(("auto break case const continue default do else enum extern for goto if inline register restrict return " +
  "sizeof static struct switch typedef union volatile while NULL true false").split(" "));
const TYPES = new Set(("void char short int long float double signed unsigned bool size_t ssize_t off_t pid_t time_t FILE " +
  "socklen_t sa_family_t in_addr_t in_port_t fd_set nfds_t pthread_t pthread_mutex_t sockaddr sockaddr_in sockaddr_storage " +
  "in_addr addrinfo pollfd timeval timespec stat dirent").split(" "));

const RULES = [
  ["com", /\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$)/y],
  ["pp", /^[ \t]*#[ \t]*[a-z]+(?:[ \t]*<[^>\n]*>)?/my],
  ["str", /"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?/y],
  ["num", /0[xX][0-9a-fA-F]+[uUlL]*|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[fFuUlL]*/y],
  ["id", /[A-Za-z_]\w*/y],
  ["op", /[+\-*/%=<>!&|^~?:]+/y],
];

function tokenize(code) {
  const out = [];
  let i = 0;
  while (i < code.length) {
    let hit = null;
    for (const [kind, re] of RULES) {
      re.lastIndex = i;
      const m = re.exec(code);
      if (m && m.index === i && m[0]) { hit = [kind, m[0]]; break; }
    }
    if (!hit) { out.push(["", code[i]]); i += 1; continue; }
    let [kind, text] = hit;
    if (kind === "id") {
      const after = code.slice(i + text.length).match(/^\s*(\()/);
      if (KEYWORDS.has(text)) kind = "kw";
      else if (TYPES.has(text) || /_t$/.test(text)) kind = "ty";
      else if (after) kind = "fn";
      else kind = "";
    }
    out.push([kind, text]);
    i += text.length;
  }
  return out;
}

// Tách luồng token thành các dòng (token nhiều dòng như /* ... */ được cắt theo '\n').
function toLines(code) {
  const lines = [[]];
  for (const [kind, text] of tokenize(code.replace(/\r\n?/g, "\n").replace(/\t/g, "    "))) {
    text.split("\n").forEach((part, k) => {
      if (k > 0) lines.push([]);
      if (part) lines[lines.length - 1].push([kind, part]);
    });
  }
  if (lines.length > 1 && lines[lines.length - 1].length === 0) lines.pop();
  return lines;
}

export function CodeBlock({ code, onLoad, preview = 8, className }) {
  const lines = useMemo(() => toLines(code || ""), [code]);
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const long = lines.length > preview + 2;
  const shown = long && !open ? lines.slice(0, preview) : lines;
  const copy = async () => {
    try { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* không có quyền clipboard */ }
  };
  return (
    <div className={cn("group relative rounded-xl bg-[var(--fill-3)]", className)}>
      <div className="absolute right-2 top-2 z-10 flex gap-1.5 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <button onClick={copy} title="Sao chép code" aria-label="Sao chép code"
          className="flex size-8 items-center justify-center rounded-lg border border-[var(--line)] bg-[var(--panel)] text-[var(--icon)] hover:text-[var(--title)]">
          {copied ? <Check className="size-4 text-[var(--green)]" /> : <Copy className="size-4" />}
        </button>
        {onLoad && (
          <button onClick={onLoad} title="Nạp code này vào editor" aria-label="Nạp code vào editor"
            className="flex size-8 items-center justify-center rounded-lg border border-[var(--line)] bg-[var(--panel)] text-[var(--icon)] hover:text-[var(--title)]">
            <Repeat2 className="size-4" />
          </button>
        )}
      </div>
      <pre className="m-0 overflow-x-auto py-3 font-mono text-[13px] leading-[1.7]">
        <code className="block min-w-max">
          {shown.map((ln, k) => (
            <div key={k} className="flex">
              <span className="w-12 shrink-0 select-none pr-4 text-right text-[var(--faint)]">{k + 1}</span>
              <span className="whitespace-pre pr-4">
                {ln.length ? ln.map(([kind, text], j) => <span key={j} className={kind ? `tok-${kind}` : undefined}>{text}</span>) : " "}
              </span>
            </div>
          ))}
        </code>
      </pre>
      {long && (
        <button onClick={() => setOpen(!open)}
          className="relative flex w-full items-center justify-center gap-1.5 rounded-b-xl pb-3 pt-1 text-sm text-[var(--text2)] hover:text-[var(--title)]">
          {open ? <><ChevronUp className="size-4" />View less</> : <><ChevronDown className="size-4" />View more <span className="text-xs text-[var(--faint)]">({lines.length - preview} dòng nữa)</span></>}
        </button>
      )}
    </div>
  );
}
