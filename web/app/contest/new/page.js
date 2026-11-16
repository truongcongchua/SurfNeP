import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { requireAdmin } from "@/lib/auth";
import { listProblems, DIFF_LABEL } from "@/lib/content";
import { NewContestForm } from "./form";

export const dynamic = "force-dynamic";

export default async function NewContest() {
  if (!(await requireAdmin())) notFound();
  const problems = listProblems().filter((p) => !p.exam).map((p) => ({ id: p.id, title: p.title, difficulty: p.difficulty, label: DIFF_LABEL[p.difficulty], chapter: p.chapter }));
  const t = new Date(Date.now() + 3600_000);
  t.setMinutes(0, 0, 0);
  const pad = (n) => String(n).padStart(2, "0");
  const def = `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}T${pad(t.getHours())}:00`;
  return (
    <div className="ct-wrap narrow">
      <Link href="/contest" className="ct-back"><ChevronLeft className="size-4" /> Tất cả cuộc thi</Link>
      <h1 className="ct-h1">Tạo cuộc thi</h1>
      <NewContestForm problems={problems} defaultStart={def} />
    </div>
  );
}
