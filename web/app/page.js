import Link from "next/link";
import fs from "node:fs";
import path from "node:path";
import { redirect } from "next/navigation";
import { ArrowRight, Award, BookOpenCheck, Bug, FilePlus2, Flame, GraduationCap, Layers, ListChecks, Medal, NotebookText, Target, Timer, Trophy } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { ROOT, db } from "@/lib/db";
import { getProblem, listProblems, listPlans, planProblemIds, problemDir } from "@/lib/content";
import { listConcepts } from "@/lib/learn";
import { BADGES, earnedBadges } from "@/lib/badges";
import { statusMap, unmetPrereqs } from "@/lib/progress";
import { ActivityCalendar } from "@/components/activity-calendar";

export const dynamic = "force-dynamic";

const ymd = (d) => d.toLocaleDateString("sv-SE");
const DIFF = { easy: "Dễ", medium: "Trung bình", hard: "Khó" };
const AV = [["#ffb74d", "#ffa116"], ["#5ac8fa", "#007aff"], ["#4cd964", "#2db55d"], ["#d68cf0", "#af52de"]];
const TIPS = [
  ["Một send() không bằng một recv()", "TCP là luồng byte, không có ranh giới thông điệp. Luôn tự ghép dòng hoặc dùng độ dài tiền tố, đừng giả định một lần recv() trả về đúng một lệnh."],
  ["Đừng quên đóng fd đúng phía sau fork()", "Cha đóng socket client, con đóng socket nghe. Quên một trong hai thì kết nối không bao giờ kết thúc và fd cạn dần."],
  ["select() sửa chính tập fd bạn truyền vào", "Mỗi vòng lặp phải dựng lại fd_set từ danh sách client. poll() thì không cần vì events và revents tách riêng."],
  ["Giới hạn N client: giảm bộ đếm ở một chỗ", "Đặt active-- ngay chỗ đóng client, dùng chung cho QUIT, recv trả 0 và lỗi, tránh rò chỗ khi client rớt mạng đột ngột."],
  ["stdout là tệp thì được đệm đầy", "Khi chạy dưới bộ chấm hoặc chuyển hướng, printf không hiện ngay. Dùng fflush(stdout) hoặc write(1, ...) cho phản hồi cần đến kịp thời."],
  ["UDP bảo toàn ranh giới nhưng có thể mất gói", "Một sendto ứng với một recvfrom, nhưng client luôn cần thời gian chờ (poll hoặc SO_RCVTIMEO) để không treo khi mất gói."],
];

function ago(t) {
  const s = Math.floor(Date.now() / 1000) - t;
  if (s < 60) return "vừa xong";
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  if (s < 86400) return `${Math.floor(s / 3600)} giờ trước`;
  return `${Math.floor(s / 86400)} ngày trước`;
}
const inDays = (n) => (n <= 0 ? "hôm nay" : n === 1 ? "ngày mai" : `trong ${n} ngày`);

// Đoạn mở đầu của một tệp markdown (bỏ tiêu đề, khối code, bảng), rút gọn để làm trích đoạn trong bảng tin.
function excerpt(md, max = 190) {
  const para = md.replace(/\r\n/g, "\n").split(/\n{2,}/).map((x) => x.trim())
    .find((x) => x && !/^(#|```|>|\||-{3}|\*\*Chú ý)/.test(x)) || "";
  const t = para.replace(/[`*#]/g, "").replace(/\[(.*?)\]\(.*?\)/g, "$1").replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max).replace(/\s+\S*$/, "") + "…" : t;
}
const mtime = (f) => { try { return Math.floor(fs.statSync(f).mtimeMs / 1000); } catch { return 0; } };

function Avatar({ name, i = 0, size = 40 }) {
  const [a, b] = AV[i % AV.length];
  return <span className="inline-grid shrink-0 place-items-center rounded-full font-medium text-white" style={{ width: size, height: size, fontSize: size * 0.42, background: `linear-gradient(135deg,${a},${b})` }}>{name.slice(0, 1).toUpperCase()}</span>;
}

export default async function Home() {
  const user = await currentUser();
  if (!user) redirect("/login");
  const now = new Date();
  const today0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  const status = statusMap(user.id);
  const all = listProblems().map((p, i) => ({ ...p, n: i + 1 }));
  const byId = new Map(all.map((p) => [p.id, p]));
  const plans = listPlans();
  const main = plans[0];
  const planDone = (p) => { const ids = planProblemIds(p); return { done: ids.filter((i) => status[i] === "solved").length, total: ids.length }; };
  const solved = all.filter((p) => status[p.id] === "solved").length;

  const nextProblem = all.find((p) => status[p.id] !== "solved" && !p.exam && unmetPrereqs(p, status).length === 0);
  const nextExam = all.filter((p) => p.exam).find((p) => status[p.id] !== "solved");
  const examDate = plans.map((p) => p.exam_date).filter(Boolean)
    .map((v) => new Date((v instanceof Date ? v.toISOString() : String(v)).slice(0, 10) + "T00:00:00"))
    .filter((v) => v >= today0).sort((a, b) => a - b)[0];
  const examDays = examDate ? Math.round((examDate - today0) / 86400000) : null;

  // Hoạt động mới nhất của mọi người (như bảng tin Discuss).
  const names = db.prepare("SELECT id, username, display FROM users ORDER BY id").all();
  const nameOf = Object.fromEntries(names.map((u, i) => [u.id, { name: u.display || u.username, i }]));
  const subs = db.prepare("SELECT user_id, problem_id, verdict, passed, total, created FROM submissions WHERE status='done' ORDER BY created DESC LIMIT 12").all()
    .filter((r) => byId.has(r.problem_id));

  // Bảng tin gộp ba loại bài đăng, mới nhất trước: lượt nộp của mọi người, bài mới thêm vào thư viện, thẻ kiến thức mới.
  const newest = (items, n) => items.sort((a, b) => b.t - a.t).slice(0, n);
  const feed = [
    ...subs.map((r) => ({ t: r.created, kind: "sub", r })),
    ...newest(all.map((p) => ({ t: mtime(path.join(problemDir(p.id), "statement.md")), kind: "problem", p })), 4),
    ...newest(listConcepts().map((c) => ({ t: mtime(path.join(ROOT, "knowledge", c.id + ".md")), kind: "concept", c })), 3),
  ].sort((a, b) => b.t - a.t).slice(0, 16);

  // Bảng xếp hạng tuần: số bài khác nhau đã AC trong 7 ngày qua (giống "Top 3 Contestants").
  const weekAgo = Math.floor(Date.now() / 1000) - 7 * 86400;
  const weekTop = db.prepare("SELECT user_id, COUNT(DISTINCT problem_id) AS n FROM submissions WHERE status='done' AND verdict='AC' AND created>=? GROUP BY user_id ORDER BY n DESC LIMIT 3").all(weekAgo)
    .filter((r) => nameOf[r.user_id]);
  const badgesGot = earnedBadges(user.id).length;

  // Lịch tháng của riêng bạn.
  const calDays = {};
  for (const r of db.prepare("SELECT problem_id, created, verdict FROM submissions WHERE user_id=? AND status='done' ORDER BY created").all(user.id)) {
    const p = byId.get(r.problem_id);
    if (!p) continue;
    const list = (calDays[ymd(new Date(r.created * 1000))] ||= []);
    const hit = list.find((x) => x.id === p.id);
    if (hit) hit.solved ||= r.verdict === "AC";
    else list.push({ id: p.id, title: p.title, solved: r.verdict === "AC" });
  }
  const daySet = new Set(Object.keys(calDays));
  let streak = 0;
  for (let k = daySet.has(ymd(now)) ? 0 : 1; daySet.has(ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - k))); k++) streak++;

  const tip = TIPS[Math.floor(today0.getTime() / 86400000) % TIPS.length];
  const me = user.display || user.username;
  const mainProg = main && planDone(main);

  const upcoming = [
    examDays != null && { icon: Trophy, when: inDays(examDays), text: "Thi giữa kỳ IT4062", link: main && `/plans/${main.id}`, label: examDate.toLocaleDateString("vi-VN") },
    nextExam && { icon: Timer, when: `${nextExam.examMinutes || 90} phút`, text: "Đề thi thử tiếp theo", link: `/problems/${nextExam.id}`, label: nextExam.title },
    nextProblem && { icon: Target, when: "Hôm nay", text: "Bài nên làm tiếp", link: `/problems/${nextProblem.id}`, label: `${nextProblem.n}. ${nextProblem.title} · ${DIFF[nextProblem.difficulty]}` },
  ].filter(Boolean);

  const card = "overflow-hidden rounded-2xl p-5 text-white";
  return (
    <div className="mx-auto grid max-w-[1180px] grid-cols-1 gap-10 px-6 py-8 lg:grid-cols-[minmax(0,1fr)_340px]">
      <section className="min-w-0">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <Avatar name={me} i={nameOf[user.id]?.i} size={44} />
          <div>
            <div className="text-lg font-medium text-[var(--title)]">Chào {me}</div>
            <div className="text-sm text-[var(--muted)]">Đã giải {solved}/{all.length} bài{streak > 0 && <> · <Flame className="inline size-3.5 text-[var(--brand)]" style={{ verticalAlign: "-2px" }} /> {streak} ngày liên tiếp</>}</div>
          </div>
        </div>

        <div className="divide-y divide-[var(--line)] border-y border-[var(--line)]">
          {upcoming.map((u) => (
            <div key={u.text} className="flex items-center gap-4 py-4">
              <u.icon className="size-9 shrink-0 text-[var(--brand)]" strokeWidth={1.6} />
              <div className="min-w-0 text-[15px] leading-6 text-[var(--text)]">
                <div className="text-sm text-[var(--muted)]">{u.when}</div>
                {u.text} <Link href={u.link} className="text-[var(--accent)] hover:underline">{u.label}</Link>
              </div>
            </div>
          ))}
        </div>

        <div className="my-7 flex flex-wrap items-center gap-3">
          <span className="text-[15px] text-[var(--text2)]">Khám phá thêm</span>
          {[["/plans", "Study Plan", GraduationCap], ["/problems", "Thư viện bài", Layers], ["/learn", "Ôn tập", BookOpenCheck], ["/learn/cheatsheet", "Cheatsheet", ListChecks]].map(([h, t, Icon]) => (
            <Link key={h} href={h} className="inline-flex items-center gap-1.5 rounded-full border border-[var(--accent)]/40 px-3.5 py-1.5 text-sm font-medium text-[var(--accent)] hover:bg-[var(--accent-soft)]"><Icon className="size-4" />{t}</Link>
          ))}
        </div>

        <div className="divide-y divide-[var(--line)] border-t border-[var(--line)]">
          <article className="flex gap-4 py-5">
            <span className="inline-grid size-10 shrink-0 place-items-center rounded-full bg-[var(--brand-soft)] text-[var(--brand)]"><Flame className="size-5" /></span>
            <div className="min-w-0">
              <div className="text-sm text-[var(--muted)]">Mẹo hôm nay</div>
              <div className="text-[15px] text-[var(--text)]"><b className="font-medium text-[var(--accent)]">SurfNeP</b> đăng: <b className="font-medium text-[var(--title)]">{tip[0]}</b></div>
              <p className="mt-1 text-[15px] leading-6 text-[var(--text2)]">{tip[1]}</p>
            </div>
          </article>
          <article className="flex gap-4 py-5">
            <span className="inline-grid size-10 shrink-0 place-items-center rounded-full bg-[var(--brand-soft)] text-[var(--brand)]"><Medal className="size-5" /></span>
            <div className="min-w-0">
              <div className="text-sm text-[var(--muted)]">Bảng xếp hạng tuần</div>
              <div className="text-[15px] text-[var(--text)]">Số bài AC trong 7 ngày qua</div>
              {weekTop.length === 0
                ? <p className="mt-1 text-sm text-[var(--muted)]">Tuần này chưa có ai AC. Bạn có thể là người đầu tiên!</p>
                : <ol className="mt-2 flex flex-wrap gap-x-6 gap-y-1 p-0 text-[15px]" style={{ listStyle: "none" }}>
                    {weekTop.map((r, k) => (
                      <li key={r.user_id} className="flex items-center gap-1.5">
                        <span>{["🥇", "🥈", "🥉"][k]}</span>
                        <b className="font-medium text-[var(--accent)]">{nameOf[r.user_id].name}</b>
                        <span className="text-[var(--muted)]">{r.n} bài</span>
                      </li>
                    ))}
                  </ol>}
            </div>
          </article>
          {feed.length === 0 && <div className="py-8 text-center text-sm text-[var(--muted)]">Chưa có hoạt động nào. Hãy nộp bài đầu tiên!</div>}
          {feed.map((it, k) => {
            if (it.kind === "problem") {
              const { p } = it;
              return (
                <article key={k} className="flex gap-4 py-5">
                  <span className="inline-grid size-10 shrink-0 place-items-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]"><FilePlus2 className="size-5" /></span>
                  <div className="min-w-0">
                    <div className="text-sm text-[var(--muted)]">{ago(it.t)}</div>
                    <div className="text-[15px] text-[var(--text)]">Bài tập <Link href={`/problems/${p.id}`} className="text-[var(--accent)] hover:underline">{p.n}. {p.title}</Link> vừa được cập nhật</div>
                    <p className="mt-1 text-[15px] leading-6 text-[var(--text2)]">{excerpt(getProblem(p.id)?.statement || "")}</p>
                    <div className="mt-1 text-sm text-[var(--muted)]">{DIFF[p.difficulty]} · Chương {p.chapter}</div>
                  </div>
                </article>
              );
            }
            if (it.kind === "concept") {
              const { c } = it;
              return (
                <article key={k} className="flex gap-4 py-5">
                  <span className="inline-grid size-10 shrink-0 place-items-center rounded-full bg-[var(--ok-bg)] text-[var(--green)]"><NotebookText className="size-5" /></span>
                  <div className="min-w-0">
                    <div className="text-sm text-[var(--muted)]">{ago(it.t)}</div>
                    <div className="text-[15px] text-[var(--text)]">Thẻ kiến thức <Link href={`/learn/c/${c.id}`} className="text-[var(--accent)] hover:underline">{c.title}</Link> đã được cập nhật</div>
                    <p className="mt-1 text-[15px] leading-6 text-[var(--text2)]">{excerpt(c.body)}</p>
                    {c.ref && <div className="mt-1 text-sm text-[var(--muted)]">{c.ref}</div>}
                  </div>
                </article>
              );
            }
            const { r } = it;
            const p = byId.get(r.problem_id);
            const who = nameOf[r.user_id] || { name: "?", i: 0 };
            const ac = r.verdict === "AC";
            return (
              <article key={k} className="flex gap-4 py-5">
                <Avatar name={who.name} i={who.i} />
                <div className="min-w-0">
                  <div className="text-sm text-[var(--muted)]">{ago(r.created)}</div>
                  <div className="text-[15px] text-[var(--text)]">
                    <b className="font-medium text-[var(--accent)]">{who.name}</b> {ac ? "đã giải" : "đã nộp"}{" "}
                    <Link href={`/problems/${p.id}`} className="text-[var(--accent)] hover:underline">{p.n}. {p.title}</Link>
                  </div>
                  <div className="mt-1 text-sm">
                    <span className={ac ? "text-[var(--green)]" : "text-[var(--hard)]"}>{ac ? "Accepted" : r.verdict}</span>
                    <span className="text-[var(--muted)]"> · {r.passed}/{r.total} test · {DIFF[p.difficulty]}</span>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <aside className="flex min-w-0 flex-col gap-5">
        {main && (
          <Link href={`/plans/${main.id}`} className={`${card} block`} style={{ background: "linear-gradient(135deg,#2f6bff,#6a3df0)" }}>
            <div className="text-xs opacity-80">Study Plan</div>
            <div className="mt-1 text-xl font-medium leading-snug">{main.title}</div>
            <div className="mt-1 text-sm opacity-85">{main.subtitle}</div>
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/25"><i className="block h-full rounded-full bg-white" style={{ width: `${(mainProg.done / mainProg.total) * 100}%` }} /></div>
            <div className="mt-2 flex items-center justify-between text-sm"><span>{mainProg.done}/{mainProg.total} bài</span><span className="inline-flex items-center gap-1 font-medium">Tiếp tục <ArrowRight className="size-4" /></span></div>
          </Link>
        )}
        <Link href="/learn" className={`${card} block`} style={{ background: "linear-gradient(135deg,#7c4dff,#b44df0)" }}>
          <div className="text-lg font-medium leading-snug">Ôn tập thông minh: quiz, flashcard và tìm bug</div>
          <span className="mt-4 inline-block rounded-md bg-white px-3 py-1.5 text-sm font-medium text-[#6a3df0]">Bắt đầu ôn</span>
        </Link>
        <div className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-2xl border border-[var(--line)] p-5">
          <div>
            <div className="font-medium text-[var(--title)]">Thi thử giữa kỳ</div>
            <div className="mt-1 text-sm text-[var(--muted)]">Tính giờ 90 phút, test ẩn.</div>
            {nextExam && <Link href={`/problems/${nextExam.id}`} className="mt-3 inline-block rounded-md bg-[var(--fill-3)] px-3 py-1.5 text-sm text-[var(--title)] hover:bg-[var(--fill-4)]">Vào thi</Link>}
          </div>
          <Trophy className="size-16 text-[var(--brand)]" strokeWidth={1.3} />
        </div>
        <Link href="/learn" className="grid grid-cols-[auto_1fr] items-center gap-4 rounded-2xl border border-[var(--line)] p-5 hover:bg-[var(--raised)]">
          <Bug className="size-14 text-[var(--green)]" strokeWidth={1.4} />
          <div>
            <div className="font-medium text-[var(--title)]">Tìm bug</div>
            <div className="mt-1 text-sm text-[var(--muted)]">Đọc code sai, chỉ ra dòng gây lỗi.</div>
          </div>
        </Link>
        <Link href="/learn/progress" className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-2xl border border-[var(--line)] p-5 hover:bg-[var(--raised)]">
          <div>
            <div className="font-medium text-[var(--title)]">Huy hiệu của bạn</div>
            <div className="mt-1 text-sm text-[var(--muted)]">Đã đạt {badgesGot}/{BADGES.length}. Giải bài, giữ chuỗi ngày và hoàn thành plan để mở khoá thêm.</div>
          </div>
          <Award className="size-14 text-[var(--brand)]" strokeWidth={1.3} />
        </Link>
        <div className="rounded-2xl border border-[var(--line)] p-5">
          <ActivityCalendar days={calDays} today={ymd(now)} />
        </div>
      </aside>

      <footer className="border-t border-[var(--line)] pt-6 text-sm text-[var(--muted)] lg:col-span-2">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-[var(--text2)]">Chọn một hướng</span>
          {[["/problems?c=2", "Chương 2 · Socket cơ bản"], ["/problems?c=3", "Chương 3 · Server nhiều client"], ["/problems?t=UDP", "UDP"], ["/problems?t=select", "select / poll"], ["/problems?t=Client+Limit", "Tối đa N client"]].map(([h, t]) => (
            <Link key={h} href={h} className="rounded-full bg-[var(--fill-3)] px-3 py-1 text-[var(--text)] hover:bg-[var(--fill-4)]">{t}</Link>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
          <span>© {now.getFullYear()} SurfNeP · IT4062 Thực hành Lập trình mạng, Đại học Bách khoa Hà Nội</span>
          <Link href="/plans" className="text-[var(--muted)] hover:text-[var(--title)]">Study Plan</Link>
          <Link href="/learn/cheatsheet" className="text-[var(--muted)] hover:text-[var(--title)]">Cheatsheet</Link>
          <Link href="/learn" className="text-[var(--muted)] hover:text-[var(--title)]">Ôn tập</Link>
        </div>
      </footer>
    </div>
  );
}
