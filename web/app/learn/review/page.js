import Link from "next/link";
import { currentUser } from "@/lib/auth";
import { dueQueue, listConcepts } from "@/lib/learn";
import { ReviewRunner } from "@/components/learn/review-runner";

export default async function Review({ searchParams }) {
  const user = await currentUser();
  const { c } = await searchParams;
  const concept = typeof c === "string" && /^[\w-]+$/.test(c) ? c : null;
  const q = dueQueue(user.id, concept);
  const title = concept ? listConcepts().find((x) => x.id === concept)?.title : null;

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-medium text-[var(--title)]">Flashcard{title ? `: ${title}` : ""}</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Ôn ngắt quãng (SM-2): thẻ bạn nhớ tốt sẽ hiện lại thưa dần, thẻ quên sẽ quay lại sớm. Hôm nay có {q.due} thẻ đến hạn và {q.fresh} thẻ mới.
          {concept && <> <Link href="/learn/review" className="text-[var(--accent)] hover:underline">Ôn tất cả khái niệm</Link></>}
        </p>
      </div>
      <ReviewRunner cards={q.queue} stats={{ total: q.total, learned: q.learned }} />
    </div>
  );
}
