import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { listPlans } from "@/lib/content";
import { CHAPTERS, bugStatus, dueQueue, listBugs, listConcepts, listQuestions, mastery } from "@/lib/learn";
import { BAND, Bar, Card, Stat, bandOf } from "@/components/learn/ui";

export default async function LearnHome() {
  const user = await currentUser();
  const m = mastery(user.id);
  const byId = Object.fromEntries(m.map((x) => [x.id, x]));
  const q = dueQueue(user.id);
  const bugs = listBugs();
  const found = Object.values(bugStatus(user.id)).filter((v) => v === "found").length;
  const withScore = m.filter((x) => x.score != null);
  const avg = withScore.length ? Math.round(withScore.reduce((a, x) => a + x.score, 0) / withScore.length) : null;
  const weakest = [...m].sort((a, b) => (a.score ?? -1) - (b.score ?? -1)).slice(0, 3);
  const quizDone = db.prepare("SELECT COUNT(DISTINCT ref) n FROM learn_events WHERE user_id=? AND kind='quiz'").get(user.id).n;

  const now = new Date();
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const exam = listPlans().map((p) => p.exam_date).filter(Boolean)
    .map((v) => new Date((v instanceof Date ? v.toISOString() : String(v)).slice(0, 10) + "T00:00:00"))
    .filter((v) => v >= today0).sort((a, b) => a - b)[0];
  const days = exam ? Math.round((exam - today0) / 86400000) : null;

  const concepts = listConcepts();
  const chapters = [...new Set(concepts.map((c) => c.chapter))];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-medium text-[var(--title)]">Ôn tập giữa kỳ</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Lý thuyết, quiz, tìm bug và flashcard bổ trợ cho phần luyện code.{days != null && <> Còn <b className="text-[var(--title)]">{days} ngày</b> đến kỳ thi.</>}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat href="/learn/review" label="Flashcard hôm nay" value={q.due + q.fresh} hint={`${q.due} đến hạn · ${q.fresh} thẻ mới`} />
        <Stat href="/learn/quiz" label="Quiz" value={`${quizDone}/${listQuestions().length}`} hint="câu đã làm" />
        <Stat href="/learn/bugs" label="Tìm bug" value={`${found}/${bugs.length}`} hint="bug đã tìm đúng" />
        <Stat href="/learn/progress" label="Độ thành thạo" value={avg == null ? "—" : `${avg}%`} hint="trung bình các khái niệm" />
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-medium text-[var(--title)]">Nên ôn trước</h2>
          <Link href="/learn/progress" className="flex items-center gap-1 text-xs text-[var(--muted)] hover:text-[var(--title)]">Xem tất cả <ArrowRight className="size-3.5" /></Link>
        </div>
        <ul className="divide-y divide-[var(--line)]">
          {weakest.map((c) => {
            const b = BAND[bandOf(c.score)];
            return (
              <li key={c.id} className="flex items-center gap-3 py-2.5">
                <Link href={`/learn/c/${c.id}`} className="min-w-0 flex-1 truncate text-sm text-[var(--title)] hover:underline">{c.title}</Link>
                <span className={`w-20 shrink-0 text-right text-xs ${b.text}`}>{b.label}{c.score != null && ` · ${c.score}%`}</span>
                <Bar value={c.score} className="hidden w-24 sm:block" />
              </li>
            );
          })}
        </ul>
      </Card>

      {chapters.map((ch) => (
        <section key={ch}>
          <h2 className="mb-3 text-base font-medium text-[var(--title)]">{CHAPTERS[ch] || `Chương ${ch}`}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {concepts.filter((c) => c.chapter === ch).map((c) => {
              const x = byId[c.id];
              const b = BAND[bandOf(x?.score)];
              return (
                <Link key={c.id} href={`/learn/c/${c.id}`} className="block rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3 transition-colors hover:bg-[var(--raised)]">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-sm font-medium text-[var(--title)]">{c.title}</span>
                    <span className={`shrink-0 text-xs ${b.text}`}>{b.label}</span>
                  </div>
                  {c.ref && <div className="mt-0.5 truncate text-xs text-[var(--muted)]">{c.ref}</div>}
                  <Bar value={x?.score} className="mt-2.5" />
                  <div className="mt-1.5 text-xs text-[var(--muted)]">
                    {x?.counts.problems ?? 0} bài code · {x?.counts.cards ?? 0} flashcard
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
