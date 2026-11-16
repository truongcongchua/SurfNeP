"use client";
// Form lọc tự áp dụng: đổi ô chọn là lọc ngay, gõ ô tìm thì lọc sau khi ngừng gõ 300ms.
// Cập nhật URL bằng router.replace (không tải lại trang, không chất đống lịch sử Back),
// và bỏ các tham số rỗng để URL gọn (/?c=2 thay vì /?q=&d=&c=2&t=).
import { useRef, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function FilterForm({ children, className }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const timer = useRef();
  const [pending, startTransition] = useTransition();

  const apply = (form) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of new FormData(form)) {
      if (v) next.set(k, v); else next.delete(k);
    }
    const qs = next.toString();
    startTransition(() => router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false }));
  };

  const onChange = (e) => {
    clearTimeout(timer.current);
    const form = e.currentTarget;
    if (e.target.type === "search") timer.current = setTimeout(() => apply(form), 300);
    else apply(form);
  };

  return (
    <form
      className={className}
      data-pending={pending || undefined}
      onChange={onChange}
      onSubmit={(e) => { e.preventDefault(); clearTimeout(timer.current); apply(e.currentTarget); }}
    >
      {children}
    </form>
  );
}
