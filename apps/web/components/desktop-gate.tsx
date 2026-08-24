"use client";

import { useEffect, useState } from "react";

export function useDesktop(minWidth = 1024): boolean {
  const [isDesktop, setIsDesktop] = useState(true);

  useEffect(() => {
    const query = window.matchMedia(`(min-width: ${minWidth}px)`);
    const update = () => setIsDesktop(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, [minWidth]);

  return isDesktop;
}

export function DesktopRequiredNotice({ task }: { task: string }) {
  return (
    <div
      role="note"
      className="rounded border border-line bg-surface-alt p-4 text-sm text-ink-secondary"
    >
      该操作（{task}）需要在桌面端（宽度不小于
      1024px）完成，以保证结构化编辑的准确性。当前设备可继续查看状态与回答提问。
    </div>
  );
}
