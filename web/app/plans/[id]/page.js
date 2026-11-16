import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { Check, ChevronLeft, CircleDashed, Network, Play, Target, Award } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { getPlan, listProblems, planProblemIds, DIFF_LABEL } from "@/lib/content";
import { statusMap, leaderboard, unmetPrereqs } from "@/lib/progress";
import { SideNav } from "@/components/side-nav";

export const dynamic = "force-dynamic";

function Ring({ done, total }) {
  const r = 40, c = 2 * Math.PI * r, f = total ? done / total : 0;
  return (
    <svg className="ring" viewBox="0 0 100 100" role="img" aria-label={`${done} trên ${total} bài`}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="var(--chip)" strokeWidth="6" />
      <circle cx="50" cy="50" r={r} fill="none" stroke="var(--brand)" strokeWidth="6" strokeLinecap="round"
        strokeDasharray={`${c * f} ${c}`} transform="rotate(-90 50 50)" />
      <text x="50" y="48" textAnchor="middle" dominantBaseline="central" fontSize="22">{done}</text>
      <text x="50" y="68" textAnchor="middle" fontSize="11" style={{ fill: "var(--muted)", fontWeight: 400 }}>/ {total} bài</text>
    </svg>
  );
}

const DAY = 86400;
const today = () => Math.floor(Date.now() / 1000 / DAY);
const AV = [["#ffb74d", "#ffa116"], ["#5ac8fa", "#007aff"], ["#4cd964", "#2db55d"], ["#d68cf0", "#af52de"]];

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

  const board = leaderboard(ids).sort((a, b) => b.solved - a.solved);
  const me = user.display || user.username;
  const firstTodo = ids.find((i) => status[i] !== "solved" && meta[i]);

  return (
    <div className="lc-layout">
      <SideNav active="plans" />
      <div>
        <div className="pd-hero">
          <div className="pd-hero-in">
            <div className="pd-top">
              <Link href="/plans" className="pd-sq" aria-label="Về Study Plan"><ChevronLeft className="size-4" /></Link>
            </div>
            <div className="pd-head">
              <div className="pd-icon"><Network /></div>
              <div>
                <div className="pd-sub"><Target className="size-3.5" />{plan.subtitle}</div>
                <h1>{plan.title}</h1>
                {!started
                  ? <form action={start}><button className="pd-start"><Play className="size-3.5 fill-current" /> Bắt đầu</button></form>
                  : firstTodo
                    ? <Link href={`/problems/${firstTodo}`} className="pd-start"><Play className="size-3.5 fill-current" /> Tiếp tục</Link>
                    : <span className="pd-started"><Check className="size-4" style={{ color: "var(--green)" }} /> Đã hoàn thành</span>}
              </div>
            </div>
          </div>
        </div>
        <div className="pd-hero-fade" />

        <div className="pd-body">
          <div>
            <div className="pd-tags">
              <Link href={`/plans/${id}${showTags ? "" : "?tags=1"}`} scroll={false} title="Tag mặc định bị ẩn vì có thể gợi ý cách giải">
                <span className={`box${showTags ? " on" : ""}`}>{showTags && <Check className="size-3" strokeWidth={3} />}</span> Hiện tag
              </Link>
            </div>
            <div className="pd-list">
              {plan.sections.map((s) => {
                const done = s.problems.filter((p) => status[p.id] === "solved").length;
                return (
                  <section key={s.title}>
                    <div className="pd-sec-h">
                      <span>{s.title}{s.intro && <span className="intro"> · {s.intro}</span>}</span>
                      <span className="num intro" style={{ whiteSpace: "nowrap" }}>{done}/{s.problems.length}</span>
                    </div>
                    {s.problems.map((p) => {
                      const m = meta[p.id];
                      const st = status[p.id] || "todo";
                      const unmet = m ? unmetPrereqs(m, status) : [];
                      return (
                        <div key={p.id} className="pd-row">
                          {st === "solved" ? <Check className="ok size-4" strokeWidth={2.4} /> : st === "attempted" ? <CircleDashed className="tr size-4" strokeWidth={2} /> : <span className="circ" />}
                          <div className="ttl">
                            {m ? <Link href={`/problems/${p.id}`}>{p.title}</Link> : <span>{p.title} <span className="lock">(sắp có)</span></span>}
                            {p.exam && <span className="chip accent" style={{ marginLeft: 8 }}>Thi thử</span>}
                            {unmet.length > 0 && st !== "solved" && <div className="lock">Nên làm trước: {unmet.join(", ")}</div>}
                            {showTags && m && <div className="topics">{m.topics.map((t) => <span key={t} className="chip">{t}</span>)}</div>}
                          </div>
                          <span className={`d ${p.difficulty}`}>{DIFF_LABEL[p.difficulty]}</span>
                        </div>
                      );
                    })}
                  </section>
                );
              })}
            </div>
          </div>

          <aside className="pd-side">
            <section>
              <h3>Tóm tắt</h3>
              <div className="ring-row">
                <Ring done={solved.length} total={ids.length} />
                <div className="diffs">
                  {["easy", "medium", "hard"].map((d) => {
                    const x = byDiff(d);
                    return <span key={d}><b className={`diff-${d}`}>{DIFF_LABEL[d]}</b><span className="num">{x.done}/{x.total}</span></span>;
                  })}
                </div>
              </div>
              {plan.description && <ul style={{ marginTop: 16 }}><li>{plan.description}</li>
                {plan.suggested_days && <li>Gợi ý hoàn thành trong {plan.suggested_days} ngày</li>}
                {plan.exam_date && <li>Ngày thi: {plan.exam_date}</li>}
              </ul>}
              {sched && (
                <div className="sched" style={{ background: sched.diff >= 0 ? "var(--ok-bg)" : "var(--warn-bg)" }}>
                  Còn <b>{Math.max(0, sched.left)} ngày</b>, còn <b>{sched.remaining} bài</b>
                  {sched.left > 0 && <> (khoảng <b>{sched.perDay} bài/ngày</b>)</>}.{" "}
                  {sched.diff >= 0
                    ? <>Bạn đang <b>nhanh hơn lịch {sched.diff} bài</b>.</>
                    : <>Bạn đang <b>chậm {-sched.diff} bài</b> so với lịch đều.</>}
                </div>
              )}
            </section>

            {plan.award && (
              <section>
                <h3>Phần thưởng</h3>
                <div className="pd-award">
                  <span className="badge"><Award className="size-6" /></span>
                  <div>
                    <div className="t">{plan.award}</div>
                    <div className="s">{solved.length === ids.length ? "Bạn đã đạt huy hiệu này!" : "Hoàn thành study plan để nhận huy hiệu."}</div>
                  </div>
                </div>
              </section>
            )}

            <section>
              <h3>Xếp hạng</h3>
              <ol className="pd-rank">
                {board.map((b, i) => (
                  <li key={b.name}>
                    <span className="r num">{i + 1}</span>
                    <span className="av" style={{ "--a1": AV[i % AV.length][0], "--a2": AV[i % AV.length][1] }}>{b.name.slice(0, 1).toUpperCase()}</span>
                    <span>{b.name}{b.name === me && <span className="chip" style={{ marginLeft: 6 }}>Bạn</span>}</span>
                    <span className="c num">{b.solved}/{ids.length}</span>
                  </li>
                ))}
              </ol>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
