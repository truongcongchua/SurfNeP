import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

export const ROOT = path.resolve(process.cwd(), "..");
const DATA = path.join(ROOT, "data");
fs.mkdirSync(DATA, { recursive: true });

const g = globalThis;
if (!g.__nj_db) {
  const db = new DatabaseSync(path.join(DATA, "netjudge.db"));
  db.exec(`
    PRAGMA busy_timeout = 10000;
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL, display TEXT);
    CREATE TABLE IF NOT EXISTS sessions (
      token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS submissions (
      id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, problem_id TEXT NOT NULL,
      code TEXT NOT NULL, status TEXT NOT NULL,           -- queued | running | done
      verdict TEXT, passed INTEGER, total INTEGER, result TEXT, created INTEGER NOT NULL);
    CREATE INDEX IF NOT EXISTS sub_user_problem ON submissions(user_id, problem_id);
    CREATE TABLE IF NOT EXISTS plan_start (
      user_id INTEGER NOT NULL, plan_id TEXT NOT NULL, started INTEGER NOT NULL,
      PRIMARY KEY (user_id, plan_id));
    -- Thích (v=1) / không thích (v=-1) từng bài, và danh sách Yêu thích (nút ngôi sao).
    CREATE TABLE IF NOT EXISTS reactions (
      user_id INTEGER NOT NULL, problem_id TEXT NOT NULL, v INTEGER NOT NULL,
      PRIMARY KEY (user_id, problem_id));
    CREATE TABLE IF NOT EXISTS favorites (
      user_id INTEGER NOT NULL, problem_id TEXT NOT NULL,
      PRIMARY KEY (user_id, problem_id));
  `);
  // Server khởi động lại thì các bài đang chấm dở được xếp hàng lại.
  db.exec("UPDATE submissions SET status='queued' WHERE status='running'");
  g.__nj_db = db;
}
export const db = g.__nj_db;
// Bảng thêm sau này: chạy mỗi lần nạp module để cả server đang chạy (giữ kết nối cũ) cũng có bảng mới.
db.exec(`
  CREATE TABLE IF NOT EXISTS reactions (
    user_id INTEGER NOT NULL, problem_id TEXT NOT NULL, v INTEGER NOT NULL, PRIMARY KEY (user_id, problem_id));
  CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL, problem_id TEXT NOT NULL, PRIMARY KEY (user_id, problem_id));
`);

// Cột/bảng cho đăng ký mở + quản trị + giới hạn tốc độ (chạy lại an toàn ở mỗi lần nạp module).
const have = new Set(db.prepare("PRAGMA table_info(users)").all().map((c) => c.name));
for (const [name, def] of [["role", "TEXT NOT NULL DEFAULT 'user'"], ["disabled", "INTEGER NOT NULL DEFAULT 0"], ["created", "INTEGER"]]) {
  if (!have.has(name)) db.exec(`ALTER TABLE users ADD COLUMN ${name} ${def}`);
}
db.exec(`
  CREATE TABLE IF NOT EXISTS rate_hits (key TEXT NOT NULL, ts INTEGER NOT NULL);
  CREATE INDEX IF NOT EXISTS rate_key ON rate_hits(key, ts);
`);

export function hashPassword(pw, salt = crypto.randomBytes(16).toString("hex")) {
  const h = crypto.scryptSync(pw, salt, 32).toString("hex");
  return `${salt}:${h}`;
}

export function verifyPassword(pw, stored) {
  const [salt, h] = stored.split(":");
  const t = crypto.scryptSync(pw, salt, 32);
  return crypto.timingSafeEqual(t, Buffer.from(h, "hex"));
}
