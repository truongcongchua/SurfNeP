"use client";
// Thanh trên của trang làm bài — dựng theo số đo lấy từ leetcode.com (cao 48px, padding 10px, gap 8px):
//  trái  : logo | [≡ Danh sách bài] [‹] [›] [⤮]
//  giữa  : nhóm liền [🐞🔒 | ▶ | ☁ Nộp bài] (nền fill-3, bo 5px, vạch ngăn 1px) + nút Ghi chú vuông riêng
//  phải  : Bố cục · Cài đặt · Chuông · 🔥chuỗi ngày · nhóm đồng hồ · Mời · ảnh đại diện · ô cam (đếm ngược kỳ thi)
import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useRef, useState } from "react";
import { Bell, Bug, ChevronLeft, ChevronRight, CloudUpload, Flame, ListIndentIncrease, Loader2, LogOut, Lock, Monitor, Moon, NotebookPen, Play, Settings, Shuffle, Sun, UserPlus } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Logo } from "@/components/logo";
import { logoutAction } from "@/app/actions";
import { cn } from "@/lib/utils";

// Nút icon 32×32 như LeetCode: icon 16px màu xám, hover nền fill-3 + icon đậm lên.
export function NavIcon({ label, onClick, href, children, disabled, className, active }) {
  const cls = cn("inline-flex size-8 shrink-0 items-center justify-center rounded-lg text-[var(--icon-nav)] transition-colors hover:bg-[var(--fill-3)] hover:text-[var(--title)] disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-4",
    active && "text-[var(--title)]", className);
  if (href) return <Link href={href} title={label} aria-label={label} className={cls}>{children}</Link>;
  return <button title={label} aria-label={label} onClick={onClick} disabled={disabled} className={cls}>{children}</button>;
}

const Divider = ({ h = "h-8" }) => <span className={cn("w-px shrink-0 bg-[var(--div)]", h)} />;

function Bells() {
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  useEffect(() => {
    if (!open) return;
    const h = (e) => { if (!box.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);
  return (
    <div ref={box} className="relative">
      <NavIcon label="Thông báo" onClick={() => setOpen((v) => !v)} active={open}><Bell /></NavIcon>
      {open && (
        <div className="absolute right-0 top-10 z-50 w-72 rounded-lg bg-[var(--panel)] p-4 shadow-[var(--pop-shadow)]">
          <div className="mb-2 text-sm font-medium text-[var(--title)]">Thông báo</div>
          <div className="py-6 text-center text-sm text-[var(--faint)]">Chưa có thông báo nào</div>
        </div>
      )}
    </div>
  );
}

function UserMenu({ name }) {
  const { theme, setTheme } = useTheme();
  const items = [["light", "Sáng", Sun], ["dark", "Tối", Moon], ["system", "Theo hệ thống", Monitor]];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="avatar mx-1" aria-label="Tài khoản" style={{ width: 24, height: 24, fontSize: 11 }}>{name.slice(0, 1).toUpperCase()}</button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="flex items-center gap-2 px-2 py-2">
          <span className="avatar" style={{ width: 32, height: 32 }}>{name.slice(0, 1).toUpperCase()}</span>
          <span className="truncate text-sm font-medium text-[var(--title)]">{name}</span>
        </div>
        <DropdownMenuSeparator />
        <div className="px-2 pb-1 pt-1.5 text-xs text-[var(--muted)]">Giao diện</div>
        {items.map(([k, t, Icon]) => (
          <DropdownMenuItem key={k} onSelect={(e) => { e.preventDefault(); setTheme(k); }}>
            <Icon /> {t}{theme === k && <span className="ml-auto size-1.5 rounded-full bg-[var(--accent)]" />}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild><Link href="/" className="!text-[var(--text)] hover:no-underline">Danh sách bài</Link></DropdownMenuItem>
        <DropdownMenuItem asChild><Link href="/plans" className="!text-[var(--text)] hover:no-underline">Study Plan</Link></DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => logoutAction()}><LogOut /> Đăng xuất</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function TopBar({
  nav, problemId, router, busy, running, debugging, onRun, onDebug, onSubmit, noteOpen, onNote, onList, onShuffle,
  layouts, settingsBtn, clock, streak, examDays, userName, onInvite,
}) {
  const grp = "flex h-8 items-center justify-center text-[var(--text2)] transition-colors hover:bg-[var(--fill-4)]";
  return (
    <nav className="relative flex h-12 w-full shrink-0 items-center justify-between gap-2 px-2.5">
      {/* ---- trái ---- */}
      <div className="flex min-w-0 flex-1 items-center">
        <Link href="/" className="ml-2.5 mr-2 flex h-10 items-center text-[var(--brand)]" aria-label="SurfNeP"><Logo size={22} strokeWidth={2.2} /></Link>
        <Divider h="h-7" />
        <button onClick={onList} className="group/pl flex h-8 cursor-pointer items-center gap-2 px-2 text-[var(--icon-nav)] hover:text-[var(--title)]" aria-label="Danh sách bài">
          <ListIndentIncrease className="size-4" />
          <span className="font-medium text-[var(--title)]">Danh sách bài</span>
        </button>
        <Divider h="h-7" />
        <NavIcon label="Bài trước" disabled={!nav.prev} onClick={() => router.push(`/problems/${nav.prev}`)} className="rounded-none"><ChevronLeft /></NavIcon>
        <Divider h="h-7" />
        <NavIcon label="Bài sau" disabled={!nav.next} onClick={() => router.push(`/problems/${nav.next}`)} className="rounded-none"><ChevronRight /></NavIcon>
        <Divider h="h-7" />
        <NavIcon label="Bài ngẫu nhiên" onClick={onShuffle} className="rounded-none"><Shuffle /></NavIcon>
      </div>

      {/* ---- giữa: căn giữa tuyệt đối như LeetCode ---- */}
      <div className="absolute left-1/2 top-2 flex -translate-x-1/2 items-center gap-2">
        <div className="flex overflow-hidden rounded-[5px] bg-[var(--fill-3)]">
          <button onClick={onDebug} disabled={busy || running || debugging} title="Gỡ lỗi (ASan + UBSan, chạy testcase đang chọn)" aria-label="Gỡ lỗi" className={cn(grp, "w-8 disabled:opacity-60")}>
            {debugging ? <Loader2 className="size-4 animate-spin" /> : <Bug className="size-4 text-[var(--brand)]" />}
          </button>
          <span className="w-px bg-[var(--div)]" />
          <button onClick={onRun} disabled={busy || running || debugging} title="Chạy thử (Ctrl + ')" aria-label="Chạy thử" className={cn(grp, "w-8 disabled:opacity-60")}>
            {running ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-3.5 fill-current" />}
          </button>
          <span className="w-px bg-[var(--div)]" />
          <button onClick={onSubmit} disabled={busy || running || debugging} title="Nộp bài (Ctrl + Enter)" aria-label="Nộp bài"
            className={cn(grp, "gap-2 px-3 font-medium text-[var(--submit)] disabled:opacity-60")}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : <CloudUpload className="size-4" />}
            {busy ? "Đang chấm…" : "Nộp bài"}
          </button>
        </div>
        <button onClick={onNote} title="Ghi chú" aria-label="Ghi chú"
          className={cn("flex size-8 items-center justify-center rounded-[5px] bg-[var(--fill-3)] hover:bg-[var(--fill-4)]", noteOpen ? "text-[var(--brand)]" : "text-[var(--text2)]")}>
          <NotebookPen className="size-4" />
        </button>
      </div>

      {/* ---- phải ---- */}
      <div className="flex min-w-0 flex-1 items-center justify-end gap-1">
        {layouts}
        {settingsBtn}
        <div className="relative"><Bells /></div>
        <Link href="/" title={streak ? `Chuỗi ${streak} ngày nộp bài liên tiếp` : "Chưa có chuỗi ngày nộp bài"} aria-label="Chuỗi ngày nộp bài"
          className="flex h-8 items-center gap-1 rounded-lg px-1.5 text-[var(--icon)] hover:bg-[var(--fill-3)]">
          <Flame className="size-4" /><span className="text-sm tabular-nums">{streak}</span>
        </Link>
        {clock}
        <NavIcon label="Mời bạn (sao chép liên kết)" onClick={onInvite}><UserPlus /></NavIcon>
        <UserMenu name={userName} />
        {examDays != null && (
          <Link href="/plans" title="Số ngày đến kỳ thi giữa kỳ" className="ml-1 hidden h-8 items-center rounded-lg bg-[rgba(255,161,22,.12)] px-3 text-sm leading-8 text-[#ffa116] hover:bg-[rgba(255,161,22,.18)] lg:inline-flex">
            {examDays === 0 ? "Thi hôm nay" : `Thi còn ${examDays} ngày`}
          </Link>
        )}
      </div>
    </nav>
  );
}
