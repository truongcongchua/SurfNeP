import Link from "next/link";
import { redirect } from "next/navigation";
import { currentUser } from "@/lib/auth";
import { listProblems, DIFF_LABEL } from "@/lib/content";
import { statusMap, unmetPrereqs } from "@/lib/progress";

export const dynamic = "force-dynamic";

export default async function Problems({ searchParams }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  const sp = await searchParams;
  const q = (sp.q || "").toLowerCase(), d = sp.d || "", t = sp.t || "", c = sp.c || "";
  const all = listProblems();
  const topics = [...new Set(all.flatMap((p) => p.topics))].sort();
  const status = statusMap(user.id);
  const list = all.filter(
    (p) =>
      (!q || p.title.toLowerCase().includes(q) || p.id.includes(q)) &&
      (!d || p.difficulty === d) && (!t || p.topics.includes(t)) && (!c || String(p.chapter) === c)
  );
  const solved = all.filter((p) => status[p.id] === "solved").length;
  const count = (x) => all.filter((p) => p.topics.includes(x)).length;
  // Chỉ hiện 8 chủ đề nhiều bài nhất như LeetCode; chủ đề đang lọc luôn được giữ lại.
  const topTopics = [...topics].sort((a, b) => count(b) - count(a)).slice(0, 8);
  if (t && !topTopics.includes(t)) topTopics.push(t);
  const href = (next) => {
    const s = new URLSearchParams({ ...(sp.q ? { q: sp.q } : {}), ...(d ? { d } : {}), ...(c ? { c } : {}), ...next });
    for (const [k, v] of [...s]) if (!v) s.delete(k);
    return s.size ? `/?${s}` : "/";
  };

  return (
    <>
      <h1>Bài tập</h1>
      <p className="sub">Bài ghi “cần làm trước” chỉ là gợi ý thứ tự, vẫn nộp bình thường.</p>
      <div className="tabs-pill">
        <Link href={href({ t: "" })} className={t ? "" : "on"}>Tất cả chủ đề</Link>
        {topTopics.map((x) => (
          <Link key={x} href={href({ t: x })} className={t === x ? "on" : ""}>{x} <span className="chip">{count(x)}</span></Link>
        ))}
      </div>
      <form className="filters">
        <input type="search" name="q" placeholder="Tìm bài…" defaultValue={sp.q || ""} />
        <select name="d" defaultValue={d}>
          <option value="">Mọi mức</option>
          {Object.entries(DIFF_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select name="c" defaultValue={c}>
          <option value="">Mọi chương</option>
          {[1, 2, 3, 4].map((n) => <option key={n} value={n}>Chương {n}</option>)}
        </select>
        <select name="t" defaultValue={t}>
          <option value="">Mọi chủ đề</option>
          {topics.map((x) => <option key={x}>{x}</option>)}
        </select>
        <button className="btn ghost">Lọc</button>
        <span className="solved-count"><b style={{ color: "var(--green)" }}>{solved}</b>/{all.length} Đã giải</span>
      </form>
      <div className="card">
        <table className="list">
          <tbody>
            {list.length === 0 && <tr><td className="empty">Không có bài nào khớp.</td></tr>}
            {list.map((p) => {
              const st = status[p.id] || "todo";
              const unmet = unmetPrereqs(p, status);
              return (
                <tr key={p.id}>
                  <td className={`st ${st}`} title={st}>{st === "solved" ? "✓" : st === "attempted" ? "•" : "○"}</td>
                  <td>
                    <Link href={`/problems/${p.id}`}>{p.title}</Link>
                    {p.exam && <span className="chip" style={{ marginLeft: 8 }}>Thi thử</span>}
                    {unmet.length > 0 && <div className="lock">Cần làm trước: {unmet.join(", ")}</div>}
                  </td>
                  <td><div className="topics">{p.topics.slice(0, 3).map((x) => <span key={x} className="chip">{x}</span>)}</div></td>
                  <td>Chương {p.chapter}</td>
                  <td className={`diff-${p.difficulty}`}>{DIFF_LABEL[p.difficulty]}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
