import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";
import { Check } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { getConcept } from "@/lib/content";
import { conceptProblems, listBugs, listCards, listQuestions, mastery } from "@/lib/learn";
import { statusMap } from "@/lib/progress";
import { BAND, Bar, Card, bandOf } from "@/components/learn/ui";

export default async function ConceptPage({ params }) {
  const user = await currentUser();
  const { id } = await params;
  const c = getConcept(id);
  if (!c) notFound();
  const probs = conceptProblems()[id] || [];
  const status = statusMap(user.id);
  const me = mastery(user.id).find((x) => x.id === id);
  const b = BAND[bandOf(me?.score)];
  const nQuiz = listQuestions().filter((q) => q.concept === id).length;
  const nCards = listCards().filter((x) => x.concept === id).length;
  const bugs = listBugs().filter((x) => x.concept === id);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
      <article>
        <Link href="/learn" className="text-xs text-[var(--muted)] hover:text-[var(--title)]">← Tổng quan</Link>
        <h1 className="mt-2 text-2xl font-medium text-[var(--title)]">{c.title}</h1>
        {c.ref && <div className="mt-1 text-sm text-[var(--muted)]">{c.ref}</div>}
        <div className="lc-prose mt-5" dangerouslySetInnerHTML={{ __html: marked.parse(c.body, { async: false }) }} />
      </article>

      <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <Card>
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--muted)]">Độ thành thạo</span>
            <span className={b.text}>{b.label}{me?.score != null && ` · ${me.score}%`}</span>
          </div>
          <Bar value={me?.score} className="mt-2" />
        </Card>

        <Card>
          <h2 className="mb-2 text-sm font-medium text-[var(--title)]">Luyện tập</h2>
          <ul className="space-y-1.5 text-sm">
            {nCards > 0 && <li><Link className="text-[var(--accent)] hover:underline" href={`/learn/review?c=${id}`}>Ôn {nCards} flashcard</Link></li>}
            {nQuiz > 0 && <li><Link className="text-[var(--accent)] hover:underline" href={`/learn/quiz/${id}`}>Làm {nQuiz} câu quiz</Link></li>}
            {bugs.map((x) => (
              <li key={x.id}><Link className="text-[var(--accent)] hover:underline" href={`/learn/bugs/${x.id}`}>Tìm bug: {x.title}</Link></li>
            ))}
          </ul>
        </Card>

        {probs.length > 0 && (
          <Card>
            <h2 className="mb-2 text-sm font-medium text-[var(--title)]">Bài code dùng khái niệm này</h2>
            <ul className="space-y-1.5 text-sm">
              {probs.map((p) => (
                <li key={p.id} className="flex items-center gap-1.5">
                  {status[p.id] === "solved" ? <Check className="size-3.5 shrink-0 text-[var(--easy)]" /> : <span className="size-3.5 shrink-0" />}
                  <Link className="truncate text-[var(--accent)] hover:underline" href={`/problems/${p.id}`}>{p.title}</Link>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </aside>
    </div>
  );
}
