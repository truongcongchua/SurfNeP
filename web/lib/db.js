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
  `);
  // Server khởi động lại thì các bài đang chấm dở được xếp hàng lại.
  db.exec("UPDATE submissions SET status='queued' WHERE status='running'");
  g.__nj_db = db;
}
export const db = g.__nj_db;

export function hashPassword(pw, salt = crypto.randomBytes(16).toString("hex")) {
  const h = crypto.scryptSync(pw, salt, 32).toString("hex");
  return `${salt}:${h}`;
}

export function verifyPassword(pw, stored) {
  const [salt, h] = stored.split(":");
  const t = crypto.scryptSync(pw, salt, 32);
  return crypto.timingSafeEqual(t, Buffer.from(h, "hex"));
}
