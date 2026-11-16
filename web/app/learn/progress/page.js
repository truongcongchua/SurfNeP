import Link from "next/link";
import { currentUser } from "@/lib/auth";
import { CHAPTERS, mastery } from "@/lib/learn";
import { BAND, Bar, Card, bandOf } from "@/components/learn/ui";

const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);

export default async function Progress() {
  const user = await currentUser();
  const m = mastery(user.id);
  const sorted = [...m].sort((a, b) => (a.score ?? -1) - (b.score ?? -1));
  const next = sorted.find((x) => x.score == null || x.score < 70);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-medium text-[var(--title)]">Bản đồ điểm yếu</h1>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Mỗi khái niệm được chấm theo trung bình của: bài code đã AC, quiz + tìm bug (10 lượt gần nhất) và flashcard đã nhớ lâu (khoảng ôn từ 3 ngày). Khái niệm yếu xếp trên cùng.
        </p>
      </div>

      {next && (
        <Card className="border-[var(--brand)]">
          <div className="text-xs text-[var(--muted)]">Gợi ý tiếp theo</div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-medium text-[var(--title)]">{next.title}</span>
            <Link className="text-sm text-[var(--accent)] hover:underline" href={`/learn/c/${next.id}`}>Đọc lại</Link>
            {next.counts.cards > 0 && <Link className="text-sm text-[var(--accent)] hover:underline" href={`/learn/review?c=${next.id}`}>Ôn flashcard</Link>}
            <Link className="text-sm text-[var(--accent)] hover:underline" href={`/learn/quiz/${next.id}`}>Làm quiz</Link>
            {next.problems.find((p) => p.status !== "solved") && (
              <Link className="text-sm text-[var(--accent)] hover:underline" href={`/problems/${next.problems.find((p) => p.status !== "solved").id}`}>Làm bài code</Link>
            )}
          </div>
        </Card>
      )}

      <div className="overflow-x-auto rounded-lg border border-[var(--line)]">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="bg-[var(--panel)] text-left text-xs text-[var(--muted)]">
              <th className="px-3 py-2 font-normal">Khái niệm</th>
              <th className="px-3 py-2 font-normal">Mức</th>
              <th className="px-3 py-2 font-normal">Bài code</th>
              <th className="px-3 py-2 font-normal">Quiz / bug</th>
              <th className="px-3 py-2 font-normal">Flashcard</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((c) => {
              const b = BAND[bandOf(c.score)];
              return (
                <tr key={c.id} className="border-t border-[var(--line)]">
                  <td className="px-3 py-2.5">
                    <Link href={`/learn/c/${c.id}`} className="text-[var(--title)] hover:underline">{c.title}</Link>
                    <div className="text-xs text-[var(--muted)]">{CHAPTERS[c.chapter]?.split(" · ")[0]}</div>
                  </td>
                  <td className="w-40 px-3 py-2.5">
                    <div className={`mb-1 text-xs ${b.text}`}>{b.label}{c.score != null && ` · ${c.score}%`}</div>
                    <Bar value={c.score} />
                  </td>
                  <td className="px-3 py-2.5 text-[var(--muted)]">{c.counts.solved}/{c.counts.problems} <span className="text-xs">({pct(c.sig.problems)})</span></td>
                  <td className="px-3 py-2.5 text-[var(--muted)]">{c.counts.quizN ? pct(c.sig.quiz) : "—"} <span className="text-xs">{c.counts.quizN ? `(${c.counts.quizN} lượt)` : ""}</span></td>
                  <td className="px-3 py-2.5 text-[var(--muted)]">{c.counts.known}/{c.counts.cards} <span className="text-xs">nhớ lâu</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
