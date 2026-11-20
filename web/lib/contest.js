// Contest kiểu LeetCode: admin tạo contest (giờ bắt đầu, thời lượng, danh sách bài); người dùng đăng ký rồi nộp bài
// bình thường. Điểm lấy từ chính bảng submissions: lượt nộp đã chấm của người đã đăng ký, vào bài của contest,
// trong khoảng [start, end] — không cần đổi API nộp bài.
import { db } from "./db";
import { listProblems } from "./content";

db.exec(`
  CREATE TABLE IF NOT EXISTS contests (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, start INTEGER NOT NULL, duration INTEGER NOT NULL,
    problems TEXT NOT NULL, created INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS contest_reg (
    contest_id INTEGER NOT NULL, user_id INTEGER NOT NULL, ts INTEGER NOT NULL, PRIMARY KEY (contest_id, user_id));
`);

export const POINTS = { easy: 3, medium: 5, hard: 7 }; // điểm mỗi bài theo độ khó
export const PENALTY = 300; // phạt 5 phút cho mỗi lần nộp sai trước khi AC (CE không bị phạt)

const now = () => Math.floor(Date.now() / 1000);

function shape(r) {
  if (!r) return null;
  return { id: Number(r.id), title: r.title, start: Number(r.start), duration: Number(r.duration), end: Number(r.start) + Number(r.duration) * 60, problems: JSON.parse(r.problems) };
}

export const listContests = () => db.prepare("SELECT * FROM contests ORDER BY start DESC").all().map(shape);
export const getContest = (id) => shape(db.prepare("SELECT * FROM contests WHERE id=?").get(Number(id) || 0));
export const phase = (c, t = now()) => (t < c.start ? "upcoming" : t <= c.end ? "running" : "ended");
export const isRegistered = (cid, uid) => !!db.prepare("SELECT 1 x FROM contest_reg WHERE contest_id=? AND user_id=?").get(cid, uid);
export const regCount = (cid) => Number(db.prepare("SELECT COUNT(*) n FROM contest_reg WHERE contest_id=?").get(cid).n);

// Chi tiết bài của contest (giữ đúng thứ tự admin chọn, bỏ bài đã bị xoá khỏi ngân hàng).
export function contestProblems(c) {
  const by = new Map(listProblems().map((p) => [p.id, p]));
  return c.problems.map((id) => by.get(id)).filter(Boolean).map((p) => ({ id: p.id, title: p.title, difficulty: p.difficulty, points: POINTS[p.difficulty] || 3 }));
}

// Bảng xếp hạng: điểm giảm dần, rồi thời gian hoàn thành (giây từ lúc bắt đầu + phạt) tăng dần.
export function standings(c) {
  const probs = contestProblems(c);
  if (!probs.length) return { probs, rows: [] };
  const ids = probs.map((p) => p.id);
  const pts = Object.fromEntries(probs.map((p) => [p.id, p.points]));
  const users = db
    .prepare("SELECT r.user_id, u.username, u.display FROM contest_reg r JOIN users u ON u.id=r.user_id WHERE r.contest_id=?")
    .all(c.id);
  const rows = new Map(users.map((u) => [Number(u.user_id), { userId: Number(u.user_id), name: u.display || u.username, score: 0, finish: 0, cells: {} }]));
  const subs = db
    .prepare(
      `SELECT user_id, problem_id, verdict, created FROM submissions
       WHERE status='done' AND created>=? AND created<=? AND problem_id IN (${ids.map(() => "?").join(",")}) ORDER BY created, id`
    )
    .all(c.start, c.end, ...ids);
  for (const s of subs) {
    const row = rows.get(Number(s.user_id));
    if (!row) continue;
    const cell = (row.cells[s.problem_id] ||= { ac: false, wrong: 0, t: 0 });
    if (cell.ac) continue;
    if (s.verdict === "AC") {
      cell.ac = true;
      cell.t = Number(s.created) - c.start;
      row.score += pts[s.problem_id];
      row.finish = Math.max(row.finish, cell.t + cell.wrong * PENALTY);
    } else if (s.verdict !== "CE" && s.verdict !== "IE") cell.wrong++;
  }
  // Phạt chỉ tính cho bài đã AC: tính lại thời gian hoàn thành cuối cùng sau khi biết đủ số lần sai.
  const list = [...rows.values()];
  for (const r of list) r.finish = Object.values(r.cells).filter((x) => x.ac).reduce((m, x) => Math.max(m, x.t + x.wrong * PENALTY), 0);
  list.sort((a, b) => b.score - a.score || a.finish - b.finish || a.name.localeCompare(b.name));
  let rank = 0;
  list.forEach((r, i) => { r.rank = i > 0 && list[i - 1].score === r.score && list[i - 1].finish === r.finish ? rank : (rank = i + 1); });
  return { probs, rows: list };
}

// Xếp hạng toàn cục: tổng điểm qua mọi contest đã kết thúc.
export function globalRanking() {
  const agg = new Map();
  for (const c of listContests()) {
    if (phase(c) !== "ended") continue;
    for (const r of standings(c).rows) {
      const a = agg.get(r.userId) || { userId: r.userId, name: r.name, score: 0, attended: 0 };
      a.score += r.score; a.attended++;
      agg.set(r.userId, a);
    }
  }
  return [...agg.values()].sort((a, b) => b.score - a.score || b.attended - a.attended);
}

export const fmtDur = (s) => {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`;
};
