import { db } from "./db";

// Trạng thái của người dùng với từng bài: 'solved' nếu có lần AC, 'attempted' nếu đã nộp, ngược lại 'todo'.
export function statusMap(userId) {
  const rows = db
    .prepare(
      `SELECT problem_id, MAX(CASE WHEN verdict='AC' THEN 1 ELSE 0 END) AS solved, COUNT(*) AS n
       FROM submissions WHERE user_id = ? AND status='done' GROUP BY problem_id`
    )
    .all(userId);
  const m = {};
  for (const r of rows) m[r.problem_id] = r.solved ? "solved" : "attempted";
  return m;
}

// Bài bị khoá nếu còn bài nền chưa AC (chỉ gợi ý, không chặn nộp bài).
export function unmetPrereqs(problem, status) {
  return problem.prerequisites.filter((p) => status[p] !== "solved");
}

export function leaderboard(planIds) {
  const users = db.prepare("SELECT id, username, display FROM users ORDER BY id").all();
  return users.map((u) => {
    const s = statusMap(u.id);
    return { name: u.display || u.username, solved: planIds.filter((id) => s[id] === "solved").length };
  });
}
