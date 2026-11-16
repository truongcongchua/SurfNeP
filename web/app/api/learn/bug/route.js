import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { getBug, logEvent } from "@/lib/learn";

// Chấm "Tìm bug" ở phía server (không gửi đáp án xuống trình duyệt trước khi trả lời).
// Đúng khi chọn ít nhất 1 dòng thuộc `lines`, không quá 5 dòng, và không chọn dòng nào ngoài `lines` + `near`.
export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { id, lines } = await req.json().catch(() => ({}));
  const b = typeof id === "string" ? getBug(id) : null;
  if (!b || !Array.isArray(lines) || lines.length > 40 || !lines.every((n) => Number.isInteger(n)))
    return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });

  const truth = new Set(b.lines);
  const allowed = new Set([...b.lines, ...(b.near || [])]);
  const hit = lines.filter((n) => truth.has(n)).length;
  const stray = lines.filter((n) => !allowed.has(n)).length;
  const ok = hit > 0 && lines.length <= 5 && stray === 0;
  logEvent(user.id, "bug", b.id, b.concept, ok);
  return NextResponse.json({ ok, hit, total: b.lines.length, stray, lines: b.lines, title: b.title, explain: b.explain, fix: b.fix || null });
}
