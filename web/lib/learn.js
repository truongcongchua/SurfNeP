// Phần "Ôn tập": nạp nội dung (knowledge/*.yaml|md), lịch ôn SM-2 và độ thành thạo theo khái niệm.
import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import { ROOT, db } from "./db";
import { listProblems, getConcept } from "./content";
import { statusMap } from "./progress";

const K = path.join(ROOT, "knowledge");
const safe = (s) => typeof s === "string" && /^[\w.-]+$/.test(s);

function yaml(file, fallback) {
  try {
    return YAML.parse(fs.readFileSync(path.join(K, file), "utf8")) ?? fallback;
  } catch {
    return fallback;
  }
}

export const CHAPTERS = { 2: "Chương 2 · Lập trình socket", 3: "Chương 3 · Server nhiều client" };

// Khái niệm = knowledge/<id>.md, xếp theo chương rồi theo tên.
export function listConcepts() {
  return fs
    .readdirSync(K)
    .filter((f) => f.endsWith(".md") && f !== "cheatsheet.md")
    .map((f) => getConcept(f.replace(/\.md$/, "")))
    .filter(Boolean)
    .sort((a, b) => (a.chapter || 9) - (b.chapter || 9) || a.title.localeCompare(b.title, "vi"));
}

// Khái niệm -> các bài (không tính bài thi thử) dùng nó.
export function conceptProblems() {
  const m = {};
  for (const p of listProblems()) if (!p.exam) for (const c of p.concepts) (m[c] ||= []).push(p);
  return m;
}

export function getCheatsheet() {
  try {
    return fs.readFileSync(path.join(K, "cheatsheet.md"), "utf8");
  } catch {
    return "";
  }
}

// ---- Tìm bug ----
export const listBugs = () => yaml("bugs.yaml", []).filter((b) => safe(b.problem) && safe(b.file));
export const getBug = (id) => listBugs().find((b) => b.id === id) ?? null;

// Mã nguồn bản sai, bỏ các chú thích "SAI ..." (cả dòng 1) nhưng giữ nguyên số dòng.
export function bugCode(b) {
  const f = path.join(ROOT, "problems", b.problem, "wrong", b.file);
  if (!fs.existsSync(f)) return null;
  return fs
    .readFileSync(f, "utf8")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((l) => l.replace(/\s*\/\/\s*(SAI|Lời giải mẫu).*$/, ""))
    .join("\n")
    .replace(/\n$/, "");
}

// ---- Quiz ----
export const listQuestions = () => yaml("quiz.yaml", []);
export function quizSet(set) {
  const all = listQuestions();
  if (set === "all") return all;
  const m = /^ch(\d)$/.exec(set);
  if (m) {
    const ids = new Set(listConcepts().filter((c) => String(c.chapter) === m[1]).map((c) => c.id));
    return all.filter((q) => ids.has(q.concept));
  }
  return all.filter((q) => q.concept === set);
}

// ---- Flashcard (SM-2 rút gọn) ----
export const listCards = () => yaml("flashcards.yaml", []);
const DAY = 86400;
const now = () => Math.floor(Date.now() / 1000);

// grade: 0 Lại · 1 Khó · 2 Được · 3 Dễ
export function nextState(s, grade) {
  let { ease = 2.5, reps = 0, lapses = 0, interval = 0 } = s || {};
  if (grade === 0) {
    return { ease: Math.max(1.3, ease - 0.2), reps: 0, lapses: lapses + 1, interval: 0, due: now() + 600 };
  }
  ease = Math.max(1.3, ease + (grade === 1 ? -0.15 : grade === 3 ? 0.15 : 0));
  reps += 1;
  const mult = grade === 1 ? 0.8 : grade === 3 ? 1.3 : 1;
  interval = reps === 1 ? 1 : reps === 2 ? (grade === 1 ? 3 : 6) : Math.max(interval + 1, Math.round(interval * ease * mult));
  return { ease, reps, lapses, interval, due: now() + interval * DAY };
}

export function reviewCard(userId, cardId, grade) {
  const cur = db.prepare("SELECT * FROM srs WHERE user_id=? AND card_id=?").get(userId, cardId);
  const n = nextState(cur, grade);
  db.prepare(
    `INSERT INTO srs (user_id, card_id, due, interval, ease, reps, lapses, last) VALUES (?,?,?,?,?,?,?,?)
     ON CONFLICT(user_id, card_id) DO UPDATE SET due=excluded.due, interval=excluded.interval, ease=excluded.ease,
       reps=excluded.reps, lapses=excluded.lapses, last=excluded.last`
  ).run(userId, cardId, n.due, n.interval, n.ease, n.reps, n.lapses, now());
  return n;
}

const NEW_PER_DAY = 10;
// Hàng đợi hôm nay: thẻ đến hạn (quá hạn lâu nhất trước) rồi thẻ mới (tối đa NEW_PER_DAY thẻ mới mỗi ngày).
export function dueQueue(userId, concept) {
  const cards = listCards().filter((c) => !concept || c.concept === concept);
  const st = new Map(db.prepare("SELECT * FROM srs WHERE user_id=?").all(userId).map((r) => [r.card_id, r]));
  const t = now();
  const due = cards.filter((c) => st.has(c.id) && st.get(c.id).due <= t).sort((a, b) => st.get(a.id).due - st.get(b.id).due);
  const startOfDay = new Date();
  startOfDay.setHours(0, 0, 0, 0);
  // Thẻ mới đã học hôm nay: lần ôn đầu tiên của thẻ rơi vào hôm nay (chưa từng bị "Lại", mới ôn 1 lần).
  const newToday = db
    .prepare("SELECT COUNT(*) n FROM srs WHERE user_id=? AND reps=1 AND lapses=0 AND last>=?")
    .get(userId, Math.floor(startOfDay / 1000)).n;
  const fresh = cards.filter((c) => !st.has(c.id)).slice(0, Math.max(0, NEW_PER_DAY - newToday));
  return { queue: [...due, ...fresh], due: due.length, fresh: fresh.length, total: cards.length, learned: st.size };
}

export function dueCount(userId) {
  const t = now();
  const ids = new Set(listCards().map((c) => c.id));
  return db.prepare("SELECT card_id, due FROM srs WHERE user_id=?").all(userId).filter((r) => ids.has(r.card_id) && r.due <= t).length;
}

// ---- Nhật ký & độ thành thạo ----
export function logEvent(userId, kind, ref, concept, ok) {
  db.prepare("INSERT INTO learn_events (user_id, kind, ref, concept, ok, ts) VALUES (?,?,?,?,?,?)").run(
    userId, kind, ref, concept ?? null, ok ? 1 : 0, now()
  );
}

export function bugStatus(userId) {
  const rows = db.prepare("SELECT ref, MAX(ok) ok FROM learn_events WHERE user_id=? AND kind='bug' GROUP BY ref").all(userId);
  return Object.fromEntries(rows.map((r) => [r.ref, r.ok ? "found" : "tried"]));
}

// Độ thành thạo 0–100 của từng khái niệm = trung bình các tín hiệu đang có:
//  · bài code: tỉ lệ bài đã AC
//  · quiz + tìm bug: tỉ lệ đúng ở 10 lượt gần nhất
//  · flashcard: tỉ lệ thẻ đã nhớ lâu (khoảng ôn >= 3 ngày)
export function mastery(userId) {
  const status = statusMap(userId);
  const probs = conceptProblems();
  const cards = listCards();
  const srs = new Map(db.prepare("SELECT * FROM srs WHERE user_id=?").all(userId).map((r) => [r.card_id, r]));
  const ev = db.prepare("SELECT concept, ok FROM learn_events WHERE user_id=? AND concept IS NOT NULL ORDER BY id DESC").all(userId);
  const evBy = {};
  for (const e of ev) {
    const a = (evBy[e.concept] ||= []);
    if (a.length < 10) a.push(e.ok);
  }

  return listConcepts().map((c) => {
    const ps = probs[c.id] || [];
    const solved = ps.filter((p) => status[p.id] === "solved").length;
    const mine = cards.filter((x) => x.concept === c.id);
    const seen = mine.filter((x) => srs.has(x.id));
    const known = seen.filter((x) => srs.get(x.id).interval >= 3).length;
    const q = evBy[c.id] || [];

    const parts = [];
    const sig = { problems: null, quiz: null, cards: null };
    if (ps.length) { sig.problems = solved / ps.length; parts.push(sig.problems); }
    if (q.length) { sig.quiz = q.reduce((a, b) => a + b, 0) / q.length; parts.push(sig.quiz); }
    if (seen.length) { sig.cards = mine.length ? known / mine.length : 0; parts.push(sig.cards); }
    const score = parts.length ? Math.round((100 * parts.reduce((a, b) => a + b, 0)) / parts.length) : null;
    return {
      id: c.id, title: c.title, chapter: c.chapter, score, sig,
      counts: { problems: ps.length, solved, cards: mine.length, seen: seen.length, known, quizN: q.length },
      problems: ps.map((p) => ({ id: p.id, title: p.title, status: status[p.id] || "todo" })),
    };
  });
}
