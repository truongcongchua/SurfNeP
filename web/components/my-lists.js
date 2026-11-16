"use client";
// Mục "Danh sách của tôi" thu/mở được như "My Lists" của LeetCode; nhớ trạng thái thu/mở trên trình duyệt.
import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";

const KEY = "nj-mylists-open";

export function MyLists({ lists }) {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    try { if (localStorage.getItem(KEY) === "0") setOpen(false); } catch {}
  }, []);
  const toggle = () => {
    setOpen((o) => {
      try { localStorage.setItem(KEY, o ? "0" : "1"); } catch {}
      return !o;
    });
  };
  return (
    <div className="mylists" data-open={open}>
      <button type="button" className="grp-btn" onClick={toggle} aria-expanded={open} aria-controls="mylists-body">
        <span>Danh sách của tôi</span>
        <ChevronDown className="chev" />
      </button>
      <div id="mylists-body" className="body">
        <div className="sm">
          {lists.map((x) => (
            <Link key={x.key} href={x.href} className={x.on ? "on" : undefined} tabIndex={open ? 0 : -1}>{x.icon} {x.label} <span className="n">{x.count}</span></Link>
          ))}
        </div>
      </div>
    </div>
  );
}
