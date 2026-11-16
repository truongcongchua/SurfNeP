import Link from "next/link";
import { Check, CircleDashed, Star, LayoutGrid, BookOpen, GraduationCap, Flame, Trophy, Search, ArrowRight, Timer, Target } from "lucide-react";
import { redirect } from "next/navigation";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { listProblems, listPlans, planProblemIds, DIFF_LABEL, DIFF_ORDER } from "@/lib/content";
import { statusMap, unmetPrereqs, leaderboard } from "@/lib/progress";
import { FilterForm } from "@/components/filter-form";
import { TopicRow } from "@/components/topic-row";
import { RandomButton } from "@/components/random-button";
import { SideNav } from "@/components/side-nav";

export const dynamic = "force-dynamic";
const RING = 2 * Math.PI * 16;
const WEEK = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
// Nhãn mức độ rút gọn trong bảng (LeetCode ghi "Easy / Med. / Hard").
const DIFF_SHORT = { easy: "Dễ", medium: "TB", hard: "Khó" };
const ymd = (d) => d.toLocaleDateString("sv-SE"); // YYYY-MM-DD theo giờ máy

const SORTS = {
  "diff-asc": (a, b) => DIFF_ORDER[a.difficulty] - DIFF_ORDER[b.difficulty],
  "diff-desc": (a, b) => DIFF_ORDER[b.difficulty] - DIFF_ORDER[a.difficulty],
  "ac-desc": (a, b) => b.acRate - a.acRate,
  "ac-asc": (a, b) => a.acRate - b.acRate,
  title: (a, b) => a.title.localeCompare(b.title),
};
const SORT_LABEL = { "": "Sắp xếp", "diff-asc": "Dễ → Khó", "diff-desc": "Khó → Dễ", "ac-desc": "Tỉ lệ AC cao", "ac-asc": "Tỉ lệ AC thấp", title: "Theo tên A–Z" };
// Màu icon tab chương (bảng màu icon của LeetCode) và màu avatar bảng xếp hạng (xoay vòng).
const CH_COLOR = ["#ffa116", "#007aff", "#2db55d", "#af52de", "#5ac8fa"];
const AV = [["#ffb74d", "#ffa116"], ["#5ac8fa", "#007aff"], ["#4cd964", "#2db55d"], ["#d68cf0", "#af52de"]];
const ST_LABEL = { solved: "Đã giải", attempted: "Đang thử", todo: "Chưa làm", fav: "Yêu thích" };

export default async function Problems({ searchParams }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const sp = await searchParams;
  const q = (sp.q || "").toLowerCase(), d = sp.d || "", t = sp.t || "", c = sp.c || "", st = sp.st || "", sort = sp.s || "";

  const status = statusMap(user.id);
  const favs = new Set(db.prepare("SELECT problem_id FROM favorites WHERE user_id=?").all(user.id).map((r) => r.problem_id));
  // Tỉ lệ AC = số lần AC / số lần nộp đã chấm của mọi người dùng.
  const accRows = db.prepare("SELECT problem_id, SUM(verdict='AC') AS ac, COUNT(*) AS n FROM submissions WHERE status='done' GROUP BY problem_id").all();
  const acc = Object.fromEntries(accRows.map((r) => [r.problem_id, r]));
  const all = listProblems().map((p, i) => ({ ...p, n: i + 1, acRate: acc[p.id]?.n ? acc[p.id].ac / acc[p.id].n : -1 }));

  const list = all
    .filter(
      (p) =>
        (!q || p.title.toLowerCase().includes(q) || p.id.includes(q) || String(p.n) === q) &&
        (!d || p.difficulty === d) && (!t || p.topics.includes(t)) && (!c || String(p.chapter) === c) &&
        (!st || (st === "fav" ? favs.has(p.id) : (status[p.id] || "todo") === st))
    )
    .sort(SORTS[sort] || (() => 0));

  const solved = all.filter((p) => status[p.id] === "solved").length;
  const stCount = (k) => (k === "fav" ? all.filter((p) => favs.has(p.id)).length : all.filter((p) => (status[p.id] || "todo") === k).length);
  const topicNames = [...new Set(all.flatMap((p) => p.topics))];
  const count = (x) => all.filter((p) => p.topics.includes(x)).length;
  const chapters = [...new Set(all.map((p) => p.chapter))].sort((a, b) => a - b);

  const href = (next) => {
    const o = { q: sp.q, d, c, t, st, s: sort, ...next };
    const qs = new URLSearchParams(Object.entries(o).filter(([, v]) => v)).toString();
    return qs ? `/?${qs}` : "/";
  };

  /* ----- dữ liệu cho cột phải & banner ----- */
  const plans = listPlans();
  const planProg = (p) => {
    const ids = planProblemIds(p);
    return { done: ids.filter((i) => status[i] === "solved").length, total: ids.length };
  };
  const nextProblem = all.find((p) => status[p.id] !== "solved" && !p.exam && unmetPrereqs(p, status).length === 0);
  const exams = all.filter((p) => p.exam);
  const nextExam = exams.find((p) => status[p.id] !== "solved") || exams[0];
  const mainPlan = plans[0];

  const now = new Date();
  const y = now.getFullYear(), m = now.getMonth();
  const monthStart = Math.floor(new Date(y, m, 1).getTime() / 1000), monthEnd = Math.floor(new Date(y, m + 1, 1).getTime() / 1000);
  const monthRows = db.prepare("SELECT created, verdict FROM submissions WHERE user_id=? AND status='done' AND created>=? AND created<?").all(user.id, monthStart, monthEnd);
  const active = new Map();
  for (const r of monthRows) {
    const day = new Date(r.created * 1000).getDate();
    active.set(day, active.get(day) || r.verdict === "AC");
  }
  const daysSet = new Set(db.prepare("SELECT created FROM submissions WHERE user_id=? AND status='done'").all(user.id).map((r) => ymd(new Date(r.created * 1000))));
  let streak = 0;
  for (let k = daysSet.has(ymd(now)) ? 0 : 1; daysSet.has(ymd(new Date(y, m, now.getDate() - k))); k++) streak++;
  const lead = (new Date(y, m, 1).getDay() + 6) % 7, dim = new Date(y, m + 1, 0).getDate();
  const today0 = new Date(y, m, now.getDate());
  const examDate = plans
    .map((p) => p.exam_date).filter(Boolean)
    .map((v) => new Date((v instanceof Date ? v.toISOString() : String(v)).slice(0, 10) + "T00:00:00"))
    .filter((v) => v >= today0).sort((a, b) => a - b)[0];
  const examDays = examDate ? Math.round((examDate - today0) / 86400000) : null;
  const board = leaderboard(all.map((p) => p.id)).sort((a, b) => b.solved - a.solved);
  const me = user.display || user.username;
  const byDiff = Object.keys(DIFF_LABEL).map((k) => ({
    k, label: DIFF_LABEL[k],
    total: all.filter((p) => p.difficulty === k).length,
    done: all.filter((p) => p.difficulty === k && status[p.id] === "solved").length,
  }));
  const lists = Object.entries(ST_LABEL).map(([k, v]) => ({
    key: k, label: v, count: stCount(k), on: st === k, href: st === k ? href({ st: "" }) : href({ st: k }),
    icon: k === "solved"
      ? <Check style={{ color: "var(--green)" }} strokeWidth={2.2} />
      : k === "fav" ? <Star style={{ color: "var(--brand)" }} />
      : <CircleDashed style={{ color: k === "attempted" ? "var(--medium)" : "var(--faint)" }} />,
  }));

  return (
    <div className="lc-layout">
      <SideNav active="problems" lists={lists} />
      <div className="home">
        <h1 className="sr-only">Bài tập</h1>

        {/* ===== cột giữa ===== */}
        <section className="center">
          <div className="promo">
            {mainPlan && (() => { const { done, total } = planProg(mainPlan); return (
              <Link href={`/plans/${mainPlan.id}`}>
                <span className="k">Study Plan</span>
                <span className="t">{mainPlan.title}</span>
                <span className="bar" style={{ marginTop: "auto", width: "60%" }}><i style={{ width: `${total ? (100 * done) / total : 0}%` }} /></span>
                <span className="m" style={{ marginTop: 6 }}>{done} / {total} bài · {mainPlan.sections.length} chủ đề</span>
                <GraduationCap className="big" />
              </Link>); })()}
            {nextProblem && (
              <Link href={`/problems/${nextProblem.id}`}>
                <span className="k">Bài tiếp theo</span>
                <span className="t">{nextProblem.title}</span>
                <span className="m">{DIFF_LABEL[nextProblem.difficulty]} · Chương {nextProblem.chapter} <ArrowRight className="size-3.5" style={{ display: "inline", verticalAlign: "-2px" }} /></span>
                <Target className="big" />
              </Link>)}
            {nextExam && (
              <Link href={`/problems/${nextExam.id}`}>
                <span className="k">Thi thử</span>
                <span className="t">{nextExam.title}</span>
                <span className="m"><Timer className="size-3.5" style={{ display: "inline", verticalAlign: "-2px" }} /> {nextExam.examMinutes ? `${nextExam.examMinutes} phút` : "Tính giờ"} · {exams.length} đề</span>
                <Timer className="big" />
              </Link>)}
          </div>

          <TopicRow
            items={[...topicNames].sort((a, b) => count(b) - count(a)).map((x) => ({ name: x, count: count(x), on: t === x, href: t === x ? href({ t: "" }) : href({ t: x }) }))}
          />

          <div className="cat-tabs">
            <Link href={href({ c: "" })} className={c ? undefined : "on"}><LayoutGrid /> Tất cả</Link>
            {chapters.map((n, i) => (
              <Link key={n} style={{ "--ic": CH_COLOR[i % CH_COLOR.length] }} href={c === String(n) ? href({ c: "" }) : href({ c: String(n) })} className={c === String(n) ? "on" : undefined}>
                <BookOpen /> Chương {n}
              </Link>
            ))}
          </div>

          {/* key: bấm chip/tab/danh sách bên cạnh thì các ô chọn hiện lại đúng giá trị trên URL. */}
          <FilterForm key={`${d}|${c}|${t}|${st}|${sort}`} className="filters">
            <label className="search">
              <Search />
              <input type="search" name="q" placeholder="Tìm bài" defaultValue={sp.q || ""} />
            </label>
            <select name="s" defaultValue={sort} aria-label="Sắp xếp">
              {Object.entries(SORT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select name="d" defaultValue={d} aria-label="Mức độ">
              <option value="">Mức độ</option>
              {Object.entries(DIFF_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select name="st" defaultValue={st} aria-label="Trạng thái">
              <option value="">Trạng thái</option>
              {Object.entries(ST_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <span className="solved-count">
              <svg width="16" height="16" viewBox="0 0 40 40" aria-hidden="true">
                <circle cx="20" cy="20" r="16" fill="none" stroke="var(--line-strong)" strokeWidth="4" />
                <circle cx="20" cy="20" r="16" fill="none" stroke="var(--green)" strokeWidth="4" strokeLinecap="round"
                  strokeDasharray={RING} strokeDashoffset={RING * (1 - (all.length ? solved / all.length : 0))} transform="rotate(-90 20 20)" />
              </svg>
              <span className="num">{solved}/{all.length} đã giải</span>
            </span>
            <RandomButton ids={(list.length ? list : all).map((p) => p.id)} />
          </FilterForm>

          <div className="plist">
            <table className="list">
              <tbody>
                {list.length === 0 && <tr><td colSpan={5} className="empty">Không có bài nào khớp.</td></tr>}
                {list.map((p) => {
                  const s = status[p.id] || "todo";
                  const unmet = unmetPrereqs(p, status);
                  return (
                    <tr key={p.id}>
                      <td className={`st ${s}`} title={ST_LABEL[s]}>
                        {s === "solved" ? <Check className="size-4" strokeWidth={2.2} /> : s === "attempted" ? <CircleDashed className="size-4" strokeWidth={2} /> : null}
                      </td>
                      <td className="title-cell">
                        <Link href={`/problems/${p.id}`} className="row-link">{p.n}. {p.title}</Link>
                        {p.exam && <span className="chip accent" style={{ marginLeft: 8 }}>Thi thử</span>}
                        {unmet.length > 0 && <div className="lock">Cần làm trước: {unmet.join(", ")}</div>}
                      </td>
                      <td className="chap num">Chương {p.chapter}</td>
                      <td className="acc num">{p.acRate < 0 ? "—" : `${(p.acRate * 100).toFixed(1)}%`}</td>
                      <td className={`diff-${p.difficulty}`}>{DIFF_SHORT[p.difficulty]}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* ===== cột phải: lịch, tiến độ, xếp hạng ===== */}
        <aside className="side-r">
          <div className="rcard">
            <div className="rhead">
              <b>Ngày {now.getDate()}<small>Tháng {m + 1}/{y}</small></b>
              {streak > 0 && <span className="streak"><Flame className="size-3.5" /> {streak} ngày</span>}
            </div>
            <div className="cal">
              {WEEK.map((w) => <span key={w} className="dow">{w}</span>)}
              {Array.from({ length: lead }, (_, i) => <span key={`e${i}`} />)}
              {Array.from({ length: dim }, (_, i) => {
                const day = i + 1;
                return (
                  <span key={day} className={`day${day === now.getDate() ? " today" : active.get(day) ? " done" : ""}`}>
                    {day}
                    {active.has(day) && <i style={{ background: active.get(day) ? "var(--green)" : "var(--medium)" }} />}
                  </span>
                );
              })}
            </div>
            <div className="legend"><span><i style={{ background: "var(--green)" }} />Có AC</span><span><i style={{ background: "var(--medium)" }} />Có nộp bài</span></div>
            {examDays != null && (
              <div className="exam"><Timer className="size-4" /> {examDays === 0 ? "Thi giữa kỳ hôm nay" : <>Còn <b className="num">{examDays}</b> ngày đến kỳ thi ({examDate.toLocaleDateString("vi-VN")})</>}</div>
            )}
          </div>

          <div className="rcard">
            <div className="rhead"><b>Tiến độ theo mức độ</b></div>
            <div className="diffrows">
              {byDiff.map((r) => (
                <div key={r.k} className="drow">
                  <span className={`diff-${r.k}`}>{r.label}</span>
                  <span className="bar"><i style={{ width: `${r.total ? (100 * r.done) / r.total : 0}%`, background: `var(--${r.k})` }} /></span>
                  <span className="num mut">{r.done}/{r.total}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rcard">
            <div className="rhead"><b>Bảng xếp hạng</b><Trophy className="size-4" style={{ color: "var(--brand)" }} /></div>
            <ol className="board-l">
              {board.map((u, i) => (
                <li key={u.name} className={u.name === me ? "me" : undefined}>
                  <span className="rank num">{i + 1}</span>
                  <span className="av" style={{ "--a1": AV[i % AV.length][0], "--a2": AV[i % AV.length][1] }}>{u.name.slice(0, 1).toUpperCase()}</span>
                  <span className="who-n">{u.name}{u.name === me && <span className="chip" style={{ marginLeft: 6 }}>Bạn</span>}</span>
                  <span className="num mut">{u.solved} bài</span>
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  );
}
