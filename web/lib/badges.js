import { db } from "./db";
import { listProblems, listPlans, planProblemIds } from "./content";

export const BADGES = [
  { id: "first-ac",   emoji: "🎯",   name: "Bài đầu tiên",    description: "Nộp AC bài đầu tiên" },
  { id: "streak-3",   emoji: "🔥",   name: "Lửa 3 ngày",      description: "Giải đúng 3 ngày liên tiếp" },
  { id: "streak-7",   emoji: "🔥🔥", name: "Lửa 7 ngày",      description: "Giải đúng 7 ngày liên tiếp" },
  { id: "first-hard", emoji: "💪",   name: "Khó đầu tiên",    description: "AC bài mức Khó đầu tiên" },
  { id: "all-easy",   emoji: "✅",   name: "Dễ hết",           description: "Giải hết tất cả bài Dễ" },
  { id: "half-way",   emoji: "🏃",   name: "Nửa đường",        description: "Giải 50% tổng số bài" },
  { id: "plan-done",  emoji: "🎓",   name: "Hoàn thành plan",  description: "Hoàn thành 100% một study plan" },
  { id: "bug-hunter", emoji: "🐛",   name: "Bug Hunter",       description: "Tìm 5+ bug trong phần học" },
  { id: "centurion",  emoji: "💯",   name: "100 lần nộp",      description: "Tổng cộng 100 lần nộp bài" },
];

/** Returns array of earned badge ids for the given userId. */
export function earnedBadges(userId) {
  const earned = [];

  // --- first-ac: has at least one AC submission ---
  const firstAC = db
    .prepare("SELECT 1 FROM submissions WHERE user_id=? AND status='done' AND verdict='AC' LIMIT 1")
    .get(userId);
  if (firstAC) earned.push("first-ac");

  // --- streak-3 / streak-7: consecutive days with at least one AC ---
  const acDays = db
    .prepare(
      "SELECT DISTINCT date(created,'unixepoch','localtime') AS d FROM submissions WHERE user_id=? AND status='done' AND verdict='AC' ORDER BY d DESC"
    )
    .all(userId)
    .map((r) => r.d);

  if (acDays.length > 0) {
    let maxStreak = 1, cur = 1;
    for (let i = 1; i < acDays.length; i++) {
      const prev = new Date(acDays[i - 1]);
      const curr = new Date(acDays[i]);
      const diff = Math.round((prev - curr) / 86400000);
      if (diff === 1) { cur++; maxStreak = Math.max(maxStreak, cur); }
      else cur = 1;
    }
    if (maxStreak >= 3) earned.push("streak-3");
    if (maxStreak >= 7) earned.push("streak-7");
  }

  // --- first-hard: AC on a hard problem ---
  const hardAC = db
    .prepare(
      "SELECT 1 FROM submissions s WHERE s.user_id=? AND s.status='done' AND s.verdict='AC' " +
      "AND EXISTS (SELECT 1 FROM submissions s2 WHERE s2.id=s.id LIMIT 1) LIMIT 1"
    );
  // We need to cross-reference with problem metadata (difficulty lives in YAML, not DB).
  const problems = listProblems();
  const hardIds = new Set(problems.filter((p) => p.difficulty === "hard").map((p) => p.id));
  if (hardIds.size > 0) {
    const placeholders = [...hardIds].map(() => "?").join(",");
    const row = db
      .prepare(
        `SELECT 1 FROM submissions WHERE user_id=? AND status='done' AND verdict='AC' AND problem_id IN (${placeholders}) LIMIT 1`
      )
      .get(userId, ...[...hardIds]);
    if (row) earned.push("first-hard");
  }

  // --- all-easy: solved every Easy problem ---
  const easyIds = problems.filter((p) => p.difficulty === "easy").map((p) => p.id);
  if (easyIds.length > 0) {
    const solvedEasy = db
      .prepare(
        `SELECT COUNT(DISTINCT problem_id) AS n FROM submissions WHERE user_id=? AND status='done' AND verdict='AC' AND problem_id IN (${easyIds.map(() => "?").join(",")})`
      )
      .get(userId, ...easyIds);
    if (solvedEasy && solvedEasy.n >= easyIds.length) earned.push("all-easy");
  }

  // --- half-way: solved >= 50% of all problems ---
  const totalProblems = problems.length;
  if (totalProblems > 0) {
    const solvedCount = db
      .prepare("SELECT COUNT(DISTINCT problem_id) AS n FROM submissions WHERE user_id=? AND status='done' AND verdict='AC'")
      .get(userId);
    if (solvedCount && solvedCount.n >= Math.ceil(totalProblems / 2)) earned.push("half-way");
  }

  // --- plan-done: completed any plan 100% ---
  const plans = listPlans();
  const solvedProblems = new Set(
    db
      .prepare("SELECT DISTINCT problem_id FROM submissions WHERE user_id=? AND status='done' AND verdict='AC'")
      .all(userId)
      .map((r) => r.problem_id)
  );
  for (const plan of plans) {
    const ids = planProblemIds(plan);
    if (ids.length > 0 && ids.every((id) => solvedProblems.has(id))) {
      earned.push("plan-done");
      break;
    }
  }

  // --- bug-hunter: found 5+ bugs in learn/bugs section ---
  const bugs = db
    .prepare("SELECT COUNT(*) AS n FROM learn_events WHERE user_id=? AND kind='bug' AND ok=1")
    .get(userId);
  if (bugs && bugs.n >= 5) earned.push("bug-hunter");

  // --- centurion: 100 total submissions ---
  const totalSubs = db
    .prepare("SELECT COUNT(*) AS n FROM submissions WHERE user_id=?")
    .get(userId);
  if (totalSubs && totalSubs.n >= 100) earned.push("centurion");

  return earned;
}

/** Returns array of badge ids that are newly earned but not yet seen. */
export function newBadges(userId) {
  const earned = earnedBadges(userId);
  if (earned.length === 0) return [];
  const seen = new Set(
    db
      .prepare("SELECT badge_id FROM badge_seen WHERE user_id=?")
      .all(userId)
      .map((r) => r.badge_id)
  );
  return earned.filter((id) => !seen.has(id));
}

/** Mark a badge as seen. */
export function markBadgeSeen(userId, badgeId) {
  db
    .prepare("INSERT OR IGNORE INTO badge_seen (user_id, badge_id, seen_at) VALUES (?,?,?)")
    .run(userId, badgeId, Math.floor(Date.now() / 1000));
}
