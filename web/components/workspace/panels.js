"use client";
// Nội dung các khung của trang làm bài: Đề bài, Lịch sử nộp, chi tiết bài nộp, Testcase, Test Result.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft, BookOpen, Check, ChevronDown, CircleDashed, CircleHelp, Clock, Code2, Lightbulb, Link2, ListTree, Loader2, Plus,
  SquareArrowOutUpRight, SquareCheckBig, SquarePen, SquareX, Star, Tag, ThumbsDown, ThumbsUp, Timer, X,
} from "lucide-react";
import { marked } from "marked";
import { VERDICT_HELP } from "@/lib/verdicts";
import { cn } from "@/lib/utils";

export const LABEL = {
  AC: "Accepted", WA: "Wrong Answer", CE: "Compile Error", RE: "Runtime Error", TLE: "Time Limit Exceeded", OLE: "Output Limit Exceeded",
  NL: "Not Listening", BLOCKED: "Blocked", LIMIT: "Client Limit", CV: "Constraint Violation", IE: "Internal Error",
};
export const vColor = (v) => (v === "AC" ? "text-[var(--green)]" : v === "CE" || v === "CV" ? "text-[var(--medium)]" : "text-[var(--hard)]");
const DIFF_COLOR = { easy: "text-[var(--easy)]", medium: "text-[var(--medium)]", hard: "text-[var(--hard)]" };
const fmt = (t) => new Date(t * 1000).toLocaleString("vi-VN");
function ago(t) {
  const s = Math.floor(Date.now() / 1000) - t;
  if (s < 60) return "vừa xong";
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  if (s < 86400) return `${Math.floor(s / 3600)} giờ trước`;
  return `${Math.floor(s / 86400)} ngày trước`;
}
export const maxTime = (r) => Math.max(0, ...(r?.tests || []).map((t) => t.time_ms || 0));

export function Pill({ className, children, ...props }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full bg-[var(--pill)] px-2.5 py-1 text-xs leading-4 text-[var(--text)]", className)} {...props}>{children}</span>;
}

export function Box({ label, children, tone }) {
  return (
    <div className="mb-3">
      {label && <div className="mb-1.5 text-xs text-[var(--text2)]">{label}</div>}
      <pre className={cn("m-0 overflow-x-auto whitespace-pre-wrap rounded-lg px-3 py-2.5 font-mono text-sm leading-5",
        tone === "bad" ? "bg-[var(--bad-bg)] text-[var(--hard)]" : "bg-[var(--fill-3)] text-[var(--text)]")}>{children}</pre>
    </div>
  );
}

/* ---------- Đề bài ---------- */

// Accordion cuối đề (Topics / Hint / Similar Questions của LeetCode).
function Acc({ id, icon: Icon, title, open, onToggle, children, className }) {
  return (
    <div id={id} className="border-t border-[var(--line)]">
      <button onClick={onToggle} className={cn("flex h-11 w-full items-center gap-2 text-sm text-[var(--title)] hover:text-[var(--accent)]", className)}>
        <Icon className="size-4" /><span className="flex-1 text-left">{title}</span>
        <ChevronDown className={cn("size-4 text-[var(--muted)] transition-transform", open && "rotate-180")} />
      </button>
      {open && <div className="pb-4 pl-6 text-sm">{children}</div>}
    </div>
  );
}

export function Description({ problem, html, solved, stats, similar }) {
  const [open, setOpen] = useState({});
  const root = useRef(null);
  const toggle = (k) => setOpen((o) => ({ ...o, [k]: !o[k] }));
  // Bấm pill ở đầu đề: mở accordion tương ứng rồi cuộn tới (như LeetCode).
  const jump = (k) => {
    setOpen((o) => ({ ...o, [k]: true }));
    requestAnimationFrame(() => root.current?.querySelector(`#acc-${k}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  };
  const hasHint = !!problem.ref || problem.prerequisites.length > 0;
  const rate = stats.total ? ((100 * stats.ac) / stats.total).toFixed(1) : null;

  return (
    <div ref={root} className="px-4 pb-4 pt-5">
      <div className="flex items-start justify-between gap-4">
        <h1 className="mb-3 text-2xl font-medium leading-8 text-[var(--title)]">{problem.number}. {problem.title}</h1>
        {solved && <span className="mt-1.5 flex shrink-0 items-center gap-1 text-sm text-[var(--muted)]">Đã giải <Check className="size-4 text-[var(--green)]" /></span>}
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        <Pill className={cn("font-medium", DIFF_COLOR[problem.difficulty])}>{problem.diffLabel}</Pill>
        {problem.topics.length > 0 && <button onClick={() => jump("topics")}><Pill className="hover:bg-[var(--chip)]"><Tag className="size-3.5" />Chủ đề</Pill></button>}
        <Pill><BookOpen className="size-3.5" />Chương {problem.chapter}</Pill>
        {hasHint && <button onClick={() => jump("hint")}><Pill className="hover:bg-[var(--chip)]"><Lightbulb className="size-3.5" />Tham chiếu</Pill></button>}
        {problem.exam && <Pill className="bg-[var(--brand-soft)] text-[var(--brand)]"><Timer className="size-3.5" />Thi thử</Pill>}
      </div>
      <div className="lc-prose" dangerouslySetInnerHTML={{ __html: html }} />

      <div className="mt-8 flex flex-wrap gap-x-6 gap-y-1 border-t border-[var(--line)] py-4 text-sm">
        <span className="text-[var(--muted)]">Lượt AC <b className="ml-1 text-base font-medium text-[var(--title)]">{stats.ac}</b></span>
        <span className="text-[var(--muted)]">Lượt nộp <b className="ml-1 text-base font-medium text-[var(--title)]">{stats.total}</b></span>
        <span className="text-[var(--muted)]">Tỉ lệ AC <b className="ml-1 text-base font-medium text-[var(--title)]">{rate == null ? "—" : `${rate}%`}</b></span>
      </div>
      {problem.topics.length > 0 && (
        <Acc id="acc-topics" icon={Tag} title="Chủ đề" open={open.topics} onToggle={() => toggle("topics")}>
          <div className="flex flex-wrap gap-2">{problem.topics.map((t) => <Pill key={t}>{t}</Pill>)}</div>
        </Acc>
      )}
      {hasHint && (
        <Acc id="acc-hint" icon={Lightbulb} title="Tham chiếu & bài cần làm trước" open={open.hint} onToggle={() => toggle("hint")}>
          <div className="space-y-2 text-[var(--text)]">
            {problem.ref && <p className="m-0">Đọc lại: {problem.ref}</p>}
            {problem.prerequisites.length > 0 && (
              <p className="m-0">Nên làm trước: {problem.prerequisites.map((x, i) => <span key={x}>{i > 0 && ", "}<Link href={`/problems/${x}`}>{x}</Link></span>)}</p>
            )}
          </div>
        </Acc>
      )}
      {similar.length > 0 && (
        <Acc id="acc-similar" icon={ListTree} title="Bài tương tự" open={open.similar} onToggle={() => toggle("similar")}>
          <ul className="m-0 list-none space-y-2 p-0">
            {similar.map((s) => (
              <li key={s.id} className="flex items-center gap-2">
                {s.status === "solved" ? <Check className="size-4 text-[var(--green)]" /> : s.status === "attempted" ? <CircleDashed className="size-4 text-[var(--medium)]" /> : <span className="size-4" />}
                <Link href={`/problems/${s.id}`} className="flex-1 text-[var(--text)] hover:text-[var(--accent)]">{s.title}</Link>
                <span className={cn("text-xs", DIFF_COLOR[s.difficulty])}>{s.difficulty === "easy" ? "Dễ" : s.difficulty === "medium" ? "Trung bình" : "Khó"}</span>
              </li>
            ))}
          </ul>
        </Acc>
      )}
    </div>
  );
}

// Chân khung đề (như LeetCode): [👍 46K | 👎] · ★ (Danh sách của tôi) · ↗ chia sẻ · ? trợ giúp — bên phải: chấm xanh + thống kê.
export function DescFooter({ likes, mine, favorite, onLike, onFavorite, onShare, onHelp, right }) {
  const [menu, setMenu] = useState(false);
  const box = useRef(null);
  useEffect(() => {
    if (!menu) return;
    const h = (e) => { if (!box.current?.contains(e.target)) setMenu(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [menu]);
  const ic = "inline-flex h-7 items-center gap-1 rounded-md px-1.5 text-[var(--text2)] hover:text-[var(--title)] [&_svg]:size-3.5";
  return (
    <div className="relative flex h-12 shrink-0 items-center justify-between gap-2 px-3.5 text-xs text-[var(--text2)]">
      <div className="flex items-center gap-1">
        <div className="mr-1 flex h-7 items-center overflow-hidden rounded-lg bg-[var(--fill-2)]">
          <button title="Thích" aria-label="Thích" aria-pressed={mine === 1} onClick={() => onLike(mine === 1 ? 0 : 1)}
            className={cn("flex h-7 items-center gap-1.5 px-2 text-sm font-medium hover:bg-[var(--fill-4)]", mine === 1 ? "text-[var(--submit)]" : "text-[var(--text2)]")}>
            <ThumbsUp className={cn("size-3.5", mine === 1 && "fill-current")} />{likes}
          </button>
          <span className="h-3.5 w-px bg-[var(--line-strong)]" />
          <button title="Không thích" aria-label="Không thích" aria-pressed={mine === -1} onClick={() => onLike(mine === -1 ? 0 : -1)}
            className={cn("flex h-7 items-center px-2 hover:bg-[var(--fill-4)]", mine === -1 ? "text-[var(--title)]" : "text-[var(--text2)]")}>
            <ThumbsDown className={cn("size-3.5", mine === -1 && "fill-current")} />
          </button>
        </div>
        <span className="mx-1 h-3.5 w-px bg-[var(--line-strong)]" />
        <div ref={box} className="relative">
          <button title="Danh sách của tôi" aria-label="Danh sách của tôi" aria-pressed={favorite} onClick={() => setMenu((v) => !v)}
            className={cn(ic, "hover:bg-[var(--fill-3)]", favorite && "text-[var(--title)]")}><Star className={cn(favorite && "fill-current")} /></button>
          {menu && (
            <div className="absolute bottom-9 left-0 z-50 w-60 rounded-lg bg-[var(--panel)] p-2 text-sm shadow-[var(--pop-shadow)]">
              <Link href="/?st=fav" className="mb-1 flex items-center justify-between rounded px-2 py-1.5 text-[var(--title)] hover:bg-[var(--raised)]">Danh sách của tôi <span aria-hidden>→</span></Link>
              <button onClick={() => onFavorite(!favorite)} className="flex h-9 w-full items-center gap-2 rounded px-2 text-left text-[var(--title)] hover:bg-[var(--raised)]">
                <span className={cn("grid size-4 place-items-center rounded-[3px] border", favorite ? "border-[var(--title)] bg-[var(--title)] text-[var(--panel)]" : "border-[var(--line-strong)]")}>{favorite && <Check className="size-3" strokeWidth={3} />}</span>
                Yêu thích
              </button>
            </div>
          )}
        </div>
        <button title="Chia sẻ (sao chép liên kết)" aria-label="Chia sẻ" onClick={onShare} className={cn(ic, "hover:bg-[var(--fill-3)]")}><SquareArrowOutUpRight /></button>
        <button title="Trợ giúp: phím tắt" aria-label="Trợ giúp" onClick={onHelp} className={cn(ic, "hover:bg-[var(--fill-3)]")}><CircleHelp /></button>
      </div>
      {right && <div className="flex items-center gap-1.5 truncate"><span className="size-1.5 shrink-0 rounded-full bg-[var(--submit)]" />{right}</div>}
    </div>
  );
}

/* ---------- Lịch sử nộp ---------- */

export function SubmissionList({ past, onOpen }) {
  if (past.length === 0) return <div className="p-6 text-center text-sm text-[var(--muted)]">Bạn chưa nộp bài này lần nào.</div>;
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-left text-xs text-[var(--muted)]">
          <th className="w-10 px-3 py-2.5 font-normal" />
          <th className="px-3 py-2.5 font-normal">Trạng thái</th>
          <th className="px-3 py-2.5 font-normal">Ngôn ngữ</th>
          <th className="px-3 py-2.5 font-normal">Test</th>
        </tr>
      </thead>
      <tbody>
        {past.map((s, i) => {
          const done = s.status === "done";
          return (
            <tr key={s.id} onClick={() => done && onOpen(s.id)}
              className={cn(done && "cursor-pointer hover:bg-[var(--raised)]", i % 2 === 1 && "bg-[var(--zebra)]")}>
              <td className="px-3 py-2.5 text-[var(--muted)]">{past.length - i}</td>
              <td className="px-3 py-2.5">
                <div className={cn("font-medium", done ? vColor(s.verdict) : "text-[var(--muted)]")}>
                  {done ? LABEL[s.verdict] || s.verdict : s.status === "running" ? "Đang chấm…" : "Chờ chấm…"}
                </div>
                <div className="text-xs text-[var(--muted)]" title={fmt(s.created)}>{ago(s.created)}</div>
              </td>
              <td className="px-3 py-2.5"><Pill>C</Pill></td>
              <td className="px-3 py-2.5 text-[var(--muted)]">{s.total ? `${s.passed}/${s.total}` : "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// Giải thích verdict không phải AC: nguyên nhân thường gặp + các lỗi hay mắc ở đúng bài này (link sang bài "Tìm bug").
function VerdictHelp({ verdict, bugs = [] }) {
  const text = VERDICT_HELP[verdict];
  if (!verdict || verdict === "AC" || !text) return null;
  // Lỗi cùng verdict với kết quả này xếp trước.
  const list = [...bugs].sort((a, b) => (b.verdict === verdict) - (a.verdict === verdict));
  return (
    <div className="mb-4 rounded-lg border border-[var(--line)] bg-[var(--fill-3)] p-3 text-sm">
      <div className="mb-1 flex items-center gap-1.5 font-medium text-[var(--title)]"><Lightbulb className="size-4 text-[var(--brand)]" />Vì sao có thể bị {LABEL[verdict] || verdict}?</div>
      <div className="lc-prose" dangerouslySetInnerHTML={{ __html: marked.parseInline(text, { async: false }) }} />
      {list.length > 0 && (
        <div className="mt-2">
          <div className="text-xs text-[var(--muted)]">Lỗi hay gặp ở bài này (bấm để tập tìm bug):</div>
          <ul className="mt-1 space-y-1">
            {list.map((b) => (
              <li key={b.id}>
                <a href={`/learn/bugs/${b.id}`} target="_blank" rel="noreferrer" className="text-[var(--accent)] hover:underline">{b.title}</a>
                {b.verdict === verdict && <span className="ml-1.5 text-xs text-[var(--muted)]">· khớp verdict</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function SubmissionDetail({ sub, user, onBack, onLoad, bugs }) {
  if (!sub) return <div className="flex items-center gap-2 p-5 text-sm text-[var(--muted)]"><Loader2 className="size-4 animate-spin" />Đang tải…</div>;
  const r = sub.result || {};
  const firstBad = (r.tests || []).find((t) => t.verdict !== "AC" && t.message);
  return (
    <div>
      <div className="flex h-9 items-center justify-between border-b border-[var(--line)] pl-3 pr-2">
        <button onClick={onBack} className="flex items-center gap-2 text-sm text-[var(--text2)] hover:text-[var(--title)]"><ArrowLeft className="size-4" /> Tất cả bài nộp</button>
        <button title="Sao chép liên kết bài nộp" aria-label="Sao chép liên kết" onClick={() => navigator.clipboard?.writeText(location.href)} className="inline-flex size-7 items-center justify-center rounded text-[var(--icon)] hover:bg-[var(--fill-3)]"><Link2 className="size-4" /></button>
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className={cn("text-xl font-medium", vColor(sub.verdict))}>{LABEL[sub.verdict] || sub.verdict}</span>
              {r.total ? <span className="text-xs text-[var(--text2)]">{r.passed} / {r.total} testcases passed</span> : null}
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs text-[var(--text2)]">
              <span className="avatar" style={{ width: 20, height: 20, fontSize: 10 }}>{user.name.slice(0, 1).toUpperCase()}</span>
              <b className="font-medium text-[var(--title)]">{user.name}</b> submitted at {fmt(sub.created)}
            </div>
          </div>
          <button onClick={onLoad} title="Nạp code này vào editor" aria-label="Sửa code"
            className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#2db55d] text-white hover:bg-[#28a352]"><SquarePen className="size-4" /></button>
        </div>

        <VerdictHelp verdict={sub.verdict} bugs={bugs} />

        {r.tests?.length > 0 && (
          <div className="mt-4 rounded-xl border border-[var(--line)] p-3">
            <div className="rounded-lg bg-[var(--fill-3)] p-3">
              <div className="flex items-center gap-1.5 text-sm text-[var(--title)]"><Clock className="size-4" />Runtime</div>
              <div className="mt-2 flex items-baseline gap-1 text-[var(--title)]"><span className="text-xl font-medium">{maxTime(r)}</span><span className="text-xs">ms</span></div>
            </div>
          </div>
        )}
        {sub.verdict === "CE" && <div className="mt-4"><Box tone="bad">{r.compile_log}</Box></div>}
        {r.message && <div className="mt-4"><Box>{r.message}</Box></div>}
        {firstBad && <div className="mt-4"><Box label={firstBad.name}>{firstBad.message}</Box></div>}
        <div className="mb-2 mt-5 flex items-center gap-2 text-sm text-[var(--text2)]"><Code2 className="size-4" />Code <span className="h-3.5 w-px bg-[var(--line-strong)]" /> C</div>
        <pre className="m-0 overflow-x-auto rounded-lg bg-[var(--fill-3)] p-3 font-mono text-sm leading-relaxed">{sub.code}</pre>
      </div>
    </div>
  );
}

/* ---------- Testcase ---------- */

const SEP = "\n---\n";
function AutoText({ value, onChange, label }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (el) { el.style.height = "auto"; el.style.height = `${el.scrollHeight + 2}px`; }
  }, [value]);
  return (
    <textarea ref={ref} value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} spellCheck={false} rows={1}
      className="block w-full resize-none rounded-lg border border-transparent bg-[var(--fill-3)] px-3 py-2.5 font-mono text-sm leading-5 text-[var(--text)] outline-none focus:border-[var(--line-strong)]" />
  );
}

// Testcase như LeetCode: Case 1..n sửa được; "+" nhân bản case đang chọn; ⓧ khi rê chuột để xoá;
// "Source" chuyển sang soạn tất cả case dạng văn bản (ngăn bằng dòng ---); "Đặt lại testcase" khi đã sửa.
export function Testcases({ editable, cases, setCases, defaults, sel, setSel, max = 10 }) {
  const [source, setSource] = useState(false);
  const [raw, setRaw] = useState("");
  if (!editable)
    return (
      <div className="p-5 text-sm text-[var(--muted)]">
        Bài này chấm bằng kịch bản đóng vai client/server nên không có input dạng văn bản.
        Xem phần ví dụ trong đề bài, rồi bấm <b className="text-[var(--title)]">Chạy thử</b> để chạy test mẫu hoặc <b className="text-[var(--title)]">Nộp bài</b> để chạy toàn bộ test.
      </div>
    );
  const changed = JSON.stringify(cases) !== JSON.stringify(defaults);
  const i = Math.min(sel, cases.length - 1);
  const toggleSource = () => {
    if (!source) setRaw(cases.join(SEP));
    else {
      const next = raw.split(/\n?^---$\n?/m).map((c) => c.replace(/\s+$/, "")).filter((c, k, a) => c || a.length === 1).slice(0, max);
      setCases(next.length ? next : [""]);
      setSel(0);
    }
    setSource(!source);
  };
  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {source ? (
          <textarea value={raw} onChange={(e) => setRaw(e.target.value)} spellCheck={false} aria-label="Tất cả testcase"
            className="h-full min-h-40 w-full resize-none rounded-lg bg-[var(--chip)] p-3 font-mono text-sm leading-5 text-[var(--text)] outline-none" />
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {cases.map((_, k) => (
                <div key={k} className="group relative">
                  <button onClick={() => setSel(k)}
                    className={cn("rounded-lg px-4 py-1 text-sm font-medium", k === i ? "bg-[var(--case-sel)] text-[var(--title)]" : "text-[color:var(--text2)] hover:bg-[var(--fill-3)]")}>
                    Case {k + 1}
                  </button>
                  {cases.length > 1 && (
                    <button aria-label={`Xoá Case ${k + 1}`} onClick={() => { setCases(cases.filter((_, j) => j !== k)); setSel(Math.max(0, k <= i ? i - 1 : i)); }}
                      className="absolute -right-1.5 -top-1.5 hidden size-4 items-center justify-center rounded-full bg-[var(--muted)] text-[var(--panel)] group-hover:flex">
                      <X className="size-3" strokeWidth={3} />
                    </button>
                  )}
                </div>
              ))}
              {cases.length < max && (
                <button aria-label="Thêm testcase" title="Thêm testcase (nhân bản case đang chọn)" onClick={() => { setCases([...cases, cases[i]]); setSel(cases.length); }}
                  className="inline-flex size-8 items-center justify-center rounded-lg text-[#bfbfbf] hover:bg-[var(--fill-3)] hover:text-[var(--title)]"><Plus className="size-3.5" /></button>
              )}
            </div>
            <div className="mb-1.5 text-xs text-[var(--muted)]">stdin =</div>
            <AutoText label={`Input của Case ${i + 1}`} value={cases[i]} onChange={(v) => setCases(cases.map((c, j) => (j === i ? v : c)))} />
          </>
        )}
      </div>
      <div className="flex h-9 shrink-0 items-center gap-3 px-3 text-xs text-[var(--muted)]">
        <button onClick={toggleSource} className={cn("inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-sm hover:bg-[var(--raised)] hover:text-[var(--title)]", source && "bg-[var(--chip)] text-[var(--title)]")}>
          <Code2 className="size-4" /> Source
        </button>
        {changed && !source && <button onClick={() => { setCases(defaults); setSel(0); }} className="hover:text-[var(--title)]">Đặt lại testcase</button>}
        <span className="flex-1" />
        {source && <span>Ngăn các testcase bằng một dòng chỉ có ---</span>}
        <span className="tabular-nums">{cases.length}/{max} testcase</span>
      </div>
    </div>
  );
}

/* ---------- Test Result ---------- */

export function TestResult({ r, error, busy, note, bugs }) {
  const tests = r?.tests || [];
  const firstBad = Math.max(0, tests.findIndex((t) => t.verdict !== "AC"));
  const [sel, setSel] = useState(firstBad);
  useEffect(() => setSel(firstBad), [r]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="p-5 text-sm text-[var(--hard)]">{error}</div>;
  if (busy && !r)
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-5 text-sm text-[var(--muted)]">
        <Loader2 className="size-5 animate-spin" /> {note || "Đang chạy… (biên dịch + chạy trong Docker, thường 5–30 giây)"}
      </div>
    );
  if (!r) return <div className="flex h-full items-center justify-center p-5 text-sm text-[var(--faint)]">Bạn cần chạy code trước</div>;

  const t = tests[sel];
  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-baseline gap-3">
        <span className={cn("text-xl font-medium", vColor(r.verdict))}>{LABEL[r.verdict] || r.verdict}</span>
        {tests.length > 0 && <span className="text-xs text-[var(--text2)]">Runtime: {maxTime(r)} ms</span>}
        {r.total && !r.sampleRun ? <span className="text-xs text-[var(--text2)]">{r.passed} / {r.total} testcases passed</span> : null}
        {r.debugRun && <span className="text-xs text-[var(--faint)]">Gỡ lỗi (-O0 -g, ASan + UBSan)</span>}
      </div>

      {r.verdict === "CE" && <Box tone="bad">{r.compile_log}</Box>}
      {r.message && <Box tone={r.verdict === "AC" ? undefined : "bad"}>{r.message}</Box>}
      <VerdictHelp verdict={r.verdict} bugs={bugs} />

      {tests.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {tests.map((x, k) => (
              <button key={k} onClick={() => setSel(k)}
                className={cn("flex items-center gap-2 rounded-lg px-3 py-1 text-sm font-medium", k === sel ? "bg-[var(--case-sel)] text-[var(--title)]" : "text-[color:var(--text2)] hover:bg-[var(--fill-3)]")}>
                {x.verdict === "AC" ? <SquareCheckBig className="size-3.5 text-[var(--green)]" /> : <SquareX className="size-3.5 text-[var(--hard)]" />}
                {x.name}
              </button>
            ))}
          </div>
          {t && (t.io ? (
            <>
              {t.verdict !== "AC" && t.verdict !== "WA" && <div className={cn("mb-3 text-sm font-medium", vColor(t.verdict))}>{LABEL[t.verdict] || t.verdict}{t.message ? ` — ${t.message}` : ""}</div>}
              {t.debug_log && <Box label={t.sanitizer ? "Báo cáo Sanitizer (stderr)" : "stderr"} tone={t.sanitizer ? "bad" : undefined}>{t.debug_log}</Box>}
              <Box label="Input">{t.io.input}</Box>
              <Box label="Output">{t.io.output || " "}</Box>
              <Box label="Expected">{t.io.expected || " "}</Box>
            </>
          ) : (
            <>
              <div className="mb-3 flex items-center gap-3 text-sm">
                <span className={cn("font-medium", vColor(t.verdict))}>{LABEL[t.verdict] || t.verdict}</span>
                <span className="text-[var(--muted)]">{t.time_ms} ms</span>
              </div>
              {t.debug_log && <Box label={t.sanitizer ? "Báo cáo Sanitizer (stderr)" : "Output / stderr của chương trình"} tone={t.sanitizer ? "bad" : undefined}>{t.debug_log}</Box>}
              {t.message
                ? <Box label="Chi tiết">{t.message}</Box>
                : <div className="text-sm text-[var(--muted)]">{t.verdict === "AC" ? "Test này đạt." : "Không có chi tiết (test ẩn)."}</div>}
            </>
          ))}
        </>
      )}

      {r.compile_log && r.verdict !== "CE" && r.compile_log.trim() && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-[var(--muted)]">Cảnh báo của trình biên dịch</summary>
          <div className="mt-2"><Box>{r.compile_log}</Box></div>
        </details>
      )}
    </div>
  );
}
