import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";
import { VERDICT_LABEL as LABEL } from "@/lib/verdicts";
import { getProblem } from "@/lib/content";
import { bugCode, getBug, listBugs } from "@/lib/learn";
import { BugRunner } from "@/components/learn/bug-runner";

export default async function BugPage({ params }) {
  const { id } = await params;
  const b = getBug(id);
  const code = b ? bugCode(b) : null;
  if (!b || code == null) notFound();
  const all = listBugs();
  const i = all.findIndex((x) => x.id === id);
  const p = getProblem(b.problem);

  return (
    <div>
      <Link href="/learn/bugs" className="text-xs text-[var(--muted)] hover:text-[var(--title)]">← Danh sách bug</Link>
      <h1 className="mt-2 text-xl font-medium text-[var(--title)]">Bài {p?.title || b.problem}</h1>
      <div className="mt-1 text-sm text-[var(--muted)]">
        <Link className="text-[var(--accent)] hover:underline" href={`/problems/${b.problem}`}>Xem đề bài gốc</Link>
        {b.verdict && <> · bộ chấm báo <b className="text-[var(--title)]">{LABEL[b.verdict] || b.verdict}</b></>}
      </div>
      <div className="mt-3 rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3 text-sm">
        <span className="text-xs text-[var(--muted)]">Triệu chứng · </span>
        <span dangerouslySetInnerHTML={{ __html: marked.parseInline(b.symptom, { async: false }) }} />
      </div>
      <BugRunner bugId={b.id} code={code} next={all[i + 1]?.id ?? null} />
    </div>
  );
}
