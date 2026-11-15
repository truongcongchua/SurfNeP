import crypto from "node:crypto";
import { cookies } from "next/headers";
import { db, verifyPassword } from "./db";

const COOKIE = "nj_session";
const MAX_AGE = 60 * 60 * 24 * 30;

export async function currentUser() {
  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) return null;
  return (
    db
      .prepare(
        `SELECT u.id, u.username, u.display FROM sessions s JOIN users u ON u.id = s.user_id
         WHERE s.token = ? AND s.created > ?`
      )
      .get(token, Math.floor(Date.now() / 1000) - MAX_AGE) ?? null
  );
}

export async function login(username, password) {
  const row = db.prepare("SELECT * FROM users WHERE username = ?").get(String(username || "").trim().toLowerCase());
  // Luôn so sánh một hash để thời gian phản hồi không lộ tài khoản có tồn tại hay không.
  const dummy = "00000000000000000000000000000000:" + "0".repeat(64);
  const ok = verifyPassword(String(password || ""), row ? row.pw_hash : dummy);
  if (!row || !ok) return false;
  const token = crypto.randomBytes(32).toString("hex");
  db.prepare("INSERT INTO sessions (token, user_id, created) VALUES (?, ?, ?)").run(
    token, row.id, Math.floor(Date.now() / 1000));
  (await cookies()).set(COOKIE, token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: MAX_AGE });
  return true;
}

export async function logout() {
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  if (token) db.prepare("DELETE FROM sessions WHERE token = ?").run(token);
  jar.delete(COOKIE);
}
