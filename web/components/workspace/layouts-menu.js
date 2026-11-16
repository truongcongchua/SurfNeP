"use client";
// Nút "Bố cục" trên thanh trên (như Layouts của LeetCode): chọn Mặc định / Leet (3 cột), và Chế độ tập trung.
import { useEffect, useRef, useState } from "react";
import { LayoutDashboard, Focus } from "lucide-react";
import { cn } from "@/lib/utils";

function Thumb({ kind }) {
  const b = "rounded-[3px] bg-[var(--chip)]";
  return kind === "default" ? (
    <div className="grid h-[68px] grid-cols-2 gap-1"><div className={b} /><div className="grid grid-rows-[2fr_1fr] gap-1"><div className={b} /><div className={b} /></div></div>
  ) : (
    <div className="grid h-[68px] grid-cols-3 gap-1"><div className={b} /><div className={b} /><div className={b} /></div>
  );
}

export function LayoutsMenu({ layout, onLayout, onFocus, focused }) {
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
      <button onClick={() => setOpen((v) => !v)} title="Bố cục" aria-label="Bố cục"
        className={cn("inline-flex size-8 items-center justify-center rounded-lg hover:bg-[var(--fill-3)] hover:text-[var(--title)]", open ? "bg-[var(--fill-3)] text-[var(--title)]" : "text-[var(--icon-nav)]")}>
        <LayoutDashboard className="size-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-50 w-72 rounded-lg bg-[var(--panel)] p-4 shadow-[var(--pop-shadow)]">
          <div className="mb-3 text-sm font-medium text-[var(--title)]">Bố cục</div>
          <div className="grid grid-cols-2 gap-3">
            {[["default", "Mặc định"], ["leet", "Leet"]].map(([k, t]) => (
              <button key={k} onClick={() => { onLayout(k); setOpen(false); }} className="text-left">
                <div className={cn("rounded-md p-1.5 ring-1", layout === k ? "ring-2 ring-[var(--accent)]" : "ring-[var(--line)] hover:ring-[var(--line-strong)]")}><Thumb kind={k} /></div>
                <div className={cn("mt-1.5 text-xs", layout === k ? "font-medium text-[var(--title)]" : "text-[var(--muted)]")}>{t}</div>
              </button>
            ))}
          </div>
          <div className="my-3 h-px bg-[var(--line)]" />
          <button onClick={() => { onFocus(); setOpen(false); }} className="flex h-8 w-full items-center justify-center gap-2 rounded-md bg-[var(--chip)] text-sm text-[var(--title)] hover:bg-[var(--pill)]">
            <Focus className="size-4 text-[var(--brand)]" /> {focused ? "Thoát chế độ tập trung" : "Chế độ tập trung"}
          </button>
        </div>
      )}
    </div>
  );
}
