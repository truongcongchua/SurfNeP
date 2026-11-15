import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { getProblem } from "@/lib/content";
import { runSample } from "@/lib/queue";

const MAX_CODE = 100_000;

// "Chạy thử": biên dịch rồi chạy test mẫu, trả kết quả ngay (không ghi vào Lịch sử nộp, không tính tiến độ).
export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { problemId, code } = await req.json().catch(() => ({}));
  if (typeof problemId !== "string" || typeof code !== "string" || !getProblem(problemId))
    return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });
  if (code.length > MAX_CODE) return NextResponse.json({ error: "Mã nguồn quá dài" }, { status: 413 });

  const result = await runSample(problemId, code);
  if (!result) return NextResponse.json({ error: "Máy chấm đang bận, thử lại sau vài giây" }, { status: 429 });
  return NextResponse.json({ result });
}
