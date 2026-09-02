import Link from "next/link";

// ADR-0006: no managed identity. The landing page links straight into the
// workspace; the browser-scoped guest token is issued on first API use.
export default function PublicEntryPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center gap-6 px-6">
      <h1 className="font-editorial text-5xl font-semibold text-ink">LessonCanvas</h1>
      <p className="text-lg text-ink-secondary">
        面向高中英语教师的单元备课工作台：基于你自有的材料，生成可追溯、可恢复的教学材料。
      </p>
      <p className="text-sm text-ink-secondary">
        你的上传、生成内容与完整运行记录仅属于你的工作区，不会被用于跨用户共享或模型训练，并可随项目或账号一并删除。
      </p>
      <div className="mt-2 flex items-center gap-4">
        <Link
          href="/projects"
          className="rounded bg-accent px-5 py-2.5 text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-focus"
        >
          进入备课工作台
        </Link>
      </div>

      <section aria-label="作品集评审" className="mt-8 space-y-3 border-t border-line pt-6">
        <h2 className="text-xl font-semibold text-ink">作品集评审</h2>
        <p className="text-sm text-ink-secondary">
          以下演示使用合成示例数据与受限的真实生成额度，不包含任何真实教师数据。
        </p>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <Link
            href="/sample"
            className="rounded px-4 py-2 font-medium text-accent hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
          >
            查看合成示例项目（只读）
          </Link>
          <a
            href="https://github.com/MaoyuanYang/LessonCanvas"
            target="_blank"
            rel="noreferrer"
            className="rounded px-4 py-2 font-medium text-accent hover:bg-surface-alt focus-visible:outline-2 focus-visible:outline-focus"
          >
            可复现验证与证据（GitHub 仓库）
          </a>
        </div>
        <p className="text-sm text-ink-secondary">
          本演示为本地部署环境，不承诺持续可用；服务暂不可用时会如实提示。
        </p>
      </section>
    </main>
  );
}
