import { redirect } from "next/navigation";
import { currentUser } from "@/lib/auth";
import { dueCount } from "@/lib/learn";
import { LearnNav } from "@/components/learn/learn-nav";

export const dynamic = "force-dynamic";

export default async function LearnLayout({ children }) {
  const user = await currentUser();
  if (!user) redirect("/login");
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6">
      <LearnNav due={dueCount(user.id)} />
      {children}
    </div>
  );
}
