import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { listQuestions, logEvent } from "@/lib/learn";

// Quiz chấm ở trình duyệt; endpoint này chỉ ghi lại kết quả để tính độ thành thạo.
export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { qid, ok } = await req.json().catch(() => ({}));
  const q = listQuestions().find((x) => x.id === qid);
  if (!q || typeof ok !== "boolean") return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });
  logEvent(user.id, "quiz", q.id, q.concept, ok);
  return NextResponse.json({ ok: true });
}
