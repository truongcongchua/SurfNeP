"use client";
// Trang bài theo bố cục LeetCode (/problems/x/description):
//  thanh trên: logo · Danh sách bài · ‹ › ngẫu nhiên | Chạy thử · Nộp bài · Ghi chú | Bố cục · Cài đặt · Đồng hồ · giao diện · tài khoản
//  khung trái: Đề bài / bài nộp đang xem / Lịch sử nộp / Ghi chú — chân khung: thích, sao, chia sẻ
//  khung Code: thanh công cụ (lấy code nộp gần nhất, đặt lại, toàn màn hình) — khung Testcase / Test Result.
// Bố cục "Mặc định" (2 cột, phải chia trên/dưới) hoặc "Leet" (3 cột). Các khung kéo chỉnh, phóng to, thu gọn được.
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useCallback, useEffect, useRef, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import {
  Bookmark, Braces, Check, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Code2, Expand, FileText, History,
  Loader2, Lock, Maximize, Minimize, NotebookPen, PanelLeftOpen, RotateCcw, Settings, Shrink,
  SquareCheck, Terminal, X,
} from "lucide-react";
import { ProblemDrawer } from "@/components/problem-drawer";
import { cn } from "@/lib/utils";
import { TopBar, NavIcon } from "@/components/workspace/top-bar";
import { ConfirmDialog } from "@/components/workspace/confirm-dialog";
import { useLocal, useSettings } from "@/components/workspace/use-settings";
import { SettingsDialog } from "@/components/workspace/settings-dialog";
import { LayoutsMenu } from "@/components/workspace/layouts-menu";
import { Stopwatch } from "@/components/workspace/stopwatch";
import { NoteEditor } from "@/components/workspace/note-editor";
import { Description, DescFooter, LABEL, SubmissionDetail, SubmissionList, TestResult, Testcases, vColor } from "@/components/workspace/panels";

const Monaco = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="p-4 text-sm text-[var(--muted)]">Đang tải trình soạn thảo…</div>,
});

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

// Thanh tab cuộn ngang (ẩn thanh cuộn), con lăn cuộn ngang, mép bị che thì mờ dần, tab vừa chọn tự cuộn vào.
function TabBar({ children, right, activeKey }) {
  const ref = useRef(null);
  const [edge, setEdge] = useState({ l: false, r: false });
  const measure = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const l = el.scrollLeft > 2, r = el.scrollLeft + el.clientWidth < el.scrollWidth - 2;
    setEdge((e) => (e.l === l && e.r === r ? e : { l, r }));
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onWheel = (e) => {
      if (el.scrollWidth <= el.clientWidth || Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      el.scrollLeft += e.deltaY;
      e.preventDefault();
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("scroll", measure, { passive: true });
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    return () => { el.removeEventListener("wheel", onWheel); el.removeEventListener("scroll", measure); ro.disconnect(); };
  }, [measure]);
  useEffect(() => {
    const el = ref.current;
    const t = el?.querySelector('[data-active="true"]');
    if (!t) return;
    const pad = 32;
    const from = t.offsetLeft - pad, to = t.offsetLeft + t.offsetWidth + pad;
    if (from < el.scrollLeft) el.scrollTo({ left: Math.max(0, from), behavior: "smooth" });
    else if (to > el.scrollLeft + el.clientWidth) el.scrollTo({ left: to - el.clientWidth, behavior: "smooth" });
    measure();
  }, [activeKey, measure]);
  const mask = `linear-gradient(to right, ${edge.l ? "transparent 0, #000 32px" : "#000 0"}, ${edge.r ? "#000 calc(100% - 32px), transparent 100%" : "#000 100%"})`;
  return (
    <div className="group/bar flex h-9 shrink-0 items-center bg-[var(--panel-head)] pl-1.5 pr-1">
      <div ref={ref} style={{ maskImage: mask, WebkitMaskImage: mask }} className="tab-scroll relative flex min-w-0 flex-1 items-center overflow-x-auto">
        {children}
      </div>
      {/* Như LeetCode: nút phóng to / thu gọn chỉ hiện khi rê chuột lên thanh tab. */}
      {right && <div className="ml-1 flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover/bar:opacity-100 focus-within:opacity-100">{right}</div>}
    </div>
  );
}

function Tab({ active, onClick, icon: Icon, iconClass, children, onClose, onDragStart, onDragEnd }) {
  return (
    <div className={cn("flex shrink-0 items-center", onDragStart && "cursor-grab active:cursor-grabbing")}
      draggable={!!onDragStart} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <button
        onClick={onClick} data-active={active ? "true" : "false"}
        className={cn(
          "group flex h-7 items-center gap-1.5 whitespace-nowrap rounded-[5px] px-2 text-sm transition-colors hover:bg-[var(--raised)]",
          active ? "font-medium text-[var(--title)]" : "text-[color:var(--muted)]"
        )}
      >
        <Icon className={cn("size-4", iconClass, !active && "opacity-70 group-hover:opacity-100")} />
        {children}
      </button>
      {onClose && (
        <button onClick={onClose} className="ml-0.5 rounded-md p-1 text-[var(--muted)] transition-colors hover:bg-[var(--raised)] hover:text-[var(--title)]" aria-label="Đóng tab" title="Đóng (Alt+W)">
          <X className="size-3.5" />
        </button>
      )}
    </div>
  );
}
// Phủ lên khung khi đang kéo tab: thả vào đây để chuyển tab sang khung này (như LeetCode).
// Giữa khung = nhập vào khung làm tab; 25% mỗi mép = tách thành khung riêng nằm ở phía đó (nửa khung).
const ZONE_BOX = {
  center: "inset-[18%]", left: "inset-y-0 left-0 w-1/2", right: "inset-y-0 right-0 w-1/2",
  top: "inset-x-0 top-0 h-1/2", bottom: "inset-x-0 bottom-0 h-1/2",
};
function dropZone(e) {
  const r = e.currentTarget.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
  if (x < 0.25) return "left";
  if (x > 0.75) return "right";
  if (y < 0.25) return "top";
  if (y > 0.75) return "bottom";
  return "center";
}
function DropOverlay({ show, label, onDrop }) {
  const [zone, setZone] = useState(null);
  if (!show) return null;
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setZone(dropZone(e)); }} onDragLeave={() => setZone(null)}
      onDrop={(e) => { e.preventDefault(); const z = dropZone(e); setZone(null); onDrop(z); }}
      className="absolute inset-0 z-30 rounded-[inherit] bg-[color-mix(in_srgb,var(--panel)_55%,transparent)]"
    >
      {zone && <div className={cn("pointer-events-none absolute rounded-md border-2 border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_22%,transparent)] transition-all", ZONE_BOX[zone])} />}
      <span className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-md bg-[var(--panel)] px-3 py-1 text-sm text-[var(--title)] shadow-[var(--pop-shadow)]">
        {zone && zone !== "center" ? `Tách ${{ left: "sang trái", right: "sang phải", top: "lên trên", bottom: "xuống dưới" }[zone]}` : label}
      </span>
    </div>
  );
}

const Sep = () => <span className="mx-1 h-3.5 w-px shrink-0 bg-[var(--line-strong)] opacity-60" />;

function IconBtn({ label, onClick, children, disabled, active, className }) {
  return (
    <button
      title={label} aria-label={label} onClick={onClick} disabled={disabled}
      className={cn("inline-flex size-7 items-center justify-center rounded-md transition-colors hover:bg-[var(--raised)] hover:text-[var(--title)] disabled:pointer-events-none disabled:opacity-40",
        active ? "text-[var(--accent)]" : "text-[var(--muted)]", className)}
    >{children}</button>
  );
}

/* ---------- trang ---------- */

export default function Workspace({ problemId, problem, nav, user, samples, html, starter, originalStarter, examMinutes, history, stats, similar, lastSubmitted, social, streak, examDays }) {
  const router = useRouter();
  const [settings, setSettings] = useSettings();
  const [timerCfg, setTimerCfg] = useLocal("nj-timer-cfg", { byDifficulty: false, autoReset: false, alarm: false });
  const [code, setCode] = useState(starter);
  const [saved, setSaved] = useState(true);
  const [pos, setPos] = useState({ ln: 1, col: 1 });
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [debugging, setDebugging] = useState(false);
  const [error, setError] = useState("");
  const [waitNote, setWaitNote] = useState("");
  const [result, setResult] = useState(null);
  const [past, setPast] = useState(history);
  const [lastCode, setLastCode] = useState(lastSubmitted);
  const [leftTab, setLeftTab] = useState("desc"); // desc | subs | detail | note
  const [detail, setDetail] = useState(null);
  // Tab bài nộp đang xem nằm ở khung nào: "left" (cạnh Đề bài) | "code" (cạnh Code) | "test" (cạnh Testcase). Kéo thả để đổi.
  const [detailDock, setDetailDock] = useLocal("nj-detail-dock", "code");
  // detailDock = "left" | "code" | "test" (nhập làm tab của khung) hoặc "<khung>:<mép>" (tách nửa khung, mép = left|right|top|bottom).
  const [dockPanel, dockSide] = String(detailDock).split(":");
  const tabIn = (p) => !!detail && dockPanel === p && !dockSide;
  const splitHere = (p) => !!detail && dockPanel === p && !!dockSide;
  const [codeTab, setCodeTab] = useState("code"); // code | detail
  const [dragging, setDragging] = useState(false);
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useLocal(`nj-note-${problemId}`, "");
  const [soc, setSoc] = useState(social); // { likes, mine, favorite } — lưu trên máy chủ
  const [confirm, setConfirm] = useState(null); // { message, onOk }
  const [langMenu, setLangMenu] = useState(false);
  const [bottomTab, setBottomTab] = useState("cases");
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [bottomCollapsed, setBottomCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [codeCollapsed, setCodeCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [toast, setToast] = useState("");
  const leftRef = useRef(null), bottomRef = useRef(null), rightRef = useRef(null), codeRef = useRef(null);
  const codeBox = useRef(null);
  const clockRef = useRef(null);
  const { resolvedTheme } = useTheme();
  const draftKey = `nj-draft-${problemId}`;
  const leet = settings.layout === "leet";

  // Testcase sửa được (bài stdio/function): mặc định = input của test mẫu.
  const editable = problem.type === "stdio" || problem.type === "function";
  const defaultCases = samples.length ? samples.map((s) => s.input.replace(/\s+$/, "")) : [""];
  const [cases, setCases] = useLocal(`nj-cases-${problemId}`, defaultCases);
  const [caseSel, setCaseSel] = useState(0);

  const flash = useCallback((msg) => { setToast(msg); setTimeout(() => setToast(""), 1800); }, []);

  // Thích / Không thích / Yêu thích: cập nhật ngay, rồi đồng bộ với máy chủ (số lượt thích là của mọi người dùng).
  async function sendReact(body) {
    const prev = soc;
    setSoc((c) => ({ ...c, ...(body.like !== undefined ? { mine: body.like, likes: c.likes + (body.like === 1 ? 1 : 0) - (c.mine === 1 ? 1 : 0) } : {}), ...(body.favorite !== undefined ? { favorite: body.favorite } : {}) }));
    try {
      const res = await fetch(`/api/problems/${problemId}/react`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) throw new Error();
      setSoc(await res.json());
    } catch { setSoc(prev); flash("Không lưu được, thử lại sau"); }
  }

  // Bản nháp trong trình duyệt: mở lại trang vẫn còn code đang gõ dở.
  useEffect(() => {
    try { const d = localStorage.getItem(draftKey); if (d != null) setCode(d); } catch {}
  }, [draftKey]);
  useEffect(() => {
    setSaved(false);
    const h = setTimeout(() => { try { localStorage.setItem(draftKey, code); } catch {} setSaved(true); }, 600);
    return () => clearTimeout(h);
  }, [code, draftKey]);

  useEffect(() => {
    const onFs = () => setFullscreen(document.fullscreenElement === codeBox.current);
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

  const openBottom = (tab) => {
    setBottomTab(tab);
    if (bottomRef.current?.isCollapsed()) bottomRef.current.expand();
  };

  async function submit() {
    if (busy || running || debugging) return;
    setBusy(true); setError(""); setResult(null); openBottom("result");
    const res = await fetch("/api/submit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ problemId, code }) });
    const data = await res.json();
    if (!res.ok) { setError(data.error || "Lỗi khi nộp bài"); setBusy(false); return; }
    const id = data.id;
    setLastCode(code);
    setPast((h) => [{ id, status: "queued", created: Math.floor(Date.now() / 1000) }, ...h].slice(0, 30));
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const s = await (await fetch(`/api/submissions/${id}`)).json();
      if (s.status === "done") {
        setResult(s.result);
        setPast((h) => h.map((x) => x.id === id ? { ...x, status: "done", verdict: s.verdict, passed: s.result?.passed, total: s.result?.total } : x));
        if (s.verdict === "AC") clockRef.current?.onAccepted();
        break;
      }
      setWaitNote(s.status === "queued" && s.position > 0 ? `Đang xếp hàng — vị trí ${s.position}` : "");
      if (s.status === "running") setPast((h) => h.map((x) => x.id === id ? { ...x, status: "running" } : x));
    }
    setWaitNote("");
    setBusy(false);
  }

  // Chạy thử: bài stdio/function chạy đúng các testcase trong khung Testcase (output mong đợi lấy từ lời giải mẫu);
  // bài client/server chạy test mẫu. Không tính là một lần nộp.
  async function run(debug = false) {
    if (busy || running || debugging) return;
    (debug ? setDebugging : setRunning)(true); setError(""); setResult(null); openBottom("result");
    try {
      const body = { problemId, code, ...(editable ? { cases } : {}), ...(debug ? { debug: true } : {}) };
      const res = await fetch("/api/run", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      if (!res.ok) setError(data.error || "Lỗi khi chạy thử");
      else setResult({ ...data.result, sampleRun: true, debugRun: debug });
    } catch {
      setError("Không kết nối được máy chủ");
    }
    (debug ? setDebugging : setRunning)(false);
  }
  const debugRun = () => run(true);

  // Chọn tab "bài nộp" trong khung `dock` và mở khung đó ra nếu đang thu gọn.
  function showDetailIn(dock) {
    if (dock.includes(":")) { // tách nửa khung: chỉ cần mở khung chứa nó
      const ref = { left: leftRef, code: codeRef, test: bottomRef }[dock.split(":")[0]];
      if (ref.current?.isCollapsed()) ref.current.expand();
    } else if (dock === "left") { setLeftTab("detail"); if (leftRef.current?.isCollapsed()) leftRef.current.expand(); }
    else if (dock === "code") { setCodeTab("detail"); if (codeRef.current?.isCollapsed()) codeRef.current.expand(); }
    else { setBottomTab("detail"); if (bottomRef.current?.isCollapsed()) bottomRef.current.expand(); }
  }
  // Khung nào đang hiện tab bài nộp mà tab đó đã chuyển đi chỗ khác thì trả về tab mặc định của khung.
  function releaseDetail(keep) {
    if (keep !== "left") setLeftTab((t) => (t === "detail" ? "subs" : t));
    if (keep !== "code") setCodeTab((t) => (t === "detail" ? "code" : t));
    if (keep !== "test") setBottomTab((t) => (t === "detail" ? "cases" : t));
  }
  function moveDetail(panel, zone) {
    setDragging(false);
    if (!detail) return;
    const dock = zone === "center" ? panel : `${panel}:${zone}`;
    setDetailDock(dock); releaseDetail(zone === "center" ? panel : null); showDetailIn(dock);
  }
  function closeDetail() {
    setDetail(null); releaseDetail(null);
    if (detailDock === "left") setLeftTab("subs");
  }
  const detailActive = !!detail && (splitHere(dockPanel) || (detailDock === "left" && leftTab === "detail") || (detailDock === "code" && codeTab === "detail") || (detailDock === "test" && bottomTab === "detail"));

  async function openSubmission(id) {
    setDetail({ id }); showDetailIn(detailDock);
    const s = await (await fetch(`/api/submissions/${id}`)).json();
    setDetail({ id, ...s });
  }

  function loadIntoEditor() {
    if (!detail?.code) return;
    setCode(detail.code); setResult(detail.result); setError("");
    if (detailDock === "code") setCodeTab("code");
    openBottom("result");
  }
  function resetCode() {
    setConfirm({ message: "Code đang viết sẽ bị xoá và đưa về code khung ban đầu. Các bài đã nộp vẫn còn trong Lịch sử nộp.", onOk: () => setCode(originalStarter) });
  }
  function retrieveLast() {
    if (!lastCode) return flash("Bạn chưa nộp bài này lần nào");
    setConfirm({ message: "Code hiện tại sẽ bị xoá và thay bằng code bạn nộp gần nhất!", onOk: () => setCode(lastCode) });
  }
  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else codeBox.current?.requestFullscreen?.();
  }
  async function share() {
    const url = `${location.origin}/problems/${problemId}`;
    try { await navigator.clipboard.writeText(url); flash("Đã sao chép liên kết"); } catch { flash(url); }
  }
  function closeActiveTab() {
    if (detailActive) closeDetail();
    else if (leftTab === "note") { setNoteOpen(false); setLeftTab("desc"); }
  }
  function toggleNote() {
    if (noteOpen && leftTab === "note") { setNoteOpen(false); setLeftTab("desc"); return; }
    setNoteOpen(true); setLeftTab("note");
    if (leftRef.current?.isCollapsed()) leftRef.current.expand();
  }

  // Phóng to khung đề = thu gọn phần code + testcase.
  function toggleLeftMax() {
    if (leet) {
      const both = codeRef.current?.isCollapsed() && bottomRef.current?.isCollapsed();
      if (both) { codeRef.current?.expand(); bottomRef.current?.expand(); } else { codeRef.current?.collapse(); bottomRef.current?.collapse(); }
    } else if (rightRef.current?.isCollapsed()) rightRef.current.expand();
    else rightRef.current?.collapse();
  }
  const maximized = leftCollapsed && bottomCollapsed;
  function toggleMax() {
    if (maximized) { leftRef.current?.expand(); bottomRef.current?.expand(); }
    else { leftRef.current?.collapse(); bottomRef.current?.collapse(); }
  }
  const testMax = codeCollapsed && leftCollapsed;
  function toggleTestMax() {
    if (testMax) { codeRef.current?.expand(); leftRef.current?.expand(); }
    else { codeRef.current?.collapse(); leftRef.current?.collapse(); }
  }
  function resetLayout() {
    try { Object.keys(localStorage).filter((k) => k.startsWith("react-resizable-panels:nj-")).forEach((k) => localStorage.removeItem(k)); } catch {}
    location.reload();
  }

  // Phím tắt (giống LeetCode). Trong Monaco đăng ký riêng ở onMount để editor không nuốt phím.
  const keys = useRef({});
  keys.current = { run: () => run(), submit, toggleMax, toggleFullscreen, closeActiveTab, settings };
  useEffect(() => {
    const onKey = (e) => {
      const k = keys.current;
      if (e.ctrlKey && e.key === "'" && k.settings.runShortcut) { e.preventDefault(); k.run(); }
      else if (e.ctrlKey && e.key === "Enter" && k.settings.submitShortcut) { e.preventDefault(); k.submit(); }
      else if (e.altKey && (e.key === "=" || e.key === "+")) { e.preventDefault(); k.toggleMax(); }
      else if (e.altKey && e.code === "KeyF") { e.preventDefault(); k.toggleFullscreen(); }
      else if (e.altKey && e.code === "KeyW") { e.preventDefault(); k.closeActiveTab(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function onEditorMount(editor, monaco) {
    editor.onDidChangeCursorPosition((e) => setPos({ ln: e.position.lineNumber, col: e.position.column }));
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Quote, () => keys.current.settings.runShortcut && keys.current.run());
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => keys.current.settings.submitShortcut && keys.current.submit());
  }
  function defineThemes(monaco) {
    monaco.editor.defineTheme("nj-light", { base: "vs", inherit: true, rules: [], colors: {
      "editor.background": "#00000000", "editorLineNumber.foreground": "#999999", "editorLineNumber.activeForeground": "#262626",
      "editor.lineHighlightBackground": "#00000000", "editor.lineHighlightBorder": "#eeeeee",
      "editorStickyScroll.background": "#ffffff", "editorStickyScrollGutter.background": "#ffffff", "editorStickyScrollHover.background": "#f3f3f3", "editorStickyScroll.shadow": "#00000014" } });
    monaco.editor.defineTheme("nj-dark", { base: "vs-dark", inherit: true, rules: [], colors: {
      "editor.background": "#00000000", "editorLineNumber.foreground": "#6e6e6e", "editorLineNumber.activeForeground": "#cccccc",
      "editor.lineHighlightBackground": "#00000000", "editor.lineHighlightBorder": "#ffffff14",
      "editorStickyScroll.background": "#1e1e1e", "editorStickyScrollGutter.background": "#1e1e1e", "editorStickyScrollHover.background": "#2a2a2a", "editorStickyScroll.shadow": "#00000066" } });
  }

  const shuffle = () => {
    const others = nav.all.filter((x) => x !== problemId);
    if (others.length) router.push(`/problems/${others[Math.floor(Math.random() * others.length)]}`);
  };
  const verdictTab = detail?.verdict ? LABEL[detail.verdict] || detail.verdict : "Bài nộp";
  const acCount = past.filter((s) => s.verdict === "AC").length;

  /* ----- tab bài nộp: dùng chung cho cả 3 khung, kéo thả để đổi khung ----- */

  const detailTabEl = (active, onClick) => (
    <Tab active={active} onClick={onClick} icon={History} iconClass="text-[var(--accent)]"
      onClose={closeDetail}
      onDragStart={(e) => { e.dataTransfer.setData("text/plain", "nj-detail"); e.dataTransfer.effectAllowed = "move"; setTimeout(() => setDragging(true), 0); }}
      onDragEnd={() => setDragging(false)}>
      {verdictTab}
    </Tab>
  );
  const detailView = <SubmissionDetail sub={detail?.code != null ? detail : null} user={user}
    onBack={() => { setLeftTab("subs"); if (leftRef.current?.isCollapsed()) leftRef.current.expand(); }} onLoad={loadIntoEditor} />;
  const dropFor = (panel, label) => <DropOverlay show={dragging && !!detail} label={label} onDrop={(zone) => moveDetail(panel, zone)} />;

  // Khung tách riêng cho tab bài nộp (thả vào mép của một khung): đặt cạnh khung `target` ở phía `dockSide`.
  const splitWrap = (target, body) => {
    if (!splitHere(target)) return <div className="lc-panel h-full">{body}</div>;
    const horizontal = dockSide === "left" || dockSide === "right";
    const first = dockSide === "left" || dockSide === "top";
    const side = (
      <Panel id="detail" order={first ? 1 : 2} defaultSize={40} minSize={15}>
        <div className="lc-panel h-full">
          <TabBar activeKey="detail">{detailTabEl(true, () => {})}</TabBar>
          <div className="min-h-0 flex-1 overflow-y-auto">{detailView}</div>
        </div>
      </Panel>
    );
    const main = (
      <Panel id="main" order={first ? 2 : 1} defaultSize={60} minSize={15}>
        <div className="lc-panel h-full">{body}</div>
      </Panel>
    );
    return (
      <PanelGroup key={detailDock} direction={horizontal ? "horizontal" : "vertical"}>
        {first ? <>{side}<Handle vertical={!horizontal} />{main}</> : <>{main}<Handle vertical={!horizontal} />{side}</>}
      </PanelGroup>
    );
  };

  /* ----- các khung ----- */

  const leftPanel = (
    <Panel id="left" order={1} ref={leftRef} defaultSize={leet ? 33 : 30} minSize={20} collapsible collapsedSize={0}
      onCollapse={() => setLeftCollapsed(true)} onExpand={() => setLeftCollapsed(false)}>
      {splitWrap("left", <>
      {dropFor("left", "Thả vào khung đề bài")}
      <TabBar activeKey={`${leftTab}|${detail && detailDock === "left" ? 1 : 0}|${noteOpen ? 1 : 0}`}
        right={<>
          <IconBtn label={rightCollapsed ? "Thu nhỏ" : "Phóng to"} onClick={toggleLeftMax}>{rightCollapsed ? <Minimize className="size-4" /> : <Maximize className="size-4" />}</IconBtn>
          {!rightCollapsed && <IconBtn label="Thu gọn" onClick={() => leftRef.current?.collapse()}><ChevronLeft className="size-4" /></IconBtn>}
        </>}>
        <Tab active={leftTab === "desc"} onClick={() => setLeftTab("desc")} icon={FileText} iconClass="text-[var(--accent)]">Đề bài</Tab>
        <Sep />
        <Tab active={leftTab === "subs"} onClick={() => setLeftTab("subs")} icon={History} iconClass="text-[var(--accent)]">Lịch sử nộp</Tab>
        {detail && detailDock === "left" && (<>
          <Sep />
          {detailTabEl(leftTab === "detail", () => setLeftTab("detail"))}
        </>)}
        {noteOpen && (<>
          <Sep />
          <Tab active={leftTab === "note"} onClick={() => setLeftTab("note")} icon={NotebookPen} iconClass="text-[var(--brand)]"
            onClose={() => { setNoteOpen(false); if (leftTab === "note") setLeftTab("desc"); }}>Ghi chú</Tab>
        </>)}
      </TabBar>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {leftTab === "desc" && <Description problem={problem} html={html} solved={acCount > 0} stats={stats} similar={similar} />}
        {leftTab === "subs" && <SubmissionList past={past} onOpen={openSubmission} />}
        {leftTab === "detail" && detail && detailView}
        {leftTab === "note" && <NoteEditor value={note} onChange={setNote} />}
      </div>
      <DescFooter likes={soc.likes} mine={soc.mine} favorite={soc.favorite} onLike={(v) => sendReact({ like: v })} onFavorite={(v) => sendReact({ favorite: v })}
        onShare={share} onHelp={() => setSettingsOpen("keys")}
        />
      </>)}
    </Panel>
  );

  const codePanel = (
    <Panel id="code" order={2} ref={codeRef} defaultSize={leet ? 40 : 55} minSize={15} collapsible collapsedSize={0}
      onCollapse={() => setCodeCollapsed(true)} onExpand={() => setCodeCollapsed(false)}>
      {splitWrap("code", <>
      {dropFor("code", "Thả vào khung Code")}
      <div ref={codeBox} className="flex h-full flex-col bg-[var(--panel)]">
        <TabBar activeKey={`${codeTab}|${detail && detailDock === "code" ? 1 : 0}`} right={<>
          {leftCollapsed && !maximized && <IconBtn label="Mở khung đề bài" onClick={() => leftRef.current?.expand()}><PanelLeftOpen className="size-4" /></IconBtn>}
          <IconBtn label={maximized ? "Thu nhỏ (Alt+=)" : "Phóng to (Alt+=)"} onClick={toggleMax}>{maximized ? <Minimize className="size-4" /> : <Maximize className="size-4" />}</IconBtn>
        </>}>
          <Tab active={codeTab === "code"} onClick={() => setCodeTab("code")} icon={Code2} iconClass="text-[var(--green)]">Code</Tab>
          {detail && detailDock === "code" && (<><Sep />{detailTabEl(codeTab === "detail", () => setCodeTab("detail"))}</>)}
        </TabBar>
        {codeTab === "detail" && detail && detailDock === "code" && <div className="min-h-0 flex-1 overflow-y-auto">{detailView}</div>}
        {/* Giữ Monaco luôn gắn vào cây DOM (chỉ ẩn) để không mất vị trí con trỏ / lịch sử hoàn tác khi đổi tab. */}
        <div className={cn("flex min-h-0 flex-1 flex-col", codeTab === "detail" && detailDock === "code" && detail && "hidden")}>
        <div className="relative flex h-8 shrink-0 items-center gap-1 px-2 text-sm">
          <button onClick={() => setLangMenu((v) => !v)} className="flex h-6 items-center gap-1 rounded-[5px] px-1.5 text-[var(--text2)] hover:bg-[var(--fill-3)]" aria-haspopup="listbox">
            C <ChevronDown className="size-3.5" />
          </button>
          {langMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setLangMenu(false)} />
              <div role="listbox" className="absolute left-2 top-8 z-50 w-72 rounded-lg bg-[var(--panel)] p-1 text-sm shadow-[var(--pop-shadow)]">
                <button role="option" aria-selected onClick={() => setLangMenu(false)} className="flex w-full items-center gap-2 rounded px-2 py-2 text-left hover:bg-[var(--raised)]">
                  <Check className="size-4 text-[var(--green)]" /><span><b className="font-medium text-[var(--title)]">C</b><span className="block text-xs text-[var(--muted)]">gcc -std=gnu11 -Wall -Wextra -pthread</span></span>
                </button>
              </div>
            </>
          )}
          <span className="flex items-center gap-1.5 px-1 text-[var(--text2)]" title="gcc -std=gnu11 -Wall -Wextra -pthread"><Lock className="size-3.5" />Auto</span>
          <span className="flex-1" />
          <NavIcon label="Ghi chú bài nộp" onClick={toggleNote} className="size-6 rounded-[5px]"><Bookmark /></NavIcon>
          <NavIcon label="Lấy code nộp gần nhất" onClick={retrieveLast} className="size-6 rounded-[5px]"><Braces /></NavIcon>
          <NavIcon label="Đưa về code khung ban đầu" onClick={resetCode} className="size-6 rounded-[5px]"><RotateCcw /></NavIcon>
          <NavIcon label={fullscreen ? "Thoát toàn màn hình (Alt+F)" : "Toàn màn hình (Alt+F)"} onClick={toggleFullscreen} className="size-6 rounded-[5px]">{fullscreen ? <Shrink /> : <Expand />}</NavIcon>
        </div>
        <div className="min-h-0 flex-1">
          <Monaco
            height="100%" language="c" value={code}
            theme={resolvedTheme === "dark" ? "nj-dark" : "nj-light"}
            beforeMount={defineThemes} onMount={onEditorMount}
            onChange={(v) => setCode(v ?? "")}
            options={{
              minimap: { enabled: false }, fontSize: settings.fontSize, lineHeight: Math.round(settings.fontSize * 1.55),
              fontFamily: "Menlo, Monaco, Consolas, 'Courier New', monospace", fontLigatures: settings.ligatures,
              tabSize: settings.tabSize, wordWrap: settings.wordWrap ? "on" : "off",
              lineNumbers: settings.relativeLines ? "relative" : "on", cursorBlinking: settings.noCursorBlink ? "solid" : "blink",
              scrollBeyondLastLine: false, automaticLayout: true, padding: { top: 8 },
              lineNumbersMinChars: 3, renderLineHighlight: "line", scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
            }}
          />
        </div>
        <div className="flex h-7 shrink-0 items-center justify-between gap-3 px-3 text-xs text-[var(--text3)]">
          <span>{saved ? "Đã lưu" : "Đang lưu…"}</span>
          <span className="flex items-center gap-3">
            Ln {pos.ln}, Col {pos.col}
            {bottomCollapsed && !maximized && (
              <button onClick={() => bottomRef.current?.expand()} className="flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-[var(--raised)] hover:text-[var(--title)]">
                <Terminal className="size-3.5" />Console<ChevronUp className="size-3.5" />
              </button>
            )}
          </span>
        </div>
        </div>
      </div>
      </>)}
    </Panel>
  );

  const testPanel = (
    <Panel id="test" order={3} ref={bottomRef} defaultSize={leet ? 27 : 45} minSize={12} collapsible collapsedSize={0}
      onCollapse={() => setBottomCollapsed(true)} onExpand={() => setBottomCollapsed(false)}>
      {splitWrap("test", <>
      {dropFor("test", "Thả vào khung Testcase")}
      <TabBar activeKey={`${bottomTab}|${detail && detailDock === "test" ? 1 : 0}`} right={<>
        <IconBtn label={testMax ? "Thu nhỏ" : "Phóng to"} onClick={toggleTestMax}>{testMax ? <Minimize className="size-4" /> : <Maximize className="size-4" />}</IconBtn>
        <IconBtn label="Thu gọn" onClick={() => bottomRef.current?.collapse()}>{leet ? <ChevronRight className="size-4" /> : <ChevronDown className="size-4" />}</IconBtn>
      </>}>
        <Tab active={bottomTab === "cases"} onClick={() => setBottomTab("cases")} icon={SquareCheck} iconClass="text-[var(--green)]">Testcase</Tab>
        <Sep />
        <Tab active={bottomTab === "result"} onClick={() => setBottomTab("result")} icon={Terminal} iconClass="text-[var(--green)]">
          Test Result{(busy || running || debugging) && <Loader2 className="ml-1 size-3.5 animate-spin" />}
        </Tab>
        {detail && detailDock === "test" && (<><Sep />{detailTabEl(bottomTab === "detail", () => setBottomTab("detail"))}</>)}
      </TabBar>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {bottomTab === "cases" && <Testcases editable={editable} cases={cases} setCases={setCases} defaults={defaultCases} sel={caseSel} setSel={setCaseSel} />}
        {bottomTab === "result" && <TestResult r={result} error={error} busy={busy || running || debugging} note={waitNote} />}
        {bottomTab === "detail" && detail && detailView}
      </div>
      </>)}
    </Panel>
  );

  return (
    <div className="lc-shell">
      {/* ---------- thanh trên ---------- */}
      <TopBar
        nav={nav} problemId={problemId} router={router} busy={busy} running={running} debugging={debugging} onRun={() => run()} onDebug={debugRun} onSubmit={submit}
        noteOpen={noteOpen} onNote={toggleNote} onList={() => setDrawer(true)} onShuffle={shuffle}
        layouts={<LayoutsMenu layout={settings.layout} onLayout={(l) => setSettings({ layout: l })} onFocus={toggleMax} focused={maximized} />}
        settingsBtn={<NavIcon label="Cài đặt" onClick={() => setSettingsOpen(true)}><Settings /></NavIcon>}
        clock={<Stopwatch ref={clockRef} problemId={problemId} examMinutes={examMinutes} difficulty={problem.difficulty} cfg={timerCfg} />}
        streak={streak} examDays={examDays} userName={user.name} onInvite={share}
      />
      <ProblemDrawer open={drawer} onClose={() => setDrawer(false)} list={nav.list} diffLabel={nav.diffLabel} currentId={problemId} />

      {/* ---------- các khung ---------- */}
      <div className="min-h-0 flex-1 px-2.5 pb-2.5">
        {leet ? (
          <PanelGroup key="leet" direction="horizontal" autoSaveId="nj-lc-leet2">
            {leftPanel}<Handle />{codePanel}<Handle />{testPanel}
          </PanelGroup>
        ) : (
          <PanelGroup key="default" direction="horizontal" autoSaveId="nj-lc-h2">
            {leftPanel}
            <Handle />
            <Panel id="right" order={2} ref={rightRef} defaultSize={70} minSize={30} collapsible collapsedSize={0}
              onCollapse={() => setRightCollapsed(true)} onExpand={() => setRightCollapsed(false)}>
              <PanelGroup direction="vertical" autoSaveId="nj-lc-v2">
                {codePanel}<Handle vertical />{testPanel}
              </PanelGroup>
            </Panel>
          </PanelGroup>
        )}
      </div>

      <SettingsDialog open={!!settingsOpen} initial={settingsOpen === "keys" ? "keys" : "layout"} onClose={() => setSettingsOpen(false)} settings={settings} set={setSettings}
        onResetLayout={resetLayout} timerCfg={timerCfg} setTimerCfg={setTimerCfg} />

      <ConfirmDialog open={!!confirm} message={confirm?.message} onCancel={() => setConfirm(null)} onConfirm={() => { confirm?.onOk(); setConfirm(null); }} />

      {toast && (
        <div role="status" className="fixed left-1/2 top-16 z-[70] -translate-x-1/2 rounded-lg bg-[var(--solid)] px-4 py-2 text-sm text-[var(--solid-text)] shadow-[var(--pop-shadow)]">
          {toast}
        </div>
      )}
    </div>
  );
}
