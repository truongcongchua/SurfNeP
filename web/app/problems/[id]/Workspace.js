"use client";
// Trang bài theo bố cục LeetCode: thanh trên riêng, khung trái (Đề bài / Lịch sử nộp / chi tiết bài nộp),
// khung Code ở phải trên, khung Testcase / Test Result ở phải dưới. Các khung kéo chỉnh và thu gọn được.
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import {
  ArrowLeft, Check, ChevronLeft, ChevronRight, ChevronsLeft, CloudUpload, Code2, FileText, History,
  List, Loader2, Lock, LogOut, Maximize2, Minimize2, PanelLeftOpen, Play, RotateCcw, Shuffle, SquareCheck,
  SquarePen, Tag, Terminal, Timer, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { logoutAction } from "@/app/actions";
import { cn } from "@/lib/utils";

const Monaco = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-muted-foreground">Đang tải trình soạn thảo…</div>,
});

const LABEL = {
  AC: "Accepted", WA: "Wrong Answer", CE: "Compile Error", RE: "Runtime Error", TLE: "Time Limit Exceeded",
  NL: "Not Listening", BLOCKED: "Blocked", LIMIT: "Client Limit", CV: "Constraint Violation", IE: "Internal Error",
};
const vColor = (v) => (v === "AC" ? "text-[var(--green)]" : v === "CE" || v === "CV" ? "text-[var(--medium)]" : "text-[var(--hard)]");
const DIFF_COLOR = { easy: "text-[var(--easy)]", medium: "text-[var(--medium)]", hard: "text-[var(--hard)]" };
const fmt = (t) => new Date(t * 1000).toLocaleString("vi-VN");
function ago(t) {
  const s = Math.floor(Date.now() / 1000) - t;
  if (s < 60) return "vừa xong";
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  if (s < 86400) return `${Math.floor(s / 3600)} giờ trước`;
  return `${Math.floor(s / 86400)} ngày trước`;
}
const maxTime = (r) => Math.max(0, ...(r?.tests || []).map((t) => t.time_ms || 0));

/* ---------- mảnh giao diện dùng chung ---------- */

function Handle({ vertical }) {
  return (
    <PanelResizeHandle className={cn("group flex items-center justify-center", vertical ? "h-2" : "w-2")}>
      <div className={cn(
        "rounded-full bg-transparent transition-colors group-hover:bg-[var(--accent)] group-data-[resize-handle-state=drag]:bg-[var(--accent)]",
        vertical ? "h-[3px] w-full" : "h-full w-[3px]"
      )} />
    </PanelResizeHandle>
  );
}

function TabBar({ children, right }) {
  return (
    <div className="flex h-9 shrink-0 items-center bg-[var(--panel-head)] px-1">
      <div className="flex min-w-0 flex-1 items-center overflow-x-auto">{children}</div>
      {right && <div className="flex items-center gap-0.5 pr-1">{right}</div>}
    </div>
  );
}

function Tab({ active, onClick, icon: Icon, iconClass, children, onClose }) {
  return (
    <div className="flex items-center">
      <button
        onClick={onClick}
        className={cn(
          "flex h-7 items-center gap-1.5 whitespace-nowrap rounded-[5px] px-2.5 text-sm transition-colors hover:bg-[var(--chip)]",
          active ? "font-medium text-foreground" : "text-[color:var(--tab-idle)]"
        )}
      >
        <Icon className={cn("size-3.5", iconClass)} />
        {children}
      </button>
      {onClose && (
        <button onClick={onClose} className="rounded p-0.5 text-muted-foreground hover:bg-[var(--chip)]" aria-label="Đóng tab">
          <X className="size-3.5" />
        </button>
      )}
    </div>
  );
}
const Sep = () => <span className="mx-0.5 h-4 w-px shrink-0 bg-[var(--line)]" />;

function IconBtn({ label, onClick, children, disabled }) {
  return (
    <button
      title={label} aria-label={label} onClick={onClick} disabled={disabled}
      className="inline-flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-[var(--chip)] hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
    >{children}</button>
  );
}

function Pill({ className, children, ...props }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full bg-[var(--pill)] px-2 py-1 text-xs leading-4", className)} {...props}>{children}</span>;
}

function Box({ label, children }) {
  return (
    <div className="mb-3">
      {label && <div className="mb-1.5 text-xs font-medium text-muted-foreground">{label}</div>}
      <pre className="m-0 overflow-x-auto whitespace-pre-wrap rounded-lg bg-[var(--chip)] px-3 py-2.5 font-mono text-sm leading-5">{children}</pre>
    </div>
  );
}

/* ---------- thanh trên ---------- */

function TopBar({ nav, problemId, busy, running, onRun, onSubmit, examMinutes, left, user }) {
  const router = useRouter();
  const mm = left == null ? null : `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
  const shuffle = () => {
    const others = nav.all.filter((x) => x !== problemId);
    if (others.length) router.push(`/problems/${others[Math.floor(Math.random() * others.length)]}`);
  };
  return (
    <div className="grid h-12 shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-2 px-3">
      <div className="flex min-w-0 items-center gap-1">
        <Link href="/" className="mr-1 flex items-center gap-1.5 font-semibold text-foreground hover:no-underline">
          <Code2 className="size-5 text-[var(--brand)]" />
          <span className="hidden sm:inline">NetJudge</span>
        </Link>
        <Sep />
        <Link href="/" className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm font-medium text-foreground hover:bg-[var(--chip)] hover:no-underline">
          <List className="size-4" /> <span className="hidden md:inline">Danh sách bài</span>
        </Link>
        <IconBtn label="Bài trước" disabled={!nav.prev} onClick={() => router.push(`/problems/${nav.prev}`)}><ChevronLeft className="size-4" /></IconBtn>
        <IconBtn label="Bài sau" disabled={!nav.next} onClick={() => router.push(`/problems/${nav.next}`)}><ChevronRight className="size-4" /></IconBtn>
        <IconBtn label="Bài ngẫu nhiên" onClick={shuffle}><Shuffle className="size-4" /></IconBtn>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={onRun} disabled={busy || running} title="Chạy thử với test mẫu" aria-label="Chạy thử"
          className="flex size-8 items-center justify-center rounded-md bg-[var(--chip)] transition-colors hover:brightness-95 disabled:opacity-60"
        >
          {running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-3.5 fill-current" />}
        </button>
        <button
          onClick={onSubmit} disabled={busy || running}
          className="flex h-8 items-center gap-1.5 rounded-md bg-[var(--chip)] px-3 text-sm font-medium text-[color:var(--submit)] transition-colors hover:brightness-95 disabled:opacity-60"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <CloudUpload className="size-4" />}
          {busy ? "Đang chấm…" : "Nộp bài"}
        </button>
        {examMinutes && (left == null
          ? <button onClick={() => window.__njStartExam()} className="flex items-center gap-1.5 rounded-md bg-[var(--chip)] px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"><Timer className="size-4" />{examMinutes}′</button>
          : <span className={cn("flex items-center gap-1.5 rounded-md bg-[var(--chip)] px-3 py-1.5 font-mono text-sm tabular-nums", left === 0 ? "text-[var(--hard)]" : "text-[var(--accent)]")}><Timer className="size-4" />{mm}</span>)}
      </div>

      <div className="flex items-center justify-end gap-2">
        <ThemeToggle />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex size-7 items-center justify-center rounded-full bg-[var(--brand)] text-xs font-semibold text-white" aria-label="Tài khoản">
              {user.name.slice(0, 1).toUpperCase()}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <div className="px-2 py-1.5 text-sm font-semibold">{user.name}</div>
            <DropdownMenuItem onSelect={() => logoutAction()}><LogOut /> Đăng xuất</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

/* ---------- khung trái ---------- */

function Description({ problem, html, solved }) {
  const [showTopics, setShowTopics] = useState(false);
  return (
    <div className="px-4 py-5">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-2xl font-semibold leading-7">{problem.number}. {problem.title}</h1>
        {solved && <span className="mt-1.5 flex shrink-0 items-center gap-1 text-sm text-muted-foreground">Đã giải <Check className="size-4 text-[var(--green)]" /></span>}
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-1">
        <Pill className={cn("font-medium", DIFF_COLOR[problem.difficulty])}>{problem.diffLabel}</Pill>
        <Pill>Chương {problem.chapter}</Pill>
        {problem.topics.length > 0 && (
          <button onClick={() => setShowTopics((v) => !v)}><Pill className="hover:brightness-95"><Tag className="size-3.5" />Chủ đề</Pill></button>
        )}
        {problem.exam && <Pill className="text-[var(--brand)]">Thi thử</Pill>}
      </div>
      {showTopics && (
        <div className="mb-5 flex flex-wrap gap-2">{problem.topics.map((t) => <Pill key={t}>{t}</Pill>)}</div>
      )}
      <div className="prose lc-prose" dangerouslySetInnerHTML={{ __html: html }} />
      {(problem.ref || problem.prerequisites.length > 0) && (
        <div className="mt-6 space-y-1 border-t border-[var(--line)] pt-4 text-sm text-muted-foreground">
          {problem.ref && <p className="m-0">Tham chiếu: {problem.ref}</p>}
          {problem.prerequisites.length > 0 && (
            <p className="m-0">Bài nền: {problem.prerequisites.map((x, i) => <span key={x}>{i > 0 && ", "}<Link href={`/problems/${x}`}>{x}</Link></span>)}</p>
          )}
        </div>
      )}
    </div>
  );
}

function SubmissionList({ past, onOpen }) {
  if (past.length === 0) return <div className="p-6 text-center text-sm text-muted-foreground">Bạn chưa nộp bài này lần nào.</div>;
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-left text-xs text-muted-foreground">
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
              className={cn("border-t border-[var(--line)]", done && "cursor-pointer hover:bg-[var(--chip)]", i % 2 === 1 && "bg-[var(--zebra)]")}>
              <td className="px-3 py-2.5 text-muted-foreground">{past.length - i}</td>
              <td className="px-3 py-2.5">
                <div className={cn("font-medium", done ? vColor(s.verdict) : "text-muted-foreground")}>
                  {done ? LABEL[s.verdict] || s.verdict : s.status === "running" ? "Đang chấm…" : "Chờ chấm…"}
                </div>
                <div className="text-xs text-muted-foreground" title={fmt(s.created)}>{ago(s.created)}</div>
              </td>
              <td className="px-3 py-2.5"><Pill>C</Pill></td>
              <td className="px-3 py-2.5 text-muted-foreground">{s.total ? `${s.passed}/${s.total}` : "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function SubmissionDetail({ sub, user, onBack, onLoad }) {
  if (!sub) return <div className="flex items-center gap-2 p-5 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Đang tải…</div>;
  const r = sub.result || {};
  const firstBad = (r.tests || []).find((t) => t.verdict !== "AC" && t.message);
  return (
    <div>
      <button onClick={onBack} className="flex w-full items-center gap-2 border-b border-[var(--line)] px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Tất cả bài nộp
      </button>
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-baseline gap-3">
              <span className={cn("text-xl font-semibold", vColor(sub.verdict))}>{LABEL[sub.verdict] || sub.verdict}</span>
              {r.total ? <span className="text-sm text-muted-foreground">{r.passed} / {r.total} test đạt</span> : null}
            </div>
            <div className="mt-1 text-xs text-muted-foreground"><b className="text-foreground">{user.name}</b> nộp lúc {fmt(sub.created)}</div>
          </div>
          <button onClick={onLoad} title="Nạp code này vào editor"
            className="flex items-center gap-1.5 rounded-md bg-[var(--green)] px-3 py-1.5 text-sm font-medium text-white hover:brightness-95">
            <SquarePen className="size-4" /> Sửa code
          </button>
        </div>

        {r.tests?.length > 0 && (
          <div className="mt-4 rounded-lg bg-[var(--chip)] p-4">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground"><Timer className="size-4" />Thời gian chạy (test lâu nhất)</div>
            <div className="mt-1 text-2xl font-semibold">{maxTime(r)} <span className="text-sm font-normal text-muted-foreground">ms</span></div>
          </div>
        )}

        {sub.verdict === "CE" && <div className="mt-4"><Box label="Lỗi biên dịch">{r.compile_log}</Box></div>}
        {r.message && <div className="mt-4"><Box label="Thông báo">{r.message}</Box></div>}
        {firstBad && <div className="mt-4"><Box label={`Test sai đầu tiên: ${firstBad.name}`}>{firstBad.message}</Box></div>}

        <div className="mt-5 mb-2 flex items-center gap-2 text-sm text-muted-foreground">Code <Sep /> C</div>
        <pre className="m-0 overflow-x-auto rounded-lg bg-[var(--chip)] p-3 font-mono text-sm leading-relaxed">{sub.code}</pre>
      </div>
    </div>
  );
}

/* ---------- khung dưới ---------- */

function Testcases({ samples }) {
  const [i, setI] = useState(0);
  if (samples.length === 0)
    return (
      <div className="p-5 text-sm text-muted-foreground">
        Bài này chấm bằng kịch bản đóng vai client/server nên không có input dạng văn bản.
        Xem phần ví dụ trong đề bài, rồi bấm <b className="text-[var(--green)]">Nộp bài</b> để chạy toàn bộ test.
      </div>
    );
  const s = samples[Math.min(i, samples.length - 1)];
  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap gap-2">
        {samples.map((x, k) => (
          <button key={x.name} onClick={() => setI(k)}
            className={cn("rounded-lg px-4 py-1.5 text-sm", k === i ? "bg-[var(--chip)] font-medium text-foreground" : "text-muted-foreground hover:bg-[var(--chip)]")}>
            Case {k + 1}
          </button>
        ))}
      </div>
      <Box label="Input">{s.input}</Box>
      <Box label="Output mong đợi">{s.output}</Box>
    </div>
  );
}

function TestResult({ r, error, busy }) {
  const tests = r?.tests || [];
  const firstBad = Math.max(0, tests.findIndex((t) => t.verdict !== "AC"));
  const [sel, setSel] = useState(firstBad);
  useEffect(() => setSel(firstBad), [r]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="p-5 text-sm text-[var(--hard)]">{error}</div>;
  if (busy && !r)
    return (
      <div className="flex items-center gap-2 p-5 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Đang chấm… (biên dịch + chạy từng test trong Docker, thường 5–30 giây)
      </div>
    );
  if (!r) return <div className="flex h-full items-center justify-center p-5 text-sm text-muted-foreground">Bạn cần nộp bài trước.</div>;

  const t = tests[sel];
  return (
    <div className="p-4">
      <div className="mb-4 flex flex-wrap items-baseline gap-4">
        <span className={cn("text-xl font-semibold", vColor(r.verdict))}>{LABEL[r.verdict] || r.verdict}</span>
        {r.total ? <span className="text-sm text-muted-foreground">{r.passed}/{r.total} test đạt</span> : null}
        {tests.length > 0 && <span className="text-sm text-muted-foreground">Thời gian: {maxTime(r)} ms</span>}
        {r.sampleRun && <Pill>Chạy thử · chỉ test mẫu, chưa tính là nộp bài</Pill>}
      </div>

      {r.verdict === "CE" && <Box>{r.compile_log}</Box>}
      {r.message && <Box>{r.message}</Box>}

      {tests.length > 0 && (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            {tests.map((x, k) => (
              <button key={k} onClick={() => setSel(k)}
                className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm", k === sel ? "bg-[var(--chip)] font-medium text-foreground" : "text-muted-foreground hover:bg-[var(--chip)]")}>
                <span className={cn("size-1.5 rounded-full", x.verdict === "AC" ? "bg-[var(--green)]" : "bg-[var(--hard)]")} />
                {x.name}
              </button>
            ))}
          </div>
          {t && (
            <>
              <div className="mb-3 flex items-center gap-3 text-sm">
                <span className={cn("font-semibold", vColor(t.verdict))}>{LABEL[t.verdict] || t.verdict}</span>
                <span className="text-muted-foreground">{t.time_ms} ms</span>
              </div>
              {t.message
                ? <Box label="Chi tiết">{t.message}</Box>
                : <div className="text-sm text-muted-foreground">{t.verdict === "AC" ? "Test này đạt." : "Không có chi tiết (test ẩn)."}</div>}
            </>
          )}
        </>
      )}

      {r.compile_log && r.verdict !== "CE" && r.compile_log.trim() && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-muted-foreground">Cảnh báo của trình biên dịch</summary>
          <div className="mt-2"><Box>{r.compile_log}</Box></div>
        </details>
      )}
    </div>
  );
}

/* ---------- trang ---------- */

export default function Workspace({ problemId, problem, nav, user, samples, html, starter, originalStarter, examMinutes, history }) {
  const [code, setCode] = useState(starter);
  const [saved, setSaved] = useState(true);
  const [pos, setPos] = useState({ ln: 1, col: 1 });
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState(false); // đang "Chạy thử" (chỉ test mẫu, không lưu lịch sử)
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [past, setPast] = useState(history);
  const [leftTab, setLeftTab] = useState("desc"); // desc | subs | detail
  const [detail, setDetail] = useState(null); // { id, ...dữ liệu bài nộp } hoặc { id } khi đang tải
  const [bottomTab, setBottomTab] = useState("cases");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [bottomCollapsed, setBottomCollapsed] = useState(false);
  const leftRef = useRef(null);
  const bottomRef = useRef(null);
  const { resolvedTheme } = useTheme();
  const [left, setLeft] = useState(null); // giây còn lại trong chế độ thi
  const timer = useRef(null);
  const draftKey = `nj-draft-${problemId}`;

  // Bản nháp trong trình duyệt: mở lại trang vẫn còn code đang gõ dở.
  useEffect(() => {
    try {
      const d = localStorage.getItem(draftKey);
      if (d != null) setCode(d);
    } catch {}
  }, [draftKey]);
  useEffect(() => {
    setSaved(false);
    const h = setTimeout(() => {
      try { localStorage.setItem(draftKey, code); } catch {}
      setSaved(true);
    }, 600);
    return () => clearTimeout(h);
  }, [code, draftKey]);

  // Đồng hồ thi thử: lưu mốc bắt đầu trong trình duyệt, chỉ để nhắc giờ (không chặn nộp bài).
  useEffect(() => {
    if (!examMinutes) return;
    const key = `nj-exam-${problemId}`;
    let start = null;
    try { start = Number(localStorage.getItem(key)) || null; } catch {}
    if (start) tick(start);
    function tick(s) {
      clearInterval(timer.current);
      timer.current = setInterval(() => setLeft(Math.max(0, examMinutes * 60 - Math.floor((Date.now() - s) / 1000))), 500);
    }
    window.__njStartExam = () => {
      const s = Date.now();
      try { localStorage.setItem(key, String(s)); } catch {}
      tick(s);
    };
    return () => clearInterval(timer.current);
  }, [examMinutes, problemId]);

  async function submit() {
    setBusy(true); setError(""); setResult(null); setBottomTab("result");
    if (bottomRef.current?.isCollapsed()) bottomRef.current.expand();
    const res = await fetch("/api/submit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ problemId, code }) });
    const data = await res.json();
    if (!res.ok) { setError(data.error || "Lỗi khi nộp bài"); setBusy(false); return; }
    const id = data.id;
    setPast((h) => [{ id, status: "queued", created: Math.floor(Date.now() / 1000) }, ...h].slice(0, 30));
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const s = await (await fetch(`/api/submissions/${id}`)).json();
      if (s.status === "done") {
        setResult(s.result);
        setPast((h) => h.map((x) => x.id === id ? { ...x, status: "done", verdict: s.verdict, passed: s.result?.passed, total: s.result?.total } : x));
        break;
      }
      if (s.status === "running") setPast((h) => h.map((x) => x.id === id ? { ...x, status: "running" } : x));
    }
    setBusy(false);
  }

  // Chạy thử: biên dịch + chạy test mẫu, kết quả hiện ngay ở tab Test Result, không tính là một lần nộp.
  async function run() {
    setRunning(true); setError(""); setResult(null); setBottomTab("result");
    if (bottomRef.current?.isCollapsed()) bottomRef.current.expand();
    try {
      const res = await fetch("/api/run", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ problemId, code }) });
      const data = await res.json();
      if (!res.ok) setError(data.error || "Lỗi khi chạy thử");
      else setResult({ ...data.result, sampleRun: true });
    } catch {
      setError("Không kết nối được máy chủ");
    }
    setRunning(false);
  }

  async function openSubmission(id) {
    setDetail({ id }); setLeftTab("detail");
    const s = await (await fetch(`/api/submissions/${id}`)).json();
    setDetail({ id, ...s });
  }

  function loadIntoEditor() {
    if (!detail?.code) return;
    setCode(detail.code); setResult(detail.result); setError(""); setBottomTab("result");
  }

  function resetCode() {
    if (!confirm("Đưa về code khung ban đầu? Code đang viết sẽ mất (bài đã nộp vẫn còn trong Lịch sử nộp).")) return;
    setCode(originalStarter);
  }

  const maximized = leftCollapsed && bottomCollapsed;
  function toggleMax() {
    if (maximized) { leftRef.current?.expand(); bottomRef.current?.expand(); }
    else { leftRef.current?.collapse(); bottomRef.current?.collapse(); }
  }

  function defineThemes(monaco) {
    // Nền trong suốt để editor lấy màu của khung (--panel) theo từng hướng thiết kế.
    monaco.editor.defineTheme("nj-light", { base: "vs", inherit: true, rules: [], colors: { "editor.background": "#00000000", "editorLineNumber.foreground": "#a3a3a3" } });
    monaco.editor.defineTheme("nj-dark", { base: "vs-dark", inherit: true, rules: [], colors: { "editor.background": "#00000000", "editorLineNumber.foreground": "#6b6b6b" } });
  }

  const verdictTab = detail?.verdict ? LABEL[detail.verdict] || detail.verdict : "Bài nộp";

  return (
    <div className="lc-shell">
      <TopBar nav={nav} problemId={problemId} busy={busy} running={running} onRun={run} onSubmit={submit} examMinutes={examMinutes} left={left} user={user} />

      <div className="min-h-0 flex-1 px-2 pb-2">
        <PanelGroup direction="horizontal" autoSaveId="nj-lc-h">
          {/* ---- Trái ---- */}
          <Panel ref={leftRef} defaultSize={45} minSize={22} collapsible collapsedSize={0}
            onCollapse={() => setLeftCollapsed(true)} onExpand={() => setLeftCollapsed(false)}
            className="lc-panel">
            <TabBar right={<IconBtn label="Thu gọn" onClick={() => leftRef.current?.collapse()}><ChevronsLeft className="size-4" /></IconBtn>}>
              <Tab active={leftTab === "desc"} onClick={() => setLeftTab("desc")} icon={FileText} iconClass="text-[var(--accent)]">Đề bài</Tab>
              <Sep />
              {detail && (
                <>
                  <Tab active={leftTab === "detail"} onClick={() => setLeftTab("detail")} icon={History}
                    iconClass={detail.verdict ? vColor(detail.verdict) : ""}
                    onClose={() => { setDetail(null); if (leftTab === "detail") setLeftTab("subs"); }}>
                    <span className={detail.verdict ? vColor(detail.verdict) : ""}>{verdictTab}</span>
                  </Tab>
                  <Sep />
                </>
              )}
              <Tab active={leftTab === "subs"} onClick={() => setLeftTab("subs")} icon={History} iconClass="text-[var(--accent)]">Lịch sử nộp</Tab>
            </TabBar>
            <div className="min-h-0 flex-1 overflow-y-auto">
              {leftTab === "desc" && <Description problem={problem} html={html} solved={past.some((s) => s.verdict === "AC")} />}
              {leftTab === "subs" && <SubmissionList past={past} onOpen={openSubmission} />}
              {leftTab === "detail" && (
                <SubmissionDetail sub={detail?.code != null ? detail : null} user={user}
                  onBack={() => setLeftTab("subs")} onLoad={loadIntoEditor} />
              )}
            </div>
            <div className="flex h-9 shrink-0 items-center justify-between px-4 text-xs text-muted-foreground">
              <span>Bài {nav.all.indexOf(problemId) + 1} / {nav.all.length} · Chương {problem.chapter}</span>
              <span>Đã nộp {past.length} lần · <span className="text-[var(--green)]">AC {past.filter((s) => s.verdict === "AC").length}</span></span>
            </div>
          </Panel>

          <Handle />

          {/* ---- Phải ---- */}
          <Panel defaultSize={55} minSize={30}>
            <PanelGroup direction="vertical" autoSaveId="nj-lc-v">
              <Panel defaultSize={62} minSize={20} className="lc-panel">
                <TabBar right={
                  <>
                    {leftCollapsed && !maximized && <IconBtn label="Mở khung đề bài" onClick={() => leftRef.current?.expand()}><PanelLeftOpen className="size-4" /></IconBtn>}
                    <IconBtn label={maximized ? "Thu nhỏ" : "Phóng to"} onClick={toggleMax}>
                      {maximized ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
                    </IconBtn>
                  </>
                }>
                  <Tab active icon={Code2} iconClass="text-[var(--green)]">Code</Tab>
                </TabBar>
                <div className="flex h-8 shrink-0 items-center gap-3 px-3 text-sm">
                  <span className="font-medium">C</span>
                  <span className="flex min-w-0 items-center gap-1 truncate text-xs text-muted-foreground">
                    <Lock className="size-3.5 shrink-0" />gcc -std=gnu11 -Wall -Wextra -pthread
                  </span>
                  <span className="flex-1" />
                  <IconBtn label="Đưa về code khung" onClick={resetCode}><RotateCcw className="size-4" /></IconBtn>
                </div>
                <div className="min-h-0 flex-1">
                  <Monaco
                    height="100%" language="c" value={code}
                    theme={resolvedTheme === "dark" ? "nj-dark" : "nj-light"}
                    beforeMount={defineThemes}
                    onMount={(editor) => editor.onDidChangeCursorPosition((e) => setPos({ ln: e.position.lineNumber, col: e.position.column }))}
                    onChange={(v) => setCode(v ?? "")}
                    options={{
                      minimap: { enabled: false }, fontSize: 13, lineHeight: 20, fontFamily: "var(--font-jetbrains), Consolas, monospace",
                      scrollBeyondLastLine: false, tabSize: 4, automaticLayout: true, padding: { top: 8 },
                      lineNumbersMinChars: 3, renderLineHighlight: "line", scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
                    }}
                  />
                </div>
                <div className="flex h-6 shrink-0 items-center justify-between px-3 text-xs text-muted-foreground">
                  <span>{saved ? "Đã lưu" : "Đang lưu…"}</span>
                  <span>Ln {pos.ln}, Col {pos.col}</span>
                </div>
              </Panel>

              <Handle vertical />

              <Panel ref={bottomRef} defaultSize={38} minSize={12} collapsible collapsedSize={0}
                onCollapse={() => setBottomCollapsed(true)} onExpand={() => setBottomCollapsed(false)}
                className="lc-panel">
                <TabBar>
                  <Tab active={bottomTab === "cases"} onClick={() => setBottomTab("cases")} icon={SquareCheck} iconClass="text-[var(--green)]">Testcase</Tab>
                  <Sep />
                  <Tab active={bottomTab === "result"} onClick={() => setBottomTab("result")} icon={Terminal} iconClass="text-[var(--green)]">
                    Test Result{busy && <Loader2 className="ml-1 size-3.5 animate-spin" />}
                    {!busy && result && (result.verdict === "AC"
                      ? <Check className="ml-1 size-3.5 text-[var(--green)]" />
                      : <X className="ml-1 size-3.5 text-[var(--hard)]" />)}
                  </Tab>
                </TabBar>
                <div className="min-h-0 flex-1 overflow-y-auto">
                  {bottomTab === "cases" ? <Testcases samples={samples} /> : <TestResult r={result} error={error} busy={busy || running} />}
                </div>
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
}
