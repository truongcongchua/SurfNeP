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
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import {
  BookOpen, Bookmark, Lightbulb, Braces, Check, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Code2, Expand, FileText, History,
  Loader2, Lock, Maximize, Minimize, NotebookPen, PanelLeftOpen, RotateCcw, Settings, Shrink,
  SquareCheck, Terminal, X,
} from "lucide-react";
import { ProblemDrawer } from "@/components/problem-drawer";
import { cn } from "@/lib/utils";
import { cAssistOptions, setupCAssist } from "@/lib/c-intellisense";
import { TopBar, NavIcon } from "@/components/workspace/top-bar";
import { ConfirmDialog } from "@/components/workspace/confirm-dialog";
import { useLocal, useSettings } from "@/components/workspace/use-settings";
import { SettingsDialog } from "@/components/workspace/settings-dialog";
import { LayoutsMenu } from "@/components/workspace/layouts-menu";
import { Stopwatch } from "@/components/workspace/stopwatch";
import { NoteEditor } from "@/components/workspace/note-editor";
import { HintsPanel, KnowledgePanel } from "@/components/workspace/knowledge-panel";
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
function TabBar({ children, right, activeKey, onDropTab, dragging }) {
  const ref = useRef(null);
  const [over, setOver] = useState(false);
  useEffect(() => { if (!dragging) setOver(false); }, [dragging]);
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
    <div className={cn("group/bar flex h-9 shrink-0 items-center bg-[var(--panel-head)] pl-1.5 pr-1", over && "ring-2 ring-inset ring-[var(--accent)]")}
      onDragOver={dragging ? (e) => { e.preventDefault(); setOver(true); } : undefined}
      onDragLeave={dragging ? () => setOver(false) : undefined}
      onDrop={dragging ? (e) => { e.preventDefault(); setOver(false); onDropTab?.(); } : undefined}>
      <div ref={ref} style={{ maskImage: mask, WebkitMaskImage: mask }} className="tab-scroll relative flex min-w-0 flex-1 items-center overflow-x-auto">
        {children}
      </div>
      {/* Như LeetCode: nút phóng to / thu gọn chỉ hiện khi rê chuột lên thanh tab. */}
      {right && <div className="ml-1 flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover/bar:opacity-100 focus-within:opacity-100">{right}</div>}
    </div>
  );
}

// Tab kéo thả được (như LeetCode): kéo sang khung khác, hoặc thả lên một tab / thanh tab để chèn vào đúng chỗ.
function Tab({ active, onClick, icon: Icon, iconClass, children, onClose, onDragStart, onDragEnd, onDropBefore }) {
  return (
    <div className={cn("flex shrink-0 items-center", onDragStart && "cursor-grab active:cursor-grabbing")}
      draggable={!!onDragStart} onDragStart={onDragStart} onDragEnd={onDragEnd}
      onDragOver={onDropBefore ? (e) => e.preventDefault() : undefined}
      onDrop={onDropBefore ? (e) => { e.preventDefault(); e.stopPropagation(); onDropBefore(); } : undefined}>
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
      className="absolute inset-x-0 bottom-0 top-9 z-30 rounded-b-[inherit] bg-[color-mix(in_srgb,var(--panel)_55%,transparent)]"
    >
      {zone && <div className={cn("pointer-events-none absolute rounded-md border-2 border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_22%,transparent)] transition-all", ZONE_BOX[zone])} />}
      <span className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-md bg-[var(--panel)] px-3 py-1 text-sm text-[var(--title)] shadow-[var(--pop-shadow)]">
        {zone && zone !== "center" ? `Tách ${{ left: "sang trái", right: "sang phải", top: "lên trên", bottom: "xuống dưới" }[zone]}` : label}
      </span>
    </div>
  );
}

/* ---------- bố cục tab (dock) ---------- */

// Mọi tab đều kéo thả được giữa các khung. Lưu trong localStorage:
//  assign[tab] = khung chứa tab (left | code | test | extra), order = thứ tự tab, extra = khung tách riêng {target, side}.
const ORDER = ["desc", "hint", "know", "subs", "detail", "note", "code", "cases", "result"];
const HOME = { desc: "left", hint: "left", know: "left", subs: "left", detail: "left", note: "left", code: "code", cases: "test", result: "test" };
const PANEL_IDS = ["left", "code", "test", "extra"];
const SIDES = ["left", "right", "top", "bottom"];
const DOCK_KEY = "nj-dock-v3";
const PANEL_NAME = { left: "khung đề bài", code: "khung Code", test: "khung Testcase", extra: "khung này" };

function normalizeDock(raw) {
  const assign = {};
  for (const [k, v] of Object.entries(raw?.assign || {})) if (ORDER.includes(k) && PANEL_IDS.includes(v)) assign[k] = v;
  const saved = Array.isArray(raw?.order) ? raw.order.filter((id) => ORDER.includes(id)) : [];
  const order = [...new Set([...saved, ...ORDER])];
  const e = raw?.extra;
  const extra = e && ["left", "code", "test"].includes(e.target) && SIDES.includes(e.side) ? { target: e.target, side: e.side } : { target: "left", side: "right" };
  return { assign, order, extra };
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

export default function Workspace({ problemId, problem, nav, user, samples, html, knowledge = [], hints = [], bugs = [], starter, originalStarter, examMinutes, history, stats, similar, lastSubmitted, social, streak, examDays }) {
  const router = useRouter();
  const [settings, setSettings] = useSettings();
  const [timerCfg, setTimerCfg] = useLocal("nj-timer-cfg", { byDifficulty: false, autoReset: false, alarm: false });
  const [code, setCodeState] = useState(starter);
  // Monaco chạy "không điều khiển" (defaultValue): nếu truyền value={code} thì khi gõ nhanh, React render
  // trễ một nhịp và ghi đè nội dung cũ lên editor -> mất chữ, con trỏ nhảy. setCode chỉ dùng cho thay đổi
  // từ bên ngoài (nạp nháp, reset, lấy code đã nộp) và đẩy thẳng vào editor.
  const editorRef = useRef(null);
  const editorTextRef = useRef(starter);
  const setCode = useCallback((t) => {
    editorTextRef.current = t; setCodeState(t);
    const ed = editorRef.current;
    if (ed && ed.getValue() !== t) ed.setValue(t);
  }, []);
  const [saved, setSaved] = useState(true);
  const [pos, setPos] = useState({ ln: 1, col: 1 });
  const [busy, setBusy] = useState(false);       // đang nộp bài
  const [running, setRunning] = useState(false); // đang chạy thử
  const [debugging, setDebugging] = useState(false);
  const [error, setError] = useState("");
  const [waitNote, setWaitNote] = useState("");
  const [result, setResult] = useState(null);    // kết quả CHẠY THỬ (Test Result). Kết quả nộp bài nằm ở tab bài nộp.
  const [past, setPast] = useState(history);
  const [lastCode, setLastCode] = useState(lastSubmitted);
  const [detail, setDetail] = useState(null);    // bài nộp đang xem: tab "Accepted / Wrong Answer…" cạnh Đề bài
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useLocal(`nj-note-${problemId}`, "");
  const [soc, setSoc] = useState(social); // { likes, mine, favorite } — lưu trên máy chủ
  const [confirm, setConfirm] = useState(null); // { message, onOk }
  const [langMenu, setLangMenu] = useState(false);
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

  // Bố cục tab: tab nào nằm ở khung nào, tab nào đang mở trong mỗi khung.
  const [rawDock, setRawDock] = useLocal(DOCK_KEY, null);
  const dock = useMemo(() => normalizeDock(rawDock), [rawDock]);
  const dockRef = useRef(dock);
  dockRef.current = dock;
  const [activeIn, setActiveIn] = useState({ left: "desc", code: "code", test: "cases", extra: null });
  const [dragId, setDragId] = useState(null);

  const valid = { desc: true, hint: hints.length > 0, know: knowledge.length > 0, subs: true, detail: !!detail, note: noteOpen, code: true, cases: true, result: true };
  const panelOf = (id) => dock.assign[id] ?? HOME[id];
  const tabsIn = (p) => dock.order.filter((id) => valid[id] && panelOf(id) === p);
  const activeOf = (p) => { const t = tabsIn(p); return t.includes(activeIn[p]) ? activeIn[p] : t[0]; };
  const isActive = (id) => activeOf(panelOf(id)) === id;

  // Testcase sửa được (bài stdio/function): mặc định = input của test mẫu.
  const editable = problem.type === "stdio" || problem.type === "function";
  const defaultCases = samples.length ? samples.map((s) => s.input.replace(/\s+$/, "")) : [""];
  const [cases, setCases] = useLocal(`nj-cases-${problemId}`, defaultCases);
  const [caseSel, setCaseSel] = useState(0);

  const flash = useCallback((msg) => { setToast(msg); setTimeout(() => setToast(""), 2600); }, []);

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

  // Chọn tab `id` (ở khung đang chứa nó) và mở khung đó ra nếu đang thu gọn.
  function activate(id) {
    const d = dockRef.current;
    const p = d.assign[id] ?? HOME[id];
    setActiveIn((a) => ({ ...a, [p]: id }));
    const host = p === "extra" ? d.extra.target : p;
    const ref = { left: leftRef, code: codeRef, test: bottomRef }[host];
    if (!leet && host !== "left" && rightRef.current?.isCollapsed()) rightRef.current.expand();
    if (ref?.current?.isCollapsed()) ref.current.expand();
  }

  // Kéo thả tab: zone = center (nhập vào khung làm tab) hoặc left|right|top|bottom (tách thành khung riêng ở mép đó).
  // beforeId = chèn trước tab đó (thả lên thanh tab).
  function moveTab(id, panel, zone, beforeId) {
    setDragId(null);
    if (!id) return;
    const split = zone && zone !== "center" && panel !== "extra";
    const dest = split ? "extra" : panel;
    setRawDock((cur) => {
      const d = normalizeDock(cur);
      const assign = { ...d.assign, [id]: dest };
      const order = d.order.filter((x) => x !== id);
      const at = beforeId && beforeId !== id ? order.indexOf(beforeId) : -1;
      if (at >= 0) order.splice(at, 0, id); else order.push(id);
      return { assign, order, extra: split ? { target: panel, side: zone } : d.extra };
    });
    setActiveIn((a) => ({ ...a, [dest]: id }));
    const host = split ? panel : panel === "extra" ? dockRef.current.extra.target : panel;
    if (!leet && host !== "left" && rightRef.current?.isCollapsed()) rightRef.current.expand();
    const hostRef = { left: leftRef, code: codeRef, test: bottomRef }[host];
    if (hostRef?.current?.isCollapsed()) hostRef.current.expand();
  }

  async function submit() {
    if (busy || running || debugging) return;
    setBusy(true); setError("");
    let id;
    try {
      const res = await fetch("/api/submit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ problemId, code }) });
      const data = await res.json();
      if (!res.ok) { flash(data.error || "Lỗi khi nộp bài"); setBusy(false); return; }
      id = data.id;
    } catch { flash("Không kết nối được máy chủ"); setBusy(false); return; }
    setLastCode(code);
    const created = Math.floor(Date.now() / 1000);
    setPast((h) => [{ id, status: "queued", created }, ...h].slice(0, 30));
    // Kết quả nộp bài hiện ở tab bài nộp (cạnh Đề bài), không phải ở Test Result.
    setDetail({ id, status: "queued", created, code, result: null });
    activate("detail");
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      let s;
      try { s = await (await fetch(`/api/submissions/${id}`)).json(); } catch { continue; }
      if (s.status === "done") {
        setDetail((d) => (!d || d.id === id ? { id, ...s } : d));
        setPast((h) => h.map((x) => x.id === id ? { ...x, status: "done", verdict: s.verdict, passed: s.result?.passed, total: s.result?.total } : x));
        if (s.verdict === "AC") clockRef.current?.onAccepted();
        break;
      }
      setDetail((d) => (d && d.id === id ? { ...d, ...s } : d));
      setWaitNote(s.status === "queued" && s.position > 0 ? `Đang xếp hàng — vị trí ${s.position}` : "");
      if (s.status === "running") setPast((h) => h.map((x) => x.id === id ? { ...x, status: "running" } : x));
    }
    setWaitNote("");
    setBusy(false);
  }

  // Chạy thử: bài stdio/function chạy đúng các testcase trong khung Testcase (output mong đợi lấy từ lời giải mẫu);
  // bài client/server chạy test mẫu. Không tính là một lần nộp. Kết quả hiện ở tab Test Result.
  async function run(debug = false) {
    if (busy || running || debugging) return;
    (debug ? setDebugging : setRunning)(true); setError(""); setResult(null); activate("result");
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

  function closeDetail() {
    const p = panelOf("detail");
    setDetail(null);
    if (panelOf("subs") === p) setActiveIn((a) => ({ ...a, [p]: "subs" }));
  }
  function closeNote() { setNoteOpen(false); }

  async function openSubmission(id) {
    setDetail({ id }); activate("detail");
    try {
      const s = await (await fetch(`/api/submissions/${id}`)).json();
      setDetail((d) => (d?.id === id ? { id, ...s } : d));
    } catch { flash("Không tải được bài nộp"); }
  }

  // "Use Testcase": thêm input của test bị sai vào khung Testcase (nếu chưa có), chọn nó và chuyển sang tab Testcase.
  function useCase(input) {
    const v = String(input ?? "").replace(/\s+$/, "");
    const at = cases.indexOf(v);
    if (at >= 0) setCaseSel(at);
    else if (cases.length >= 10) { flash("Đã đủ 10 testcase, hãy xoá bớt một case rồi thử lại"); return; }
    else { setCases([...cases, v]); setCaseSel(cases.length); }
    activate("cases");
    flash(at >= 0 ? `Testcase này đã có (Case ${at + 1})` : "Đã thêm vào khung Testcase");
  }

  function loadIntoEditor() {
    if (!detail?.code) return;
    setCode(detail.code); setError("");
    activate("code");
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
    if (detail && isActive("detail")) closeDetail();
    else if (noteOpen && isActive("note")) closeNote();
  }
  function toggleNote() {
    if (noteOpen && isActive("note")) { closeNote(); return; }
    setNoteOpen(true); activate("note");
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
    try {
      Object.keys(localStorage).filter((k) => k.startsWith("react-resizable-panels:nj-")).forEach((k) => localStorage.removeItem(k));
      localStorage.removeItem(DOCK_KEY);
    } catch {}
    location.reload();
  }

  // Phím tắt (giống LeetCode). Trong Monaco đăng ký riêng ở onMount để editor không nuốt phím.
  const keys = useRef({});
  keys.current = { run: () => run(), submit, toggleMax, toggleFullscreen, closeActiveTab, settings };
  const assistRef = useRef(null);
  useEffect(() => { assistRef.current?.refresh(); }, [settings.lint]);
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
    editorRef.current = editor;
    // Monaco đo bề rộng ký tự lúc mount; nếu font chưa nạp xong (hoặc màn hình có tỉ lệ thu phóng lẻ) thì vùng chọn/con trỏ
    // lệch khỏi chữ. Đo lại khi font sẵn sàng và khi cửa sổ đổi kích thước/tỉ lệ.
    const remeasure = () => monaco.editor.remeasureFonts();
    document.fonts?.ready.then(remeasure);
    remeasure();
    window.addEventListener("resize", remeasure);
    editor.onDidDispose(() => window.removeEventListener("resize", remeasure));
    if (editor.getValue() !== editorTextRef.current) editor.setValue(editorTextRef.current);
    editor.onDidChangeCursorPosition((e) => setPos({ ln: e.position.lineNumber, col: e.position.column }));
    // Gợi ý code C: provider đọc cài đặt hiện tại qua keys.current nên bật/tắt có hiệu lực ngay.
    const assist = setupCAssist(monaco, editor, () => keys.current.settings);
    assistRef.current = assist;
    editor.onDidDispose(() => { assist.dispose(); assistRef.current = null; });
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
  const detailPending = !!detail && detail.status && detail.status !== "done";
  const verdictTab = detailPending ? "Đang chấm…" : detail?.verdict ? LABEL[detail.verdict] || detail.verdict : "Bài nộp";
  const acCount = past.filter((s) => s.verdict === "AC").length;

  /* ----- tab: nhãn + nội dung ----- */

  const TABS = {
    desc: { label: "Đề bài", icon: FileText, cls: "text-[var(--accent)]" },
    hint: { label: "Gợi ý", icon: Lightbulb, cls: "text-[var(--brand)]" },
    know: { label: "Kiến thức", icon: BookOpen, cls: "text-[var(--accent)]" },
    subs: { label: "Lịch sử nộp", icon: History, cls: "text-[var(--accent)]" },
    detail: { label: verdictTab, icon: History, cls: detailPending ? "text-[var(--muted)]" : detail?.verdict === "AC" ? "text-[var(--green)]" : detail?.verdict ? "text-[var(--hard)]" : "text-[var(--accent)]", close: closeDetail },
    note: { label: "Ghi chú", icon: NotebookPen, cls: "text-[var(--brand)]", close: closeNote },
    code: { label: "Code", icon: Code2, cls: "text-[var(--green)]" },
    cases: { label: "Testcase", icon: SquareCheck, cls: "text-[var(--green)]" },
    result: { label: <>Test Result{(running || debugging) && <Loader2 className="ml-1 size-3.5 animate-spin" />}</>, icon: Terminal, cls: "text-[var(--green)]" },
  };

  const bodyOf = (id) => {
    switch (id) {
      case "desc": return <Description problem={problem} html={html} solved={acCount > 0} stats={stats} similar={similar} />;
      case "hint": return <HintsPanel problemId={problemId} hints={hints} />;
      case "know": return <KnowledgePanel cards={knowledge} />;
      case "subs": return <SubmissionList past={past} onOpen={openSubmission} />;
      case "detail": return (
        <SubmissionDetail bugs={bugs} sub={detail?.code != null ? detail : null} user={user} note={waitNote}
          onBack={() => activate("subs")} onLoad={loadIntoEditor} onUseCase={editable ? useCase : undefined} />
      );
      case "note": return <NoteEditor value={note} onChange={setNote} />;
      case "cases": return <Testcases editable={editable} cases={cases} setCases={setCases} defaults={defaultCases} sel={caseSel} setSel={setCaseSel} />;
      case "result": return <TestResult r={result} error={error} busy={running || debugging} note={waitNote} />;
      default: return null;
    }
  };

  // Tab Code luôn gắn vào cây DOM (chỉ ẩn khi không được chọn) để không mất vị trí con trỏ / lịch sử hoàn tác khi đổi tab.
  const codeView = (active) => (
    <div ref={codeBox} className={cn("flex min-h-0 flex-1 flex-col bg-[var(--panel)]", !active && "hidden")}>
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
          height="100%" language="c" defaultValue={editorTextRef.current}
          theme={resolvedTheme === "dark" ? "nj-dark" : "nj-light"}
          beforeMount={defineThemes} onMount={onEditorMount}
          onChange={(v) => { editorTextRef.current = v ?? ""; setCodeState(v ?? ""); }}
          options={{
            minimap: { enabled: false }, fontSize: settings.fontSize, lineHeight: Math.round(settings.fontSize * 1.55),
            fontFamily: "Menlo, Monaco, Consolas, 'Courier New', monospace", fontLigatures: settings.ligatures,
            letterSpacing: 0, disableMonospaceOptimizations: true, fontVariations: false,
            tabSize: settings.tabSize, wordWrap: settings.wordWrap ? "on" : "off",
            lineNumbers: settings.relativeLines ? "relative" : "on", cursorBlinking: settings.noCursorBlink ? "solid" : "blink",
            scrollBeyondLastLine: false, automaticLayout: true, padding: { top: 8 },
            lineNumbersMinChars: 3, renderLineHighlight: "line", scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
            ...cAssistOptions(settings),
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
  );

  // Nút phóng to / thu gọn bên phải thanh tab của từng khung.
  const panelRight = (p) => {
    if (p === "left") return (<>
      <IconBtn label={rightCollapsed ? "Thu nhỏ" : "Phóng to"} onClick={toggleLeftMax}>{rightCollapsed ? <Minimize className="size-4" /> : <Maximize className="size-4" />}</IconBtn>
      {!rightCollapsed && <IconBtn label="Thu gọn" onClick={() => leftRef.current?.collapse()}><ChevronLeft className="size-4" /></IconBtn>}
    </>);
    if (p === "code") return (<>
      {leftCollapsed && !maximized && <IconBtn label="Mở khung đề bài" onClick={() => leftRef.current?.expand()}><PanelLeftOpen className="size-4" /></IconBtn>}
      <IconBtn label={maximized ? "Thu nhỏ (Alt+=)" : "Phóng to (Alt+=)"} onClick={toggleMax}>{maximized ? <Minimize className="size-4" /> : <Maximize className="size-4" />}</IconBtn>
    </>);
    if (p === "test") return (<>
      <IconBtn label={testMax ? "Thu nhỏ" : "Phóng to"} onClick={toggleTestMax}>{testMax ? <Minimize className="size-4" /> : <Maximize className="size-4" />}</IconBtn>
      <IconBtn label="Thu gọn" onClick={() => bottomRef.current?.collapse()}>{leet ? <ChevronRight className="size-4" /> : <ChevronDown className="size-4" />}</IconBtn>
    </>);
    return null;
  };

  // Một khung: thanh tab (kéo thả được) + nội dung tab đang chọn.
  const renderPanel = (p) => {
    const tabs = tabsIn(p), act = activeOf(p);
    return (
      <>
        <DropOverlay show={dragId != null} label={`Thả vào ${PANEL_NAME[p]}`} onDrop={(zone) => moveTab(dragId, p, zone)} />
        <TabBar activeKey={`${act}|${tabs.join(",")}`} right={panelRight(p)} dragging={dragId != null} onDropTab={() => moveTab(dragId, p, "center")}>
          {tabs.map((id, i) => {
            const t = TABS[id];
            return (
              <Fragment key={id}>
                {i > 0 && <Sep />}
                <Tab active={id === act} onClick={() => setActiveIn((a) => ({ ...a, [p]: id }))} icon={t.icon} iconClass={t.cls} onClose={t.close}
                  onDragStart={(e) => { e.dataTransfer.setData("text/plain", `nj-tab:${id}`); e.dataTransfer.effectAllowed = "move"; setTimeout(() => setDragId(id), 0); }}
                  onDragEnd={() => setDragId(null)}
                  onDropBefore={dragId && dragId !== id ? () => moveTab(dragId, p, "center", id) : undefined}>
                  {t.label}
                </Tab>
              </Fragment>
            );
          })}
        </TabBar>
        {tabs.includes("code") && codeView(act === "code")}
        {act !== "code" && <div className="min-h-0 flex-1 overflow-y-auto">{bodyOf(act)}</div>}
        {act === "desc" && (
          <DescFooter likes={soc.likes} mine={soc.mine} favorite={soc.favorite} onLike={(v) => sendReact({ like: v })} onFavorite={(v) => sendReact({ favorite: v })}
            onShare={share} onHelp={() => setSettingsOpen("keys")} />
        )}
      </>
    );
  };

  /* ----- các khung ----- */

  const extra = dock.extra;
  const extraHas = tabsIn("extra").length > 0;
  const has = (p) => tabsIn(p).length > 0 || (extraHas && extra.target === p);

  // Khung `target`; nếu có khung tách riêng (thả tab vào mép) thì đặt cạnh nó ở phía `extra.side`.
  const wrap = (target) => {
    if (!(extraHas && extra.target === target)) return <div className="lc-panel h-full">{renderPanel(target)}</div>;
    if (tabsIn(target).length === 0) return <div className="lc-panel h-full">{renderPanel("extra")}</div>;
    const horizontal = extra.side === "left" || extra.side === "right";
    const first = extra.side === "left" || extra.side === "top";
    const side = (
      <Panel key="extra" id="extra" order={first ? 1 : 2} defaultSize={40} minSize={15}>
        <div className="lc-panel h-full">{renderPanel("extra")}</div>
      </Panel>
    );
    const main = (
      <Panel key="main" id="main" order={first ? 2 : 1} defaultSize={60} minSize={15}>
        <div className="lc-panel h-full">{renderPanel(target)}</div>
      </Panel>
    );
    return (
      <PanelGroup key={`${target}:${extra.side}`} direction={horizontal ? "horizontal" : "vertical"}>
        {first ? [side, <Handle key="h" vertical={!horizontal} />, main] : [main, <Handle key="h" vertical={!horizontal} />, side]}
      </PanelGroup>
    );
  };

  // Khung nào rỗng (đã kéo hết tab đi) thì ẩn; kích thước các khung còn lại quy về tổng 100%.
  const share100 = (ids, base) => { const sum = ids.reduce((a, i) => a + base[i], 0); return Object.fromEntries(ids.map((i) => [i, (base[i] / sum) * 100])); };
  const join = (items, vertical) => items.flatMap((x, i) => (i ? [<Handle key={`h${i}`} vertical={vertical} />, x] : [x]));
  const sig = ["left", "code", "test"].map((p) => (has(p) ? 1 : 0)).join("");
  useEffect(() => { // khung biến mất thì không còn sự kiện thu gọn: đặt lại cờ
    setLeftCollapsed(false); setBottomCollapsed(false); setRightCollapsed(false); setCodeCollapsed(false);
  }, [sig, leet]);

  const mkLeft = (size) => (
    <Panel key="left" id="left" order={1} ref={leftRef} defaultSize={size} minSize={20} collapsible collapsedSize={0}
      onCollapse={() => setLeftCollapsed(true)} onExpand={() => setLeftCollapsed(false)}>
      {wrap("left")}
    </Panel>
  );
  const mkCode = (size) => (
    <Panel key="code" id="code" order={2} ref={codeRef} defaultSize={size} minSize={15} collapsible collapsedSize={0}
      onCollapse={() => setCodeCollapsed(true)} onExpand={() => setCodeCollapsed(false)}>
      {wrap("code")}
    </Panel>
  );
  const mkTest = (size) => (
    <Panel key="test" id="test" order={3} ref={bottomRef} defaultSize={size} minSize={12} collapsible collapsedSize={0}
      onCollapse={() => setBottomCollapsed(true)} onExpand={() => setBottomCollapsed(false)}>
      {wrap("test")}
    </Panel>
  );

  let layoutEl = null;
  if (leet) {
    const ids = ["left", "code", "test"].filter(has);
    const sz = share100(ids, { left: 33, code: 40, test: 27 });
    const mk = { left: mkLeft, code: mkCode, test: mkTest };
    layoutEl = ids.length ? <PanelGroup key={`leet-${sig}`} direction="horizontal" autoSaveId={`nj-lc-leet2-${sig}`}>{join(ids.map((i) => mk[i](sz[i])))}</PanelGroup> : null;
  } else {
    const rids = ["code", "test"].filter(has);
    const rsz = share100(rids, { code: 55, test: 45 });
    const mk = { code: mkCode, test: mkTest };
    const rightEl = rids.length ? (
      <Panel key="right" id="right" order={2} ref={rightRef} defaultSize={has("left") ? 70 : 100} minSize={30} collapsible collapsedSize={0}
        onCollapse={() => setRightCollapsed(true)} onExpand={() => setRightCollapsed(false)}>
        <PanelGroup key={`v-${sig}`} direction="vertical" autoSaveId={`nj-lc-v2-${sig}`}>{join(rids.map((i) => mk[i](rsz[i])), true)}</PanelGroup>
      </Panel>
    ) : null;
    const cols = [has("left") ? mkLeft(rids.length ? 30 : 100) : null, rightEl].filter(Boolean);
    layoutEl = cols.length ? <PanelGroup key={`default-${sig}`} direction="horizontal" autoSaveId={`nj-lc-h2-${sig}`}>{join(cols)}</PanelGroup> : null;
  }

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
      <div className="min-h-0 flex-1 px-2.5 pb-2.5">{layoutEl}</div>

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
