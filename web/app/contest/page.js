import Link from "next/link";
import { redirect } from "next/navigation";
import { Trophy, Plus, Hourglass, Clock } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { listContests, phase, standings, globalRanking, contestProblems, regCount } from "@/lib/contest";
import { Countdown } from "@/components/countdown";

export const dynamic = "force-dynamic";
export const metadata = { title: "Cuộc thi · SurfNeP" };

const fmtDate = (t) =>
  new Date(t * 1000).toLocaleString("vi-VN", { weekday: "short", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });

export default async function ContestHome({ searchParams }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const tab = (await searchParams).tab === "mine" ? "mine" : "all";
  const all = listContests();
  const live = all.filter((c) => phase(c) !== "ended").sort((a, b) => a.start - b.start);
  const past = all.filter((c) => phase(c) === "ended");
  const board = globalRanking().slice(0, 10);

  // "Cuộc thi của tôi": cuộc thi đã đăng ký, kèm số bài đã giải / tổng số bài.
  const mine = past.map((c) => {
    const { rows } = standings(c);
    const me = rows.find((r) => r.userId === user.id);
    return me ? { c, solved: Object.values(me.cells).filter((x) => x.ac).length, total: contestProblems(c).length, rank: me.rank } : null;
  }).filter(Boolean);

  return (
    <div className="ct-wrap">
      <section className="ct-hero">
        <Trophy className="trophy" strokeWidth={1.4} />
        <h1>Cuộc thi SurfNeP</h1>
        <p>Thi đấu cùng lớp, nộp bài trong giờ và xem thứ hạng của bạn!</p>
        {user.role === "admin" && <Link href="/contest/new" className="ct-new"><Plus className="size-4" /> Tạo cuộc thi</Link>}
      </section>

      <section className="ct-cards">
        {live.length === 0 && <div className="ct-empty">Chưa có cuộc thi sắp diễn ra.{user.role === "admin" ? " Bấm “Tạo cuộc thi” để lên lịch." : ""}</div>}
        {live.slice(0, 4).map((c, i) => {
          const ph = phase(c);
          return (
            <Link key={c.id} href={`/contest/${c.id}`} className={`ct-card c${i % 2}`}>
              <span className="timer"><Hourglass className="size-3.5" /> {ph === "running" ? <>Còn <Countdown to={c.end} /></> : <Countdown to={c.start} />}</span>
              {ph === "running" && <span className="live">● Đang diễn ra</span>}
              <div className="meta">
                <b>{c.title}</b>
                <span>{fmtDate(c.start)} · {c.duration} phút · {regCount(c.id)} người đăng ký</span>
              </div>
            </Link>
          );
        })}
      </section>

      <div className="ct-cols">
        <section className="ct-past">
          <div className="ct-tabs">
            <Link href="/contest" className={tab === "all" ? "on" : undefined}>Cuộc thi đã qua</Link>
            <Link href="/contest?tab=mine" className={tab === "mine" ? "on" : undefined}>Cuộc thi của tôi</Link>
          </div>
          <ul>
            {tab === "all" && past.length === 0 && <li className="none">Chưa có cuộc thi nào kết thúc.</li>}
            {tab === "mine" && mine.length === 0 && <li className="none">Bạn chưa tham gia cuộc thi nào.</li>}
            {tab === "all" && past.map((c) => (
              <li key={c.id}>
                <Link href={`/contest/${c.id}`}><span className="t">{c.title}</span><span className="d"><Clock className="size-3.5" /> {fmtDate(c.start)}</span></Link>
              </li>
            ))}
            {tab === "mine" && mine.map(({ c, solved, total, rank }) => (
              <li key={c.id}>
                <Link href={`/contest/${c.id}`}>
                  <span className="t">{c.title}</span>
                  <span className="d">{fmtDate(c.start)}</span>
                  <span className="s">{solved} / {total} · hạng {rank}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <aside className="ct-rank">
          <h2>Xếp hạng chung</h2>
          {board.length === 0 && <p className="none">Chưa có dữ liệu.</p>}
          <ol>
            {board.map((u, i) => (
              <li key={u.userId} className={u.userId === user.id ? "me" : undefined}>
                <span className="n">{i + 1}</span>
                <span className="w">{u.name}<small>{u.attended} cuộc thi</small></span>
                <b>{u.score}</b>
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </div>
  );
}
