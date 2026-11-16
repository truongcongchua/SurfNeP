import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getProblem } from "@/lib/content";
import { enqueue } from "@/lib/queue";
import { allow, blocked, record } from "@/lib/ratelimit";

const MAX_CODE = 100_000;

export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { problemId, code } = await req.json().catch(() => ({}));
  if (typeof problemId !== "string" || typeof code !== "string" || !getProblem(problemId))
    return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });
  if (code.length > MAX_CODE) return NextResponse.json({ error: "Mã nguồn quá dài" }, { status: 413 });

  // Mỗi người tối đa 2 bài đang chờ chấm, tránh bấm nộp dồn dập làm nghẽn hàng đợi. Kiểm tra trước giới hạn tốc độ
  // để lượt bị từ chối ở đây không bị tính vào quota.
  const pending = db.prepare("SELECT COUNT(*) n FROM submissions WHERE user_id=? AND status!='done'").get(user.id).n;
  if (pending >= 2) return NextResponse.json({ error: "Bạn còn bài đang chờ chấm, đợi kết quả rồi nộp tiếp" }, { status: 429 });

  // 1 lượt nộp / 10 giây và 60 lượt / giờ cho mỗi người. Kiểm tra quota giờ trước (chỉ đọc) để lượt bị chặn vì
  // hết quota giờ không chiếm luôn khe 10 giây, rồi mới ghi nhận cả hai.
  if (blocked(`submit-h:${user.id}`, 60, 3600))
    return NextResponse.json({ error: "Đã nộp 60 lượt trong một giờ, thử lại sau" }, { status: 429 });
  if (!allow(`submit:${user.id}`, 1, 10))
    return NextResponse.json({ error: "Nộp quá nhanh, đợi vài giây rồi thử lại" }, { status: 429 });
  record(`submit-h:${user.id}`);

  const r = db
    .prepare("INSERT INTO submissions (user_id, problem_id, code, status, created) VALUES (?,?,?,'queued',?)")
    .run(user.id, problemId, code, Math.floor(Date.now() / 1000));
  enqueue();
  return NextResponse.json({ id: Number(r.lastInsertRowid) });
}
