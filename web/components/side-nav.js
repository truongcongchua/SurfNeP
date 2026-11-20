// Thanh bên trái của trang Bài tập / Study Plan (giống Library · Study Plan của LeetCode). Header chỉ giữ mục cấp 1 (Bài tập · Ôn tập) để không trùng với thanh này..
// `lists` (tuỳ chọn): mục "Danh sách của tôi" — lọc theo trạng thái làm bài.
import Link from "next/link";
import { Library, GraduationCap } from "lucide-react";
import { MyLists } from "./my-lists";

export function SideNav({ active, lists }) {
  return (
    <nav className="side-nav" aria-label="Điều hướng">
      <Link href="/problems" className={active === "problems" ? "on" : undefined}><Library /> Thư viện</Link>
      <Link href="/plans" className={active === "plans" ? "on" : undefined}><GraduationCap /> Study Plan</Link>
      {lists && (
        <>
          <hr />
          <MyLists lists={lists} />
        </>
      )}
    </nav>
  );
}
