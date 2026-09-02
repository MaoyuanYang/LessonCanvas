import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PublicEntryPage from "../app/(public)/page";

describe("PublicEntryPage", () => {
  it("renders the product entry with privacy boundary", () => {
    render(<PublicEntryPage />);
    expect(screen.getByRole("heading", { name: "LessonCanvas" })).toBeInTheDocument();
    expect(screen.getByText(/单元备课工作台/)).toBeInTheDocument();
    expect(screen.getByText(/仅属于你的工作区/)).toBeInTheDocument();
  });

  it("links straight into the workspace without a sign-in step", () => {
    render(<PublicEntryPage />);
    const cta = screen.getByRole("link", { name: "进入备课工作台" });
    expect(cta).toHaveAttribute("href", "/projects");
    expect(screen.queryByRole("button", { name: /登录/ })).toBeNull();
  });

  it("renders the portfolio-review section with boundary, evidence link, availability honesty, and an unconditional sample link", () => {
    render(<PublicEntryPage />);
    expect(screen.getByRole("heading", { name: "作品集评审" })).toBeInTheDocument();
    expect(
      screen.getByText(/以下演示使用合成示例数据与受限的真实生成额度，不包含任何真实教师数据。/),
    ).toBeInTheDocument();
    const sampleLink = screen.getByRole("link", { name: /查看合成示例项目/ });
    expect(sampleLink).toHaveAttribute("href", "/sample");
    const repoLink = screen.getByRole("link", { name: /可复现验证与证据（GitHub 仓库）/ });
    expect(repoLink).toHaveAttribute("href", "https://github.com/MaoyuanYang/LessonCanvas");
    expect(repoLink).toHaveAttribute("rel", "noreferrer");
    expect(
      screen.getByText(/本演示为本地部署环境，不承诺持续可用；服务暂不可用时会如实提示。/),
    ).toBeInTheDocument();
  });
});
