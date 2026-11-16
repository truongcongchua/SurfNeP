// Giới hạn tốc độ kiểu cửa sổ trượt, lưu trong SQLite (đủ cho một máy, vài chục người).
import { headers } from "next/headers";
import { db } from "./db";

const now = () => Math.floor(Date.now() / 1000);

// Đếm các lần trong `windowSec` giây gần nhất của `key`; nếu chưa vượt `limit` thì ghi thêm một lần và trả true.
export function allow(key, limit, windowSec) {
  const t = now();
  db.prepare("DELETE FROM rate_hits WHERE key=? AND ts<=?").run(key, t - windowSec);
  const n = db.prepare("SELECT COUNT(*) n FROM rate_hits WHERE key=?").get(key).n;
  if (n >= limit) return false;
  db.prepare("INSERT INTO rate_hits (key, ts) VALUES (?,?)").run(key, t);
  return true;
}

// Chỉ kiểm tra, không ghi (dùng cho đăng nhập: chỉ tính lần sai).
export function blocked(key, limit, windowSec) {
  const n = db.prepare("SELECT COUNT(*) n FROM rate_hits WHERE key=? AND ts>?").get(key, now() - windowSec).n;
  return n >= limit;
}
export function record(key) {
  db.prepare("INSERT INTO rate_hits (key, ts) VALUES (?,?)").run(key, now());
}
export function clear(key) {
  db.prepare("DELETE FROM rate_hits WHERE key=?").run(key);
}

// IP người gọi. Chỉ tin X-Forwarded-For khi chạy sau reverse proxy (NJ_TRUST_PROXY=1).
export async function clientIp() {
  const h = await headers();
  if (process.env.NJ_TRUST_PROXY === "1") {
    const xff = h.get("x-forwarded-for");
    if (xff) return xff.split(",")[0].trim();
  }
  return h.get("x-real-ip") || "local";
}

// Dọn bản ghi cũ thỉnh thoảng.
setInterval(() => {
  try { db.prepare("DELETE FROM rate_hits WHERE ts<?").run(now() - 86400); } catch {}
}, 3600_000).unref?.();
