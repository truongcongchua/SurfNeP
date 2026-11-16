import crypto from "node:crypto";
import { cookies } from "next/headers";
import { db, hashPassword, verifyPassword } from "./db";
import { allow, blocked, record, clear, clientIp } from "./ratelimit";

const COOKIE = "nj_session";
const MAX_AGE = 60 * 60 * 24 * 30;
const USERNAME_RE = /^[a-z0-9_]{3,20}$/;
const secure = () => process.env.NJ_HTTPS === "1"; // bật khi chạy sau HTTPS

export async function currentUser() {
  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) return null;
  return (
    db
      .prepare(
        `SELECT u.id, u.username, u.display, u.role FROM sessions s JOIN users u ON u.id = s.user_id
         WHERE s.token = ? AND s.created > ? AND u.disabled = 0`
      )
      .get(token, Math.floor(Date.now() / 1000) - MAX_AGE) ?? null
  );
}

export async function requireAdmin() {
  const u = await currentUser();
  return u && u.role === "admin" ? u : null;
}

async function startSession(userId) {
  const token = crypto.randomBytes(32).toString("hex");
  db.prepare("INSERT INTO sessions (token, user_id, created) VALUES (?, ?, ?)").run(
    token, userId, Math.floor(Date.now() / 1000));
  (await cookies()).set(COOKIE, token, { httpOnly: true, sameSite: "lax", path: "/", maxAge: MAX_AGE, secure: secure() });
}

// Trả "ok" | "bad" (sai thông tin) | "locked" (sai quá nhiều lần) | "disabled".
export async function login(username, password) {
  const name = String(username || "").trim().toLowerCase().slice(0, 64);
  const ip = await clientIp();
  const kUser = `login:u:${name}`, kIp = `login:ip:${ip}`;
  // 5 lần sai / 15 phút cho mỗi tên, 20 lần sai / 15 phút cho mỗi IP.
  if (blocked(kUser, 5, 900) || blocked(kIp, 20, 900)) return "locked";

  const row = db.prepare("SELECT * FROM users WHERE username = ?").get(name);
  // Luôn so sánh một hash để thời gian phản hồi không lộ tài khoản có tồn tại hay không.
  const dummy = "00000000000000000000000000000000:" + "0".repeat(64);
  const ok = verifyPassword(String(password || "").slice(0, 128), row ? row.pw_hash : dummy);
  if (!row || !ok) {
    record(kUser); record(kIp);
    return "bad";
  }
  if (row.disabled) return "disabled";
  clear(kUser);
  await startSession(row.id);
  return "ok";
}

// Đăng ký mở như LeetCode. Nếu đặt NJ_INVITE_CODE thì bắt buộc nhập mã mời (đóng cửa tạm thời); NJ_SIGNUP=0 tắt hẳn.
// Trả { ok: true } hoặc { error: "..." }.
export async function register({ username, password, confirm, invite }) {
  if (process.env.NJ_SIGNUP === "0") return { error: "Đăng ký đang tạm đóng." };
  const ip = await clientIp();
  if (!allow(`reg:ip:${ip}`, 5, 3600)) return { error: "Đăng ký quá nhiều lần từ mạng này, thử lại sau." };

  const name = String(username || "").trim().toLowerCase();
  const pw = String(password || "");
  if (!USERNAME_RE.test(name)) return { error: "Tên đăng nhập 3–20 ký tự, chỉ gồm chữ thường, số và dấu gạch dưới." };
  if (pw.length < 8 || pw.length > 128) return { error: "Mật khẩu từ 8 đến 128 ký tự." };
  if (pw !== String(confirm || "")) return { error: "Hai mật khẩu không khớp." };
  const code = process.env.NJ_INVITE_CODE;
  if (code && String(invite || "").trim() !== code) return { error: "Mã mời không đúng." };
  if (db.prepare("SELECT 1 x FROM users WHERE username=?").get(name)) return { error: "Tên đăng nhập đã được dùng." };

  const r = db
    .prepare("INSERT INTO users (username, pw_hash, display, created) VALUES (?,?,?,?)")
    .run(name, hashPassword(pw), name, Math.floor(Date.now() / 1000));
  await startSession(Number(r.lastInsertRowid));
  return { ok: true };
}

export async function logout() {
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  if (token) db.prepare("DELETE FROM sessions WHERE token = ?").run(token);
  jar.delete(COOKIE);
}
