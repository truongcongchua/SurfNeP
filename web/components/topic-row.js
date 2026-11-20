"use client";
// Hàng chủ đề kiểu LeetCode: thu gọn = đúng MỘT dòng (chỉ hiện số chủ đề vừa chiều rộng, nhiều bài nhất trước),
// bấm "Mở rộng" để xem tất cả. Bấm chủ đề đang chọn lần nữa thì bỏ lọc (href của mục đang chọn do server tính sẵn).
import Link from "next/link";
import { useLayoutEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

const GAP = 20;

export function TopicRow({ items }) {
  const [open, setOpen] = useState(false);
  const [fit, setFit] = useState(items.length);
  const box = useRef(null);
  const ruler = useRef(null);

  // Đo thật chiều rộng từng mục (trong một hàng ẩn) rồi đếm xem bao nhiêu mục vừa một dòng, chừa chỗ cho nút "Mở rộng".
  useLayoutEffect(() => {
    const measure = () => {
      const w = box.current?.clientWidth || 0;
      const kids = [...(ruler.current?.children || [])];
      const more = kids.pop(); // nút Mở rộng nằm cuối hàng đo
      let used = (more?.offsetWidth || 0) + GAP, n = 0;
      for (const k of kids) {
        if (used + k.offsetWidth > w) break;
        used += k.offsetWidth + GAP;
        n++;
      }
      setFit(Math.max(1, n));
    };
    measure();
    const ro = new ResizeObserver(measure);
    if (box.current) ro.observe(box.current);
    if (ruler.current) ro.observe(ruler.current); // đo lại khi CSS/phông tải xong làm đổi kích thước hàng đo
    document.fonts?.ready.then(measure);
    return () => ro.disconnect();
  }, [items]);

  const overflow = items.length > fit;
  // Chủ đề đang lọc luôn phải thấy được: nếu nằm ngoài phần vừa dòng thì đổi chỗ với mục cuối của phần hiện.
  let shown = items;
  if (!open && overflow) {
    shown = items.slice(0, fit);
    const on = items.findIndex((x) => x.on);
    if (on >= fit) shown = [...items.slice(0, fit - 1), items[on]];
  }
  const link = (x) => (
    <Link key={x.name} href={x.href} scroll={false} className={x.on ? "on" : undefined}>
      {x.name} <span className="n">{x.count}</span>
    </Link>
  );
  const moreBtn = (
    <button type="button" onClick={() => setOpen(!open)} className="more">
      {open ? "Thu gọn" : "Mở rộng"} <ChevronDown className="size-3.5" style={{ transform: open ? "rotate(180deg)" : undefined }} />
    </button>
  );

  return (
    <div ref={box} className={`topic-row${open ? " open" : ""}`}>
      {shown.map(link)}
      {(overflow || open) && moreBtn}
      <div ref={ruler} className="topic-ruler" aria-hidden>
        {items.map((x) => <span key={x.name} className="inline-flex items-center gap-1.5 text-sm">{x.name} <span className="n">{x.count}</span></span>)}
        <span className="inline-flex items-center gap-1.5 text-sm">Mở rộng <ChevronDown className="size-3.5" /></span>
      </div>
    </div>
  );
}
