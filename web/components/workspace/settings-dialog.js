"use client";
// Hộp Settings kiểu LeetCode: cột trái chọn nhóm (Bố cục · Trình soạn thảo · Phím tắt · Đồng hồ), bên phải là tuỳ chọn.
// Đóng bằng nút X, phím Esc hoặc bấm ra ngoài.
import { useEffect, useState } from "react";
import { Code2, Keyboard, LayoutPanelLeft, Timer, X } from "lucide-react";
import { cn } from "@/lib/utils";

const GROUPS = [
  ["layout", "Bố cục", LayoutPanelLeft],
  ["editor", "Trình soạn thảo", Code2],
  ["keys", "Phím tắt", Keyboard],
  ["timer", "Đồng hồ", Timer],
];

function Toggle({ on, onChange, label }) {
  return (
    <button role="switch" aria-checked={on} aria-label={label} onClick={() => onChange(!on)}
      className={cn("relative h-5 w-9 shrink-0 rounded-full transition-colors", on ? "bg-[var(--accent)]" : "bg-[var(--line-strong)]")}>
      <span className={cn("absolute top-0.5 size-4 rounded-full bg-white shadow transition-transform", on ? "translate-x-[18px]" : "translate-x-0.5")} />
    </button>
  );
}

function Select({ value, options, onChange, label }) {
  return (
    <select value={value} aria-label={label} onChange={(e) => onChange(e.target.value)}
      className="h-8 min-w-28 cursor-pointer rounded-md border-0 bg-[var(--chip)] px-2.5 text-sm text-[var(--text)] outline-none">
      {options.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
    </select>
  );
}

const Row = ({ label, desc, children }) => (
  <div className="flex items-center justify-between gap-6 py-2.5">
    <div><div className="text-sm text-[var(--title)]">{label}</div>{desc && <div className="mt-0.5 text-xs text-[var(--muted)]">{desc}</div>}</div>
    {children}
  </div>
);

const Kbd = ({ children }) => <kbd className="inline-flex h-6 min-w-6 items-center justify-center rounded border border-[var(--line)] px-1.5 font-sans text-xs text-[var(--text)]">{children}</kbd>;

export function SettingsDialog({ open, initial = "layout", onClose, settings, set, onResetLayout, timerCfg, setTimerCfg }) {
  const [g, setG] = useState(initial);
  useEffect(() => { if (open) setG(initial); }, [open, initial]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-black/40 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-label="Cài đặt" className="flex h-[min(460px,90vh)] w-[min(780px,100%)] overflow-hidden rounded-xl bg-[var(--panel)] shadow-[var(--pop-shadow)]">
        <nav className="w-44 shrink-0 bg-[var(--panel-head)] p-3 max-sm:hidden">
          <div className="mb-4 px-2 pt-1 text-lg font-medium text-[var(--title)]">Cài đặt</div>
          {GROUPS.map(([k, t, Icon]) => (
            <button key={k} onClick={() => setG(k)}
              className={cn("mb-1 flex h-9 w-full items-center gap-2 rounded-md px-2 text-sm", g === k ? "bg-[var(--chip)] text-[var(--title)]" : "text-[var(--muted)] hover:text-[var(--title)]")}>
              <Icon className="size-4" />{t}
            </button>
          ))}
        </nav>
        <div className="relative min-w-0 flex-1 overflow-y-auto px-6 pb-6 pt-12">
          <button onClick={onClose} aria-label="Đóng" className="absolute right-4 top-4 rounded-md p-1 text-[var(--muted)] hover:bg-[var(--raised)] hover:text-[var(--title)]"><X className="size-5" /></button>

          {g === "layout" && (
            <>
              <Row label="Bố cục mặc định" desc="Đưa kích thước các khung về như ban đầu.">
                <button onClick={onResetLayout} className="h-7 rounded-md bg-[var(--chip)] px-3 text-xs text-[var(--text)] hover:bg-[var(--pill)]">Đặt lại</button>
              </Row>
              <Row label="Kiểu bố cục">
                <Select label="Kiểu bố cục" value={settings.layout} onChange={(v) => set({ layout: v })} options={[["default", "Mặc định"], ["leet", "Leet (3 cột)"]]} />
              </Row>
            </>
          )}

          {g === "editor" && (
            <>
              <Row label="Cỡ chữ"><Select label="Cỡ chữ" value={settings.fontSize} onChange={(v) => set({ fontSize: Number(v) })} options={[12, 13, 14, 15, 16, 18, 20].map((n) => [n, `${n}px`])} /></Row>
              <Row label="Độ rộng tab"><Select label="Độ rộng tab" value={settings.tabSize} onChange={(v) => set({ tabSize: Number(v) })} options={[[2, "2 dấu cách"], [4, "4 dấu cách"], [8, "8 dấu cách"]]} /></Row>
              <div className="grid grid-cols-1 gap-x-10 sm:grid-cols-2">
                <Row label="Xuống dòng tự động"><Toggle label="Xuống dòng tự động" on={settings.wordWrap} onChange={(v) => set({ wordWrap: v })} /></Row>
                <Row label="Số dòng tương đối"><Toggle label="Số dòng tương đối" on={settings.relativeLines} onChange={(v) => set({ relativeLines: v })} /></Row>
                <Row label="Font ligatures"><Toggle label="Font ligatures" on={settings.ligatures} onChange={(v) => set({ ligatures: v })} /></Row>
                <Row label="Tắt nhấp nháy con trỏ"><Toggle label="Tắt nhấp nháy con trỏ" on={settings.noCursorBlink} onChange={(v) => set({ noCursorBlink: v })} /></Row>
              </div>
            </>
          )}

          {g === "keys" && (
            <>
              <div className="mb-1 text-xs font-medium text-[var(--muted)]">Chung</div>
              <Row label="Chạy thử"><span className="flex items-center gap-2"><Toggle label="Bật phím chạy thử" on={settings.runShortcut} onChange={(v) => set({ runShortcut: v })} /><Kbd>Ctrl</Kbd><Kbd>&apos;</Kbd></span></Row>
              <Row label="Nộp bài"><span className="flex items-center gap-2"><Toggle label="Bật phím nộp bài" on={settings.submitShortcut} onChange={(v) => set({ submitShortcut: v })} /><Kbd>Ctrl</Kbd><Kbd>Enter</Kbd></span></Row>
              <Row label="Phóng to / thu nhỏ khung code"><span className="flex gap-1"><Kbd>Alt</Kbd><Kbd>+</Kbd></span></Row>
              <Row label="Toàn màn hình khung code"><span className="flex gap-1"><Kbd>Alt</Kbd><Kbd>F</Kbd></span></Row>
              <Row label="Đóng tab đang mở (ghi chú, bài nộp)"><span className="flex gap-1"><Kbd>Alt</Kbd><Kbd>W</Kbd></span></Row>
            </>
          )}

          {g === "timer" && (
            <>
              <Row label="Thời gian mặc định theo độ khó" desc="Bật thì Timer đếm ngược bắt đầu từ: Dễ 20 phút · Trung bình 40 phút · Khó 60 phút.">
                <Toggle label="Thời gian theo độ khó" on={timerCfg.byDifficulty} onChange={(v) => setTimerCfg({ ...timerCfg, byDifficulty: v })} />
              </Row>
              <Row label="Tự đặt lại" desc="Bật thì đồng hồ tự về 0 khi bài nộp được Accepted.">
                <Toggle label="Tự đặt lại" on={timerCfg.autoReset} onChange={(v) => setTimerCfg({ ...timerCfg, autoReset: v })} />
              </Row>
              <Row label="Chuông báo" desc="Phát tiếng khi Timer còn 10 phút và khi hết giờ.">
                <Toggle label="Chuông báo" on={timerCfg.alarm} onChange={(v) => setTimerCfg({ ...timerCfg, alarm: v })} />
              </Row>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
