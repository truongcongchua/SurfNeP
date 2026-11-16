"use client";
// Đồng hồ trên thanh trên như LeetCode:
//  - Chưa chạy: icon đồng hồ; bấm mở bảng chọn "Bấm giờ" (đếm lên) hoặc "Hẹn giờ" (đếm ngược, chọn giờ/phút) rồi Bắt đầu.
//  - Đang chạy: [‹ ẩn] [▶/❚❚ thời gian] [↻ đặt lại] [⋮ menu: đổi chế độ / dừng hẳn].
//  - Bấm ‹ thì thu gọn chỉ còn icon; bấm icon lại hiện.
// Trạng thái lưu theo từng bài trong localStorage nên tải lại trang vẫn chạy tiếp.
// Bài thi thử (examMinutes) mặc định là Hẹn giờ với đúng số phút của đề.
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { AlarmClock, ChevronLeft, EllipsisVertical, Pause, Play, RefreshCw, Timer } from "lucide-react";
import { cn } from "@/lib/utils";

const DIFF_MIN = { easy: 20, medium: 40, hard: 60 };
const fmt = (sec) => {
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  return (h ? `${h}:` : "") + `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
};

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
    g.gain.setValueAtTime(0.2, ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
    o.start(); o.stop(ctx.currentTime + 0.8);
  } catch {}
}

// st: { mode: "stopwatch"|"timer", total (giây, timer), acc (giây đã trôi trước lần chạy gần nhất), since (ms|null), hidden }
export const Stopwatch = forwardRef(function Stopwatch({ problemId, examMinutes, difficulty, cfg }, ref) {
  const key = `nj-clock-${problemId}`;
  const [st, setSt] = useState(null);
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [tab, setTab] = useState(examMinutes ? "timer" : "stopwatch");
  const defMin = examMinutes || (cfg.byDifficulty ? DIFF_MIN[difficulty] : 30);
  const [hh, setHh] = useState(Math.floor(defMin / 60));
  const [mm, setMm] = useState(defMin % 60);
  const [, tick] = useState(0);
  const warned = useRef({});
  const box = useRef(null);

  useEffect(() => {
    try { setSt(JSON.parse(localStorage.getItem(key) || "null")); } catch {}
    // tương thích đồng hồ thi thử cũ (nj-exam-<id> = mốc bắt đầu)
    try {
      const old = Number(localStorage.getItem(`nj-exam-${problemId}`));
      if (old && examMinutes && !localStorage.getItem(key)) save({ mode: "timer", total: examMinutes * 60, acc: 0, since: old, hidden: false });
    } catch {}
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = useCallback((v) => {
    setSt(v);
    try { v ? localStorage.setItem(key, JSON.stringify(v)) : localStorage.removeItem(key); } catch {}
  }, [key]);

  const elapsed = st ? st.acc + (st.since ? (Date.now() - st.since) / 1000 : 0) : 0;
  const shown = st?.mode === "timer" ? st.total - elapsed : elapsed;
  const running = !!st?.since;

  useEffect(() => {
    if (!running) return;
    const h = setInterval(() => tick((x) => x + 1), 500);
    return () => clearInterval(h);
  }, [running]);

  // Hẹn giờ: hết giờ thì dừng; chuông báo khi còn 10 phút và khi hết.
  useEffect(() => {
    if (st?.mode !== "timer" || !running) return;
    if (cfg.alarm && shown <= 600 && shown > 590 && !warned.current.ten) { warned.current.ten = true; beep(); }
    if (shown <= 0) {
      save({ ...st, acc: st.total, since: null });
      if (cfg.alarm) beep();
    }
  });

  // Đóng bảng/menu khi bấm ra ngoài.
  useEffect(() => {
    if (!open && !menu) return;
    const h = (e) => { if (!box.current?.contains(e.target)) { setOpen(false); setMenu(false); } };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open, menu]);

  const start = () => {
    warned.current = {};
    const total = (Number(hh) * 60 + Number(mm)) * 60;
    save(tab === "timer" ? { mode: "timer", total: Math.max(60, total), acc: 0, since: Date.now(), hidden: false } : { mode: "stopwatch", acc: 0, since: Date.now(), hidden: false });
    setOpen(false);
  };
  const toggle = () => save(running ? { ...st, acc: elapsed, since: null } : { ...st, since: Date.now() });
  const reset = () => { warned.current = {}; save({ ...st, acc: 0, since: running ? Date.now() : null }); };

  // Workspace gọi khi bài nộp Accepted (tuỳ chọn "Tự đặt lại").
  useImperativeHandle(ref, () => ({ onAccepted: () => { if (cfg.autoReset && st) reset(); } }));

  if (st === null || st.hidden) {
    return (
      <div ref={box} className="relative">
        <button onClick={() => (st?.hidden ? save({ ...st, hidden: false }) : setOpen((v) => !v))} title={st?.hidden ? "Hiện đồng hồ" : "Đồng hồ"} aria-label="Đồng hồ"
          className={cn("inline-flex size-8 items-center justify-center rounded-lg hover:bg-[var(--fill-3)]", st?.hidden ? "text-[var(--accent)]" : "text-[var(--icon-nav)] hover:text-[var(--title)]")}>
          <AlarmClock className="size-4" />
        </button>
        {open && (
          <div className="absolute right-0 top-10 z-50 w-64 rounded-lg bg-[var(--panel)] p-3 shadow-[var(--pop-shadow)]">
            <div className="mb-3 grid grid-cols-2 gap-1 rounded-lg bg-[var(--chip)] p-0.5">
              {[["stopwatch", "Bấm giờ"], ["timer", "Hẹn giờ"]].map(([k, t]) => (
                <button key={k} onClick={() => setTab(k)} className={cn("h-7 rounded-md text-xs", tab === k ? "bg-[var(--panel)] font-medium text-[var(--title)] shadow-sm" : "text-[var(--muted)]")}>{t}</button>
              ))}
            </div>
            {tab === "stopwatch" ? (
              <div className="mb-3 flex flex-col items-center gap-1 py-3 text-[var(--muted)]"><Timer className="size-8" /><span className="text-xs">Đếm thời gian làm bài</span></div>
            ) : (
              <div className="mb-3 flex items-center justify-center gap-2 py-2">
                <input type="number" min="0" max="9" value={hh} onChange={(e) => setHh(e.target.value)} aria-label="Giờ"
                  className="h-10 w-14 rounded-md border-0 bg-[var(--chip)] text-center text-lg text-[var(--title)] outline-none" />
                <span className="text-xs text-[var(--muted)]">giờ</span>
                <input type="number" min="0" max="59" value={mm} onChange={(e) => setMm(e.target.value)} aria-label="Phút"
                  className="h-10 w-14 rounded-md border-0 bg-[var(--chip)] text-center text-lg text-[var(--title)] outline-none" />
                <span className="text-xs text-[var(--muted)]">phút</span>
              </div>
            )}
            <button onClick={start} className="h-8 w-full rounded-md bg-[var(--accent)] text-sm font-medium text-white hover:opacity-90">Bắt đầu</button>
          </div>
        )}
      </div>
    );
  }

  const over = st.mode === "timer" && shown <= 0;
  const seg = "flex h-6 items-center justify-center text-[var(--icon)] hover:text-[var(--title)]";
  return (
    <div ref={box} className="relative flex h-8 items-center rounded-lg bg-[var(--fill-3)] pl-1">
      <button onClick={() => save({ ...st, hidden: true })} title="Ẩn" aria-label="Ẩn đồng hồ" className={cn(seg, "w-4")}><ChevronLeft className="size-3.5" /></button>
      <button onClick={toggle} title={running ? "Tạm dừng" : "Tiếp tục"} aria-label={running ? "Tạm dừng" : "Tiếp tục"}
        className="flex h-6 items-center gap-1.5 px-1 text-[var(--icon)] hover:text-[var(--title)]">
        {running ? <Pause className="size-3.5 fill-current" /> : <Play className="size-3.5 fill-current" />}
        <span className={cn("select-none text-sm tabular-nums", over ? "text-[var(--hard)]" : "text-[var(--blue-time)]")}>{fmt(shown)}</span>
      </button>
      <div className="mx-1 flex h-6 items-center rounded-[5px] bg-[var(--fill-3)]">
        <button onClick={reset} title="Đặt lại" aria-label="Đặt lại đồng hồ" className={cn(seg, "w-6")}><RefreshCw className="size-3.5" /></button>
        <span className="h-3.5 w-px bg-[var(--div)]" />
        <button onClick={() => setMenu((v) => !v)} title="Thêm" aria-label="Thêm tuỳ chọn đồng hồ" className={cn(seg, "w-6")}><EllipsisVertical className="size-3.5" /></button>
      </div>
      {menu && (
        <div className="absolute right-0 top-10 z-50 w-44 rounded-lg bg-[var(--panel)] p-1 text-sm shadow-[var(--pop-shadow)]">
          <button onClick={() => { setMenu(false); save(null); setTab(st.mode === "timer" ? "stopwatch" : "timer"); setOpen(true); }}
            className="flex h-8 w-full items-center rounded px-2 text-left hover:bg-[var(--raised)]">{st.mode === "timer" ? "Chuyển sang Bấm giờ" : "Chuyển sang Hẹn giờ"}</button>
          <button onClick={() => { setMenu(false); save(null); }} className="flex h-8 w-full items-center rounded px-2 text-left text-[var(--hard)] hover:bg-[var(--raised)]">Dừng đồng hồ</button>
        </div>
      )}
    </div>
  );
});
