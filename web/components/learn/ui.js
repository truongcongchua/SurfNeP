// Mảnh giao diện dùng chung cho khu vực Ôn tập (Server Component được).
import { cn } from "@/lib/utils";

export const bandOf = (s) => (s == null ? "none" : s < 40 ? "weak" : s < 70 ? "mid" : "good");
export const BAND = {
  none: { label: "Chưa học", bar: "bg-[var(--faint)]", text: "text-[var(--muted)]" },
  weak: { label: "Yếu", bar: "bg-[var(--hard)]", text: "text-[var(--hard)]" },
  mid: { label: "Trung bình", bar: "bg-[var(--medium)]", text: "text-[var(--medium)]" },
  good: { label: "Tốt", bar: "bg-[var(--easy)]", text: "text-[var(--easy)]" },
};

export function Bar({ value, band, className }) {
  const b = BAND[band ?? bandOf(value)];
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-[var(--chip)]", className)}>
      <div className={cn("h-full rounded-full", b.bar)} style={{ width: `${value ?? 0}%` }} />
    </div>
  );
}

export function Card({ className, children }) {
  return <section className={cn("rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4", className)}>{children}</section>;
}

export function Stat({ label, value, hint, href }) {
  const inner = (
    <>
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-2xl font-medium text-[var(--title)]">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-[var(--muted)]">{hint}</div>}
    </>
  );
  const cls = "block rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4";
  return href ? <a href={href} className={cn(cls, "transition-colors hover:bg-[var(--raised)]")}>{inner}</a> : <div className={cls}>{inner}</div>;
}
