import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getProblem } from "@/lib/content";

// Nút Thích / Không thích / ngôi sao ở chân khung đề.
// Body: { like: 1 | -1 | 0 } đặt phản ứng của người dùng; { favorite: true | false } đặt/bỏ Yêu thích.
// Trả về trạng thái mới + số lượt thích của mọi người.
export async function POST(req, { params }) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { id } = await params;
  if (!getProblem(id)) return NextResponse.json({ error: "Không có bài này" }, { status: 404 });
  const body = await req.json().catch(() => ({}));

  if ([1, -1, 0].includes(body.like)) {
    if (body.like === 0) db.prepare("DELETE FROM reactions WHERE user_id=? AND problem_id=?").run(user.id, id);
    else db.prepare("INSERT OR REPLACE INTO reactions (user_id, problem_id, v) VALUES (?,?,?)").run(user.id, id, body.like);
  }
  if (typeof body.favorite === "boolean") {
    if (body.favorite) db.prepare("INSERT OR IGNORE INTO favorites (user_id, problem_id) VALUES (?,?)").run(user.id, id);
    else db.prepare("DELETE FROM favorites WHERE user_id=? AND problem_id=?").run(user.id, id);
  }

  const likes = Number(db.prepare("SELECT COUNT(*) n FROM reactions WHERE problem_id=? AND v=1").get(id).n);
  const mine = db.prepare("SELECT v FROM reactions WHERE user_id=? AND problem_id=?").get(user.id, id)?.v ?? 0;
  const favorite = !!db.prepare("SELECT 1 x FROM favorites WHERE user_id=? AND problem_id=?").get(user.id, id);
  return NextResponse.json({ likes, mine: Number(mine), favorite });
}
