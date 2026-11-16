// Sao lưu DB nhất quán (VACUUM INTO, an toàn khi server đang chạy) vào ../backups, giữ 14 bản gần nhất.
// Dùng:  node scripts/backup.mjs
import fs from "node:fs";
import path from "node:path";
import { db, ROOT } from "../lib/db.js";

const dir = path.join(ROOT, "backups");
fs.mkdirSync(dir, { recursive: true });
const d = new Date();
const p2 = (n) => String(n).padStart(2, "0");
const file = path.join(dir, `netjudge-${d.getFullYear()}${p2(d.getMonth() + 1)}${p2(d.getDate())}-${p2(d.getHours())}${p2(d.getMinutes())}.db`);
db.exec(`VACUUM INTO '${file.replace(/'/g, "''")}'`);
console.log("Đã sao lưu:", file);

const old = fs.readdirSync(dir).filter((f) => /^netjudge-\d{8}-\d{4}\.db$/.test(f)).sort().slice(0, -14);
for (const f of old) fs.rmSync(path.join(dir, f));
if (old.length) console.log("Đã xoá bản cũ:", old.join(", "));
