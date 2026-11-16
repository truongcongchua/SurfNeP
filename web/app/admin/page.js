import { notFound, redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { requireAdmin } from "@/lib/auth";
import { db } from "@/lib/db";

async function toggle(formData) {
  "use server";
  const me = await requireAdmin();
  if (!me) return;
  const id = Number(formData.get("id"));
  if (id === me.id) return;
  db.prepare("UPDATE users SET disabled = 1 - disabled WHERE id=?").run(id);
  db.prepare("DELETE FROM sessions WHERE user_id=?").run(id); // khoá thì đăng xuất ngay
  revalidatePath("/admin");
}

async function remove(formData) {
  "use server";
  const me = await requireAdmin();
  if (!me) return;
  const id = Number(formData.get("id"));
  if (id === me.id) return;
  for (const t of ["sessions", "submissions", "plan_start", "reactions", "favorites", "contest_reg"])
    db.prepare(`DELETE FROM ${t} WHERE user_id=?`).run(id);
  db.prepare("DELETE FROM users WHERE id=?").run(id);
  revalidatePath("/admin");
}

const fmt = (t) => (t ? new Date(t * 1000).toLocaleString("vi-VN") : "—");

export default async function Admin() {
  const me = await requireAdmin();
  if (!me) notFound();
  const rows = db
    .prepare(
      `SELECT u.id, u.username, u.role, u.disabled, u.created,
              (SELECT COUNT(*) FROM submissions s WHERE s.user_id=u.id) AS subs,
              (SELECT MAX(created) FROM submissions s WHERE s.user_id=u.id) AS last
       FROM users u ORDER BY u.id`
    )
    .all();
  const q = db.prepare("SELECT COUNT(*) n FROM submissions WHERE status!='done'").get().n;
  return (
    <div className="admin">
      <h1>Quản trị — {rows.length} người dùng, {Number(q)} bài đang chờ chấm</h1>
      <table>
        <thead>
          <tr><th>#</th><th>Tên</th><th>Vai trò</th><th>Tạo lúc</th><th>Bài nộp</th><th>Nộp gần nhất</th><th></th></tr>
        </thead>
        <tbody>
          {rows.map((u) => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.username}{u.disabled ? " (đã khoá)" : ""}</td>
              <td>{u.role}</td>
              <td>{fmt(u.created)}</td>
              <td>{Number(u.subs)}</td>
              <td>{fmt(u.last)}</td>
              <td>
                {u.id !== me.id && (
                  <>
                    <form action={toggle} style={{ display: "inline" }}>
                      <input type="hidden" name="id" value={u.id} />
                      <button>{u.disabled ? "Mở khoá" : "Khoá"}</button>
                    </form>
                    <form action={remove} style={{ display: "inline" }}>
                      <input type="hidden" name="id" value={u.id} />
                      <button className="danger">Xoá</button>
                    </form>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
