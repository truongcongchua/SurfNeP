import Link from "next/link";
import { notFound } from "next/navigation";
import { quizSet } from "@/lib/learn";
import { QuizRunner } from "@/components/learn/quiz-runner";

export default async function QuizPage({ params }) {
  const { set } = await params;
  if (!/^[\w-]+$/.test(set)) notFound();
  let qs = quizSet(set);
  if (!qs.length) notFound();
  // "Tổng hợp" lấy ngẫu nhiên 15 câu để mỗi lượt làm một khác.
  const key = Date.now();
  if (set === "all") qs = [...qs].sort(() => Math.random() - 0.5).slice(0, 15);

  return (
    <div>
      <Link href="/learn/quiz" className="text-xs text-[var(--muted)] hover:text-[var(--title)]">← Danh sách quiz</Link>
      <QuizRunner key={key} questions={qs} />
    </div>
  );
}
