"use server";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { currentUser, requireAdmin } from "@/lib/auth";
import { db } from "@/lib/db";
import { getContest, phase } from "@/lib/contest";
import { getProblem } from "@/lib/content";

export async function registerContest(formData) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const id = Number(formData.get("id"));
  const c = getContest(id);
  if (!c || phase(c) === "ended") return;
  db.prepare("INSERT OR IGNORE INTO contest_reg (contest_id, user_id, ts) VALUES (?,?,?)").run(id, user.id, Math.floor(Date.now() / 1000));
  revalidatePath(`/contest/${id}`);
  revalidatePath("/contest");
}

export async function unregisterContest(formData) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const id = Number(formData.get("id"));
  const c = getContest(id);
  if (!c || phase(c) !== "upcoming") return; // đã bắt đầu thì không huỷ đăng ký nữa
  db.prepare("DELETE FROM contest_reg WHERE contest_id=? AND user_id=?").run(id, user.id);
  revalidatePath(`/contest/${id}`);
  revalidatePath("/contest");
}

// Trả { error } khi dữ liệu sai; thành công thì chuyển tới trang contest vừa tạo.
export async function createContest(_prev, formData) {
  const me = await requireAdmin();
  if (!me) return { error: "Chỉ quản trị viên được tạo cuộc thi." };
  const title = String(formData.get("title") || "").trim().slice(0, 100);
  const start = Math.floor(new Date(String(formData.get("start") || "")).getTime() / 1000);
  const duration = Number(formData.get("duration"));
  const problems = formData.getAll("problems").map(String).filter((id) => getProblem(id));
  if (!title) return { error: "Nhập tên cuộc thi." };
  if (!Number.isFinite(start)) return { error: "Chọn giờ bắt đầu." };
  if (!(duration >= 5 && duration <= 600)) return { error: "Thời lượng từ 5 đến 600 phút." };
  if (problems.length < 1 || problems.length > 10) return { error: "Chọn từ 1 đến 10 bài." };
  const r = db
    .prepare("INSERT INTO contests (title, start, duration, problems, created) VALUES (?,?,?,?,?)")
    .run(title, start, Math.round(duration), JSON.stringify(problems), Math.floor(Date.now() / 1000));
  revalidatePath("/contest");
  redirect(`/contest/${Number(r.lastInsertRowid)}`);
}

export async function deleteContest(formData) {
  const me = await requireAdmin();
  if (!me) return;
  const id = Number(formData.get("id"));
  db.prepare("DELETE FROM contest_reg WHERE contest_id=?").run(id);
  db.prepare("DELETE FROM contests WHERE id=?").run(id);
  revalidatePath("/contest");
  redirect("/contest");
}
