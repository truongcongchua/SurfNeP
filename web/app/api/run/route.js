import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { getProblem } from "@/lib/content";
import { runSample } from "@/lib/queue";
import { allow } from "@/lib/ratelimit";

const MAX_CODE = 100_000;
const MAX_CASES = 10, MAX_CASE_LEN = 10_000;

// "Chạy thử": biên dịch rồi chạy test mẫu, trả kết quả ngay (không ghi vào Lịch sử nộp, không tính tiến độ).
// Có `cases` (testcase tự nhập, chỉ bài stdio/function) thì chạy các input đó, output mong đợi lấy từ lời giải mẫu.
export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { problemId, code, cases, debug } = await req.json().catch(() => ({}));
  const p = typeof problemId === "string" ? getProblem(problemId) : null;
  if (!p || typeof code !== "string") return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });
  if (code.length > MAX_CODE) return NextResponse.json({ error: "Mã nguồn quá dài" }, { status: 413 });

  if (!allow(`run:${user.id}`, 1, 3)) return NextResponse.json({ error: "Chạy thử quá nhanh, đợi vài giây" }, { status: 429 });

  let custom = null;
  if (cases != null) {
    if (!["stdio", "function"].includes(p.type)) return NextResponse.json({ error: "Bài này không hỗ trợ testcase tự nhập" }, { status: 400 });
    if (!Array.isArray(cases) || cases.length === 0 || cases.length > MAX_CASES || cases.some((c) => typeof c !== "string" || c.length > MAX_CASE_LEN))
      return NextResponse.json({ error: `Tối đa ${MAX_CASES} testcase, mỗi testcase tối đa ${MAX_CASE_LEN} ký tự` }, { status: 400 });
    custom = cases;
  }

  const result = await runSample(problemId, code, custom, debug === true);
  if (!result) return NextResponse.json({ error: "Máy chấm đang bận, thử lại sau vài giây" }, { status: 429 });
  return NextResponse.json({ result });
}
