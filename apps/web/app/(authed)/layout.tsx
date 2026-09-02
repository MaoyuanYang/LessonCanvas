import Link from "next/link";

// ADR-0006: no managed identity for the MVP. The authed shell is a plain
// server layout; the browser-scoped workspace token is managed client-side
// by lib/auth and the backend guest-token endpoint.
export default function AuthedLayout({ children }: { children: React.ReactNode }) {
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
        </div>
      </header>
      <div className="mx-auto w-full max-w-5xl px-6 py-8">{children}</div>
    </div>
  );
}
