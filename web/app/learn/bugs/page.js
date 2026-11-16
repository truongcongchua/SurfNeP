import Link from "next/link";
import { Bug, Check } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { VERDICT_LABEL as LABEL } from "@/lib/verdicts";
import { bugStatus, listBugs, listConcepts } from "@/lib/learn";
import { getProblem } from "@/lib/content";

export default async function Bugs() {
  const user = await currentUser();
  const st = bugStatus(user.id);
  const bugs = listBugs();
  const titles = Object.fromEntries(listConcepts().map((c) => [c.id, c.title]));
  const found = bugs.filter((b) => st[b.id] === "found").length;

  return (
    <div>
      <h1 className="text-2xl font-medium text-[var(--title)]">Tìm bug</h1>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Mỗi bài là một lời giải <b>sai</b> của bài trong ngân hàng đề, kèm triệu chứng bộ chấm báo. Hãy chọn những dòng gây lỗi. Đã tìm đúng {found}/{bugs.length}.
      </p>
      <ul className="mt-5 divide-y divide-[var(--line)] rounded-lg border border-[var(--line)] bg-[var(--panel)]">
        {bugs.map((b) => {
          const s = st[b.id];
          return (
            <li key={b.id}>
              <Link href={`/learn/bugs/${b.id}`} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-[var(--raised)]">
                <span className="grid size-6 shrink-0 place-items-center">
                  {s === "found" ? <Check className="size-4 text-[var(--easy)]" /> : <Bug className={`size-4 ${s === "tried" ? "text-[var(--medium)]" : "text-[var(--muted)]"}`} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-[var(--title)]">{getProblem(b.problem)?.title || b.problem}</span>
                  <span className="block truncate text-xs text-[var(--muted)]">{titles[b.concept] || b.concept}</span>
                </span>
                {b.verdict && <span className="shrink-0 rounded bg-[var(--pill)] px-2 py-0.5 text-xs text-[var(--muted)]">{LABEL[b.verdict] || b.verdict}</span>}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
