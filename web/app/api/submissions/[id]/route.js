import { NextResponse } from "next/server";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { queuePosition } from "@/lib/queue";

export async function GET(_req, { params }) {
  const user = await currentUser();
  if (!user) return NextResponse.json({ error: "Chưa đăng nhập" }, { status: 401 });
  const { id } = await params;
  const row = db.prepare("SELECT * FROM submissions WHERE id=? AND user_id=?").get(Number(id), user.id);
  if (!row) return NextResponse.json({ error: "Không tìm thấy" }, { status: 404 });
  return NextResponse.json({
    id: row.id, status: row.status, verdict: row.verdict, created: row.created,
    position: row.status === "queued" ? queuePosition(row.id) : 0,
    code: row.code, result: row.result ? JSON.parse(row.result) : null,
  });
}
