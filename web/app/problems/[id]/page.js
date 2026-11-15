import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { marked } from "marked";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getProblem, DIFF_LABEL } from "@/lib/content";
import Workspace from "./Workspace";

export const dynamic = "force-dynamic";

export default async function ProblemPage({ params }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const { id } = await params;
  const p = getProblem(id);
  if (!p) notFound();

  const history = db
    .prepare("SELECT id, status, verdict, passed, total, created FROM submissions WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 15")
    .all(user.id, id);
  const last = db.prepare("SELECT code FROM submissions WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 1").get(user.id, id);
  const html = marked.parse(p.statement, { async: false });

  return (
    <div className="problem">
      <section className="card pane">
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 6 }}>
          <span className={`diff-${p.difficulty}`} style={{ fontWeight: 700 }}>{DIFF_LABEL[p.difficulty]}</span>
          <span className="chip">Chương {p.chapter}</span>
          {p.topics.map((t) => <span key={t} className="chip">{t}</span>)}
        </div>
        <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
        {p.ref && <p className="sub" style={{ marginTop: 18 }}>Tham chiếu: {p.ref}</p>}
        {p.prerequisites.length > 0 && (
          <p className="sub">Bài nền: {p.prerequisites.map((x, i) => <span key={x}>{i > 0 && ", "}<Link href={`/problems/${x}`}>{x}</Link></span>)}</p>
        )}
      </section>
      <Workspace
        problemId={id}
        starter={last?.code ?? p.starter}
        hasSaved={!!last}
        originalStarter={p.starter}
        examMinutes={p.examMinutes}
        history={history}
      />
    </div>
  );
}
