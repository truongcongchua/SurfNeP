"use client";
// Đồng hồ đếm ngược tới mốc `to` (giây Unix). Hết giờ thì làm mới trang để chuyển trạng thái contest.
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const pad = (n) => String(n).padStart(2, "0");

export function Countdown({ to, className }) {
  const router = useRouter();
  const [left, setLeft] = useState(null);
  useEffect(() => {
    let fired = false;
    const tick = () => {
      const s = Math.max(0, Math.ceil(to - Date.now() / 1000));
      setLeft(s);
      if (s === 0 && !fired) { fired = true; setTimeout(() => router.refresh(), 800); }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [to, router]);
  if (left == null) return <span className={className}>--:--:--</span>;
  const d = Math.floor(left / 86400), h = Math.floor((left % 86400) / 3600), m = Math.floor((left % 3600) / 60), s = left % 60;
  return <span className={className} suppressHydrationWarning>{d > 0 ? `${d}d ` : ""}{pad(h)}:{pad(m)}:{pad(s)}</span>;
}
