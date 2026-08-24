"use client";

import { SignInButton, UserButton, useUser } from "@clerk/nextjs";
import Link from "next/link";

export default function PublicEntryPage() {
  const { isSignedIn } = useUser();

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
        {isSignedIn ? (
          <>
            <Link
              href="/projects"
              className="rounded bg-accent px-5 py-2.5 text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-focus"
            >
              进入项目列表
            </Link>
            <UserButton />
          </>
        ) : (
          <SignInButton mode="modal">
            <button
              type="button"
              className="rounded bg-accent px-5 py-2.5 text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-focus"
            >
              登录并开始备课
            </button>
          </SignInButton>
        )}
      </div>
    </main>
  );
}
