import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { listCards, reviewCard } from "@/lib/learn";

export async function POST(req) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { card, grade } = await req.json().catch(() => ({}));
  if (!listCards().some((c) => c.id === card) || ![0, 1, 2, 3].includes(grade))
    return NextResponse.json({ error: "Yêu cầu không hợp lệ" }, { status: 400 });
  const n = reviewCard(user.id, card, grade);
  return NextResponse.json({ interval: n.interval, due: n.due });
}
