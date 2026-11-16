import { notFound, redirect } from "next/navigation";
import { marked } from "marked";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { statusMap } from "@/lib/progress";
import { getProblem, getSamples, listProblems, listPlans, DIFF_LABEL } from "@/lib/content";
import Workspace from "./Workspace";

export const dynamic = "force-dynamic";

export default async function ProblemPage({ params }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const { id } = await params;
  const p = getProblem(id);
  if (!p) notFound();

  const problems = listProblems();
  const all = problems.map((x) => x.id);
  const status = statusMap(user.id);
  // Dữ liệu gọn cho thanh bên "Danh sách bài" (mở ngay trong trang làm bài).
  const list = problems.map((x, i) => ({ id: x.id, n: i + 1, title: x.title, difficulty: x.difficulty, status: status[x.id] || "todo" }));
  const idx = all.indexOf(id);

  const history = db
    .prepare("SELECT id, status, verdict, passed, total, created FROM submissions WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 30")
    .all(user.id, id)
    // node:sqlite trả về object null-prototype; Client Component chỉ nhận object thường.
    .map((r) => ({ ...r }));
  const last = db.prepare("SELECT code FROM submissions WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 1").get(user.id, id);
  // Thống kê dưới đề (như "Accepted / Submissions / Acceptance Rate" của LeetCode), tính trên mọi người dùng.
  const agg = db.prepare("SELECT SUM(verdict='AC') AS ac, COUNT(*) AS n FROM submissions WHERE problem_id=? AND status='done'").get(id);
  const stats = { ac: Number(agg?.ac || 0), total: Number(agg?.n || 0) };
  // "Bài tương tự": chung chủ đề nhiều nhất, ưu tiên cùng chương.
  const similar = problems
    .filter((x) => x.id !== id)
    .map((x) => ({ x, score: x.topics.filter((t) => p.topics.includes(t)).length * 2 + (x.chapter === p.chapter ? 1 : 0) }))
    .filter((o) => o.score >= 2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map(({ x }) => ({ id: x.id, title: x.title, difficulty: x.difficulty, status: status[x.id] || "todo" }));

  // Thích / sao (Yêu thích) và chuỗi ngày nộp bài liên tiếp (ngọn lửa trên thanh trên).
  const likes = Number(db.prepare("SELECT COUNT(*) n FROM reactions WHERE problem_id=? AND v=1").get(id).n);
  const mine = Number(db.prepare("SELECT v FROM reactions WHERE user_id=? AND problem_id=?").get(user.id, id)?.v ?? 0);
  const favorite = !!db.prepare("SELECT 1 x FROM favorites WHERE user_id=? AND problem_id=?").get(user.id, id);
  const ymd = (d) => d.toLocaleDateString("sv-SE");
  const days = new Set(db.prepare("SELECT created FROM submissions WHERE user_id=? AND status='done'").all(user.id).map((r) => ymd(new Date(r.created * 1000))));
  const now = new Date();
  let streak = 0;
  for (let k = days.has(ymd(now)) ? 0 : 1; days.has(ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - k))); k++) streak++;
  // Số ngày đến kỳ thi (ô cam ở góc phải thanh trên, chỗ của nút Premium bên LeetCode).
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const examDate = listPlans().map((pl) => pl.exam_date).filter(Boolean)
    .map((v) => new Date((v instanceof Date ? v.toISOString() : String(v)).slice(0, 10) + "T00:00:00"))
    .filter((v) => v >= today0).sort((a, b) => a - b)[0];
  const examDays = examDate ? Math.round((examDate - today0) / 86400000) : null;

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
        type: p.type,
      }}
      stats={stats}
      social={{ likes, mine, favorite }}
      streak={streak}
      examDays={examDays}
      similar={similar}
      lastSubmitted={last?.code ?? null}
      nav={{ prev: all[idx - 1] ?? null, next: all[idx + 1] ?? null, all, list, diffLabel: DIFF_LABEL }}
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
