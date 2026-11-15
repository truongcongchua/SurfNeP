import Link from "next/link";
import { redirect } from "next/navigation";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { listPlans, planProblemIds } from "@/lib/content";
import { statusMap } from "@/lib/progress";

export const dynamic = "force-dynamic";

export default async function Plans() {
  const user = await currentUser();
  if (!user) redirect("/login");
  const plans = listPlans();
  const status = statusMap(user.id);
  const started = new Set(db.prepare("SELECT plan_id FROM plan_start WHERE user_id=?").all(user.id).map((r) => r.plan_id));
  const prog = (p) => {
    const ids = planProblemIds(p);
    return { done: ids.filter((i) => status[i] === "solved").length, total: ids.length };
  };
  const ongoing = plans.filter((p) => started.has(p.id));

  return (
    <>
      <h1>Study Plan</h1>
      <p className="sub">Lộ trình có thứ tự, nhóm theo chủ đề, mỗi chủ đề trỏ về mục lecture notes tương ứng.</p>

      {ongoing.length > 0 && (
        <>
          <h2>Đang học</h2>
          <div className="plans">
            {ongoing.map((p) => {
              const { done, total } = prog(p);
              return (
                <Link key={p.id} href={`/plans/${p.id}`} className="card plan-card">
                  <span className="name">{p.title}</span>
                  <span className="sub" style={{ margin: 0 }}>{p.subtitle}</span>
                  <div className="bar"><i style={{ width: `${(100 * done) / total}%` }} /></div>
                  <span className="sub" style={{ margin: 0 }}>Tiến độ {done} / {total}</span>
                </Link>
              );
            })}
          </div>
        </>
      )}

      <h2>Nổi bật</h2>
      <div className="plans">
        {plans.map((p, i) => {
          const { total } = prog(p);
          return (
            <Link key={p.id} href={`/plans/${p.id}`} className={`card plan-card feat f${(i % 3) + 1}`}>
              <span className="name">{p.title}</span>
              <span className="meta">{p.subtitle}</span>
              <span className="meta">{p.sections.length} chủ đề · {total} bài{p.suggested_days ? ` · ${p.suggested_days} ngày` : ""}</span>
            </Link>
          );
        })}
      </div>
    </>
  );
}
