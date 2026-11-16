// Tạo (hoặc đổi mật khẩu) tài khoản. Dùng:  node scripts/seed.mjs [--admin] ten1:matkhau1 ten2:matkhau2
// --admin: đặt vai trò quản trị cho các tài khoản trong lệnh này.
import { db, hashPassword } from "../lib/db.js";

const argv = process.argv.slice(2);
const admin = argv.includes("--admin");
const args = argv.filter((a) => a !== "--admin");
if (!args.length) {
  console.error("Cách dùng: node scripts/seed.mjs [--admin] <tên>:<mật khẩu> [<tên>:<mật khẩu> ...]");
  process.exit(2);
}
for (const a of args) {
  const i = a.indexOf(":");
  const name = a.slice(0, i).trim().toLowerCase(), pw = a.slice(i + 1);
  if (i < 1 || pw.length < 6) { console.error(`Bỏ qua "${name}": cần dạng tên:mật_khẩu, mật khẩu ≥ 6 ký tự`); continue; }
  db.prepare(
    `INSERT INTO users (username, pw_hash, display, role, created) VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(username) DO UPDATE SET pw_hash = excluded.pw_hash,
       role = CASE WHEN ? THEN 'admin' ELSE users.role END`
  ).run(name, hashPassword(pw), name, admin ? "admin" : "user", Math.floor(Date.now() / 1000), admin ? 1 : 0);
  console.log("OK:", name, admin ? "(admin)" : "");
}
