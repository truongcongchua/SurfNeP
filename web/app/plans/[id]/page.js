import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getPlan, listProblems, planProblemIds, DIFF_LABEL } from "@/lib/content";
import { statusMap, leaderboard, unmetPrereqs } from "@/lib/progress";

export const dynamic = "force-dynamic";

function Ring({ done, total }) {
  const r = 40, c = 2 * Math.PI * r, f = total ? done / total : 0;
  return (
    <svg className="ring" viewBox="0 0 100 100" role="img" aria-label={`${done} trên ${total} bài`}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="var(--chip)" strokeWidth="9" />
      <circle cx="50" cy="50" r={r} fill="none" stroke="var(--accent)" strokeWidth="9" strokeLinecap="round"
        strokeDasharray={`${c * f} ${c}`} transform="rotate(-90 50 50)" />
      <text x="50" y="50" textAnchor="middle" dominantBaseline="central" fontSize="22">{done}</text>
      <text x="50" y="68" textAnchor="middle" fontSize="10" style={{ fill: "var(--muted)", fontWeight: 400 }}>/ {total}</text>
    </svg>
  );
}

const DAY = 86400;
const today = () => Math.floor(Date.now() / 1000 / DAY);

export default async function PlanPage({ params, searchParams }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const { id } = await params;
  const plan = getPlan(id);
  if (!plan) notFound();
  const sp = await searchParams;
  const showTags = sp.tags === "1";

  async function start() {
    "use server";
    const u = await currentUser();
    if (!u) return;
    db.prepare("INSERT OR IGNORE INTO plan_start (user_id, plan_id, started) VALUES (?,?,?)").run(u.id, id, Math.floor(Date.now() / 1000));
    revalidatePath(`/plans/${id}`);
  }

  const status = statusMap(user.id);
  const meta = Object.fromEntries(listProblems().map((p) => [p.id, p]));
  const ids = planProblemIds(plan);
  const solved = ids.filter((i) => status[i] === "solved");
  const byDiff = (d) => {
    const all = ids.filter((i) => meta[i]?.difficulty === d);
    return { done: all.filter((i) => status[i] === "solved").length, total: all.length };
  };
  const started = db.prepare("SELECT started FROM plan_start WHERE user_id=? AND plan_id=?").get(user.id, id);

  // Lịch học: chia đều số bài từ ngày bắt đầu đến ngày thi.
  let sched = null;
  if (started && plan.exam_date) {
    const d0 = Math.floor(started.started / DAY);
    const dEnd = Math.floor(new Date(plan.exam_date + "T00:00:00Z").getTime() / 1000 / DAY);
    const span = Math.max(1, dEnd - d0), left = dEnd - today();
    const expected = Math.min(ids.length, Math.max(0, Math.round((ids.length * (today() - d0 + 1)) / span)));
    const remaining = ids.length - solved.length;
    sched = { left, expected, remaining, perDay: left > 0 ? Math.ceil(remaining / left) : remaining, diff: solved.length - expected };
  }

  const board = leaderboard(ids);

  return (
    <>
      <div className="card plan-head">
        <Ring done={solved.length} total={ids.length} />
        <div style={{ flex: 1, minWidth: 220 }}>
          <div className="sub" style={{ margin: 0 }}>{plan.subtitle}</div>
          <h1 style={{ margin: "2px 0 6px" }}>{plan.title}</h1>
          <p className="sub" style={{ margin: 0 }}>{plan.description}</p>
          {plan.award && <p className="sub" style={{ margin: "6px 0 0" }}>🏅 {plan.award} {solved.length === ids.length ? "· đã đạt!" : ""}</p>}
        </div>
        <div className="diffs">
          {["easy", "medium", "hard"].map((d) => {
            const x = byDiff(d);
            return <span key={d}><b className={`diff-${d}`}>{DIFF_LABEL[d]}</b> {x.done}/{x.total}</span>;
          })}
        </div>
        {!started && <form action={start}><button className="btn">Bắt đầu</button></form>}
      </div>

      {sched && (
        <div className="sched" style={{ background: sched.diff >= 0 ? "var(--ok-bg)" : "var(--warn-bg)" }}>
          Thi giữa kỳ <b>{plan.exam_date}</b> — còn <b>{Math.max(0, sched.left)} ngày</b>, còn <b>{sched.remaining} bài</b>
          {sched.left > 0 && <> (khoảng <b>{sched.perDay} bài/ngày</b>)</>}.{" "}
          {sched.diff >= 0
            ? <>Bạn đang <b>nhanh hơn lịch {sched.diff} bài</b>.</>
            : <>Bạn đang <b>chậm {-sched.diff} bài</b> so với lịch đều.</>}
        </div>
      )}

      <div style={{ margin: "10px 0" }}>
        <Link className="btn ghost" href={`/plans/${id}${showTags ? "" : "?tags=1"}`}>{showTags ? "Ẩn tag" : "Hiện tag"}</Link>
        <span className="sub" style={{ marginLeft: 10 }}>Tag mặc định bị ẩn vì có thể gợi ý cách giải.</span>
      </div>

      {plan.sections.map((s) => {
        const done = s.problems.filter((p) => status[p.id] === "solved").length;
        return (
          <section key={s.title} className="card sec">
            <div className="sec-head">
              <div><b>{s.title}</b><div className="intro">{s.intro}</div></div>
              <span className="cnt">{done} / {s.problems.length}</span>
            </div>
            <table className="list"><tbody>
              {s.problems.map((p) => {
                const m = meta[p.id];
                const st = status[p.id] || "todo";
                const unmet = m ? unmetPrereqs(m, status) : [];
                return (
                  <tr key={p.id}>
                    <td className={`st ${st}`}>{st === "solved" ? "✓" : st === "attempted" ? "•" : "○"}</td>
                    <td>
                      {m ? <Link href={`/problems/${p.id}`}>{p.title}</Link> : <span>{p.title} <span className="lock">(sắp có)</span></span>}
                      {p.exam && <span className="chip" style={{ marginLeft: 8 }}>Thi thử</span>}
                      {unmet.length > 0 && st !== "solved" && <div className="lock">🔒 nên làm trước: {unmet.join(", ")}</div>}
                      {showTags && m && <div className="topics" style={{ marginTop: 4 }}>{m.topics.map((t) => <span key={t} className="chip">{t}</span>)}</div>}
                    </td>
                    <td className={`diff-${p.difficulty}`} style={{ textAlign: "right" }}>{DIFF_LABEL[p.difficulty]}</td>
                  </tr>
                );
              })}
            </tbody></table>
          </section>
        );
      })}

      <h2>Tiến độ của cả hai</h2>
      <div className="card"><table className="list board"><tbody>
        {board.sort((a, b) => b.solved - a.solved).map((b) => (
          <tr key={b.name}><td>{b.name}</td><td style={{ width: "60%" }}><div className="bar"><i style={{ width: `${(100 * b.solved) / ids.length}%` }} /></div></td><td>{b.solved}/{ids.length}</td></tr>
        ))}
      </tbody></table></div>
      <div style={{ height: 40 }} />
    </>
  );
}
