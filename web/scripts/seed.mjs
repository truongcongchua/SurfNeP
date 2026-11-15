// Tạo (hoặc đổi mật khẩu) tài khoản. Dùng:  node scripts/seed.mjs ten1:matkhau1 ten2:matkhau2
import { db, hashPassword } from "../lib/db.js";

const args = process.argv.slice(2);
if (!args.length) {
  console.error("Cách dùng: node scripts/seed.mjs <tên>:<mật khẩu> [<tên>:<mật khẩu> ...]");
  process.exit(2);
}
for (const a of args) {
  const i = a.indexOf(":");
  const name = a.slice(0, i).trim().toLowerCase(), pw = a.slice(i + 1);
  if (i < 1 || pw.length < 6) { console.error(`Bỏ qua "${name}": cần dạng tên:mật_khẩu, mật khẩu ≥ 6 ký tự`); continue; }
  db.prepare(
    `INSERT INTO users (username, pw_hash, display) VALUES (?, ?, ?)
     ON CONFLICT(username) DO UPDATE SET pw_hash = excluded.pw_hash`
  ).run(name, hashPassword(pw), name);
  console.log("OK:", name);
}
