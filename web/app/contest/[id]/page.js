import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ChevronLeft, Check, Trophy } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { getContest, phase, standings, isRegistered, regCount, contestProblems, fmtDur, PENALTY } from "@/lib/contest";
import { DIFF_LABEL } from "@/lib/content";
import { Countdown } from "@/components/countdown";
import { registerContest, unregisterContest, deleteContest } from "../actions";

export const dynamic = "force-dynamic";

const fmt = (t) => new Date(t * 1000).toLocaleString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });

export default async function ContestPage({ params }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const c = getContest((await params).id);
  if (!c) notFound();
  const ph = phase(c);
  const reg = isRegistered(c.id, user.id);
  const admin = user.role === "admin";
  const showProblems = ph !== "upcoming" || admin;
  const { probs, rows } = standings(c);
  const mine = rows.find((r) => r.userId === user.id);

  return (
    <div className="ct-wrap narrow">
      <Link href="/contest" className="ct-back"><ChevronLeft className="size-4" /> Tất cả cuộc thi</Link>

      <header className="ct-head">
        <div>
          <h1>{c.title}</h1>
          <p>{fmt(c.start)} · {c.duration} phút · {probs.length} bài · {regCount(c.id)} người đăng ký</p>
        </div>
        <div className="side">
          {ph === "upcoming" && <div className="clock"><small>Bắt đầu sau</small><Countdown to={c.start} /></div>}
          {ph === "running" && <div className="clock live"><small>Còn lại</small><Countdown to={c.end} /></div>}
          {ph === "ended" && <div className="clock end"><small>Đã kết thúc</small><span>—</span></div>}
          {ph !== "ended" && (reg
            ? (ph === "upcoming"
                ? <form action={unregisterContest}><input type="hidden" name="id" value={c.id} /><button className="ct-btn ghost"><Check className="size-4" /> Đã đăng ký · Huỷ</button></form>
                : <span className="ct-btn ghost static"><Check className="size-4" /> Đã đăng ký</span>)
            : <form action={registerContest}><input type="hidden" name="id" value={c.id} /><button className="ct-btn">{ph === "running" ? "Đăng ký & thi ngay" : "Đăng ký"}</button></form>)}
        </div>
      </header>

      {showProblems ? (
        <section className="ct-sec">
          <h2>Đề bài</h2>
          {ph === "running" && !reg && <p className="ct-note">Bạn chưa đăng ký — bài nộp chỉ được tính điểm cho người đã đăng ký.</p>}
          <ol className="ct-probs">
            {probs.map((p, i) => {
              const cell = mine?.cells[p.id];
              return (
                <li key={p.id}>
                  <Link href={`/problems/${p.id}`}>
                    <span className="q">Q{i + 1}</span>
                    <span className="t">{p.title}</span>
                    <span className={`diff-${p.difficulty}`}>{DIFF_LABEL[p.difficulty]}</span>
                    <span className="pt">{p.points} điểm</span>
                    <span className={`st${cell?.ac ? " ok" : ""}`}>{cell?.ac ? <><Check className="size-4" /> {fmtDur(cell.t)}</> : cell?.wrong ? `${cell.wrong} lần sai` : ""}</span>
                  </Link>
                </li>
              );
            })}
          </ol>
          <p className="ct-note">Chấm điểm: Dễ 3 · Trung bình 5 · Khó 7. Xếp hạng theo tổng điểm, rồi thời gian hoàn thành (+{PENALTY / 60} phút mỗi lần nộp sai trước khi AC; lỗi biên dịch không bị phạt).</p>
        </section>
      ) : (
        <section className="ct-sec locked">
          <Trophy className="size-10" strokeWidth={1.4} />
          <h2>Đề bài sẽ hiện khi cuộc thi bắt đầu</h2>
          <p>Hãy đăng ký trước để được tính điểm.</p>
        </section>
      )}

      {ph !== "upcoming" && (
        <section className="ct-sec">
          <h2>{ph === "running" ? "Bảng xếp hạng (trực tiếp)" : "Kết quả"}</h2>
          <div className="ct-table-wrap">
            <table className="ct-table">
              <thead>
                <tr><th>Hạng</th><th>Thí sinh</th><th>Điểm</th><th>Thời gian</th>{probs.map((p, i) => <th key={p.id}>Q{i + 1}</th>)}</tr>
              </thead>
              <tbody>
                {rows.length === 0 && <tr><td colSpan={4 + probs.length} className="none">Chưa có ai đăng ký.</td></tr>}
                {rows.map((r) => (
                  <tr key={r.userId} className={r.userId === user.id ? "me" : undefined}>
                    <td className="rk">{r.rank}</td>
                    <td className="nm">{r.name}</td>
                    <td className="sc">{r.score}</td>
                    <td className="tm">{r.score ? fmtDur(r.finish) : "—"}</td>
                    {probs.map((p) => {
                      const x = r.cells[p.id];
                      return <td key={p.id} className={`cl${x?.ac ? " ac" : ""}`}>{x?.ac ? <>{fmtDur(x.t)}{x.wrong > 0 && <sup>-{x.wrong}</sup>}</> : x?.wrong ? <span className="wa">-{x.wrong}</span> : ""}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {admin && (
        <form action={deleteContest} className="ct-del"><input type="hidden" name="id" value={c.id} /><button>Xoá cuộc thi này</button></form>
      )}
    </div>
  );
}
