import { marked } from "marked";
import { getCheatsheet } from "@/lib/learn";
import { PrintButton } from "@/components/learn/print-button";

export default function Cheatsheet() {
  const md = getCheatsheet();
  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3 print:hidden">
        <div>
          <h1 className="text-2xl font-medium text-[var(--title)]">Cheat sheet</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">Tóm tắt hàm socket, so sánh mô hình server và các lỗi hay gặp. Có thể in ra giấy.</p>
        </div>
        <PrintButton />
      </div>
      {md ? <div className="lc-prose cheat" dangerouslySetInnerHTML={{ __html: marked.parse(md, { async: false }) }} /> : <p className="text-sm text-[var(--muted)]">Chưa có nội dung.</p>}
    </div>
  );
}
