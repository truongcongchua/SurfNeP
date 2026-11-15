import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getProblem } from "@/lib/content";
import { enqueue } from "@/lib/queue";

const MAX_CODE = 100_000;

export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { problemId, code } = await req.json().catch(() => ({}));
  if (typeof problemId !== "string" || typeof code !== "string" || !getProblem(problemId))
    return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });
  if (code.length > MAX_CODE) return NextResponse.json({ error: "Mã nguồn quá dài" }, { status: 413 });

  // Mỗi người chỉ có một bài đang chờ chấm, tránh bấm nộp dồn dập làm nghẽn hàng đợi.
  const pending = db.prepare("SELECT COUNT(*) n FROM submissions WHERE user_id=? AND status!='done'").get(user.id).n;
  if (pending >= 2) return NextResponse.json({ error: "Bạn còn bài đang chờ chấm, đợi kết quả rồi nộp tiếp" }, { status: 429 });

  const r = db
    .prepare("INSERT INTO submissions (user_id, problem_id, code, status, created) VALUES (?,?,?,'queued',?)")
    .run(user.id, problemId, code, Math.floor(Date.now() / 1000));
  enqueue();
  return NextResponse.json({ id: Number(r.lastInsertRowid) });
}
