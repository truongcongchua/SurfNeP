import Link from "next/link";
import { redirect } from "next/navigation";
import { ChevronsRight, GraduationCap, Network, Target, Timer } from "lucide-react";
import { currentUser } from "@/lib/auth";
import { db } from "@/lib/db";
import { listPlans, planProblemIds } from "@/lib/content";
import { statusMap } from "@/lib/progress";
import { SideNav } from "@/components/side-nav";

export const dynamic = "force-dynamic";
// Icon lớn ở góc thẻ Featured (xoay vòng như các thẻ LeetCode 75 / Top Interview 150 / Binary Search / SQL 50).
const ICONS = [Network, Target, Timer, GraduationCap];

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
    <div className="lc-layout gray">
      <SideNav active="plans" />
      <div className="sp-wrap">
        <div className="sp-title">
          <h1>Study Plan</h1>
          {ongoing[0] && <Link href={`/plans/${ongoing[0].id}`} className="sp-btn">Plan của tôi <ChevronsRight className="size-4" /></Link>}
        </div>

        {ongoing.length > 0 && (
          <>
            <h2 className="sp-h2">Đang học</h2>
            <div className="sp-small">
              {ongoing.map((p) => {
                const { done, total } = prog(p);
                return (
                  <Link key={p.id} href={`/plans/${p.id}`}>
                    <span className="ic"><Network /></span>
                    <span style={{ minWidth: 0 }}>
                      <div className="name">{p.title}</div>
                      <div className="meta">Đã giải {done} / {total} bài</div>
                      <div className="bar"><i style={{ width: `${total ? (100 * done) / total : 0}%` }} /></div>
                    </span>
                  </Link>
                );
              })}
            </div>
          </>
        )}

        <h2 className="sp-h2">Nổi bật</h2>
        <div className="sp-feat">
          {plans.map((p, i) => {
            const { total } = prog(p);
            const Icon = ICONS[i % ICONS.length];
            return (
              <Link key={p.id} href={`/plans/${p.id}`}>
                <span className="name">{p.title}</span>
                <span className="meta">{p.subtitle}</span>
                <span className="meta">{p.sections.length} chủ đề · {total} bài{p.suggested_days ? ` · ${p.suggested_days} ngày` : ""}</span>
                <Icon className="big" />
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
