"use client";
// Hàng chủ đề kiểu LeetCode: hiện vài chủ đề nhiều bài nhất, bấm "Mở rộng" để xem tất cả.
// Bấm chủ đề đang chọn lần nữa thì bỏ lọc (href của mục đang chọn do server tính sẵn).
import Link from "next/link";
import { useState } from "react";
import { ChevronDown } from "lucide-react";

export function TopicRow({ items, limit = 8 }) {
  const [open, setOpen] = useState(false);
  const shown = open ? items : items.filter((x, i) => i < limit || x.on);
  return (
    <div className="topic-row">
      {shown.map((x) => (
        <Link key={x.name} href={x.href} scroll={false} className={x.on ? "on" : undefined}>
          {x.name} <span className="n">{x.count}</span>
        </Link>
      ))}
      {items.length > limit && (
        <button type="button" onClick={() => setOpen(!open)} className="more">
          {open ? "Thu gọn" : "Mở rộng"} <ChevronDown className="size-3.5" style={{ transform: open ? "rotate(180deg)" : undefined }} />
        </button>
      )}
    </div>
  );
}
