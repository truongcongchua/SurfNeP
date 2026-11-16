"use client";
// Hộp xác nhận kiểu LeetCode ("Are you sure?"): icon i xanh lá bên trái, nút Huỷ xám + Xác nhận xanh lá.
// Thay cho window.confirm. Esc hoặc bấm ra ngoài = Huỷ; Enter = Xác nhận.
import { useEffect } from "react";
import { Info } from "lucide-react";

export function ConfirmDialog({ open, title = "Bạn chắc chắn chứ?", message, confirmLabel = "Xác nhận", onConfirm, onCancel }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onCancel();
      else if (e.key === "Enter") onConfirm();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel, onConfirm]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-black/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div role="alertdialog" aria-label={title} className="w-[min(480px,100%)] rounded-xl bg-[var(--panel)] p-6 shadow-[var(--pop-shadow)]">
        <div className="flex gap-4">
          <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-[#2db55d] text-white"><Info className="size-4" strokeWidth={2.5} /></span>
          <div className="min-w-0">
            <div className="text-lg text-[var(--title)]">{title}</div>
            <div className="mt-2 text-sm leading-6 text-[var(--text2)]">{message}</div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onCancel} className="h-8 rounded-lg bg-[var(--chip)] px-4 text-sm font-medium text-[var(--title)] hover:bg-[var(--pill)]">Huỷ</button>
          <button onClick={onConfirm} autoFocus className="h-8 rounded-lg bg-[#2db55d] px-4 text-sm font-medium text-white hover:bg-[#28a352]">{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
