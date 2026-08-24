import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-semibold text-ink">无法打开该内容</h1>
      <p className="text-sm text-ink-secondary">
        它可能不存在，或不属于当前账号。为保护隐私，我们不会显示更多细节。
      </p>
      <Link
        href="/projects"
        className="rounded bg-accent px-5 py-2.5 text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-focus"
      >
        返回我的项目列表
      </Link>
    </main>
  );
}
