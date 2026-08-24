import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

export default async function AuthedLayout({ children }: { children: React.ReactNode }) {
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-6">
            <Link href="/projects" className="font-editorial text-xl font-semibold text-ink">
              LessonCanvas
            </Link>
            <nav aria-label="项目导航" className="flex items-center gap-4 text-sm">
              <Link href="/projects" className="text-accent">
                项目列表
              </Link>
              <Link href="/account" className="text-ink-secondary hover:text-ink">
                账号与数据
              </Link>
            </nav>
          </div>
          <UserButton />
        </div>
      </header>
      <div className="mx-auto w-full max-w-5xl px-6 py-8">{children}</div>
    </div>
  );
}
