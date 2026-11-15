import { notFound, redirect } from "next/navigation";
import { marked } from "marked";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getProblem, getSamples, listProblems, DIFF_LABEL } from "@/lib/content";
import Workspace from "./Workspace";

export const dynamic = "force-dynamic";

export default async function ProblemPage({ params }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const { id } = await params;
  const p = getProblem(id);
  if (!p) notFound();

  const all = listProblems().map((x) => x.id);
  const idx = all.indexOf(id);

  const history = db
    .prepare("SELECT id, status, verdict, passed, total, created FROM submissions WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 30")
    .all(user.id, id)
    // node:sqlite trả về object null-prototype; Client Component chỉ nhận object thường.
    .map((r) => ({ ...r }));
  const last = db.prepare("SELECT code FROM submissions WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 1").get(user.id, id);

  // Tiêu đề hiện riêng (kiểu "3. Tên bài"), nên bỏ dòng "# ..." đầu đề.
  const statement = p.statement.replace(/^\s*#\s+[^\n]*\n/, "");
  const html = marked.parse(statement, { async: false });

  return (
    <Workspace
      problemId={id}
      problem={{
        number: idx + 1,
        title: p.title,
        difficulty: p.difficulty,
        diffLabel: DIFF_LABEL[p.difficulty],
        chapter: p.chapter,
        topics: p.topics,
        ref: p.ref || null,
        prerequisites: p.prerequisites,
        exam: !!p.exam,
      }}
      nav={{ prev: all[idx - 1] ?? null, next: all[idx + 1] ?? null, all }}
      user={{ name: user.display || user.username }}
      samples={getSamples(id)}
      html={html}
      starter={last?.code ?? p.starter}
      originalStarter={p.starter}
      examMinutes={p.examMinutes ?? null}
      history={history}
    />
  );
}
