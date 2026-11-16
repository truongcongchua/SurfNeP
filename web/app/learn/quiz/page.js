import Link from "next/link";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { CHAPTERS, listConcepts, listQuestions } from "@/lib/learn";

export default async function QuizHub() {
  const user = await currentUser();
  const qs = listQuestions();
  const done = new Map(
    db.prepare("SELECT ref, MAX(ok) ok FROM learn_events WHERE user_id=? AND kind='quiz' GROUP BY ref").all(user.id).map((r) => [r.ref, r.ok])
  );
  const concepts = listConcepts().filter((c) => qs.some((q) => q.concept === c.id));
  const count = (f) => qs.filter(f).length;
  const right = (f) => qs.filter((q) => f(q) && done.get(q.id) === 1).length;
  const chapters = [...new Set(concepts.map((c) => c.chapter))];

  const Row = ({ href, title, sub, n, ok }) => (
    <Link href={href} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-[var(--raised)]">
      <span className="min-w-0 flex-1">
        <span className="block text-sm text-[var(--title)]">{title}</span>
        {sub && <span className="block truncate text-xs text-[var(--muted)]">{sub}</span>}
      </span>
      <span className="shrink-0 text-xs text-[var(--muted)]">{ok}/{n} đúng</span>
    </Link>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium text-[var(--title)]">Quiz</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">Ba dạng câu hỏi: trắc nghiệm, sắp xếp thứ tự lời gọi hàm và điền chỗ trống trong code. Kết quả được tính vào bản đồ điểm yếu.</p>
      </div>

      <ul className="divide-y divide-[var(--line)] overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--panel)]">
        <Row href="/learn/quiz/all" title="Tổng hợp tất cả" sub="Trộn ngẫu nhiên mọi khái niệm" n={qs.length} ok={right(() => true)} />
        {chapters.map((ch) => (
          <Row key={ch} href={`/learn/quiz/ch${ch}`} title={`Ôn ${CHAPTERS[ch]?.split(" · ")[0] || `chương ${ch}`}`} sub={CHAPTERS[ch]?.split(" · ")[1]}
            n={count((q) => concepts.some((c) => c.chapter === ch && c.id === q.concept))}
            ok={right((q) => concepts.some((c) => c.chapter === ch && c.id === q.concept))} />
        ))}
      </ul>

      <section>
        <h2 className="mb-2 text-base font-medium text-[var(--title)]">Theo khái niệm</h2>
        <ul className="divide-y divide-[var(--line)] overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--panel)]">
          {concepts.map((c) => (
            <Row key={c.id} href={`/learn/quiz/${c.id}`} title={c.title} n={count((q) => q.concept === c.id)} ok={right((q) => q.concept === c.id)} />
          ))}
        </ul>
      </section>
    </div>
  );
}
