import { expect, test, type Page } from "@playwright/test";
import {
  confirmedBlueprint,
  deleteProject,
  domFill,
  HINTS,
  openWorkspace,
} from "./journey-helpers";

// F016 specialist-stage journey (test-design-f016-r1 TS-021).
//   E2E_SPECIALIST_STAGES=1 -> fake-adapter backend (deterministic).
// Drives: source upload with its analysis badge -> blueprint confirmed with
// one REVIEW_SEVERE lesson title -> generation completes through the revise
// round -> the artifact row
// expands to the read-only design + findings regions (修订后评审通过) -> the
// evidence tab renders the review/revise rows with round/severity chips ->
// keyboard expansion -> canonical 420px spot. Narration sentences are covered
// by the component suite (the eager deterministic backend settles the run
// before the SSE stream opens, so live narration lines are not assertable
// here). Design-fault and
// failed-after-revise degradation paths are covered deterministically by the
// backend suites (TS-007/TS-011).

const gate = process.env.E2E_SPECIALIST_STAGES === "1";

// No 课时分配/课时数 lines: with them in the corpus the fake planner skips
// its gap questions (same constraint as the retrieval journey).
const SOURCE_TEXT = [
  "单元主题：环境保护与可持续发展",
  "学情：高二学生，英语中等水平",
  "教学目标：提升环境保护主题的阅读与表达能力",
  "教材定位：外研社必修一 Unit 3",
  "输出语言：中英双语",
  "评估倾向：形成性评价为主",
].join("\n");

async function createAndOpenProject(page: Page): Promise<string> {
  const name = `专家阶段旅程 ${Date.now()}`;
  await page.getByRole("button", { name: "新建备课项目" }).click({ timeout: 30000 });
  await domFill(page.locator("#project-name"), name);
  await domFill(page.locator("#project-hints"), HINTS);
  await page
    .getByRole("button", { name: "创建项目" })
    .evaluate((element) => (element as HTMLButtonElement).click());
  const token = await page.evaluate(() =>
    localStorage.getItem("lessoncanvas_workspace_token"),
  );
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const response = await page.request.get(
      `${process.env.E2E_API_BASE_URL ?? "http://localhost:8000"}/projects`,
      { headers: { authorization: `Bearer ${token}` } },
    );
    if (response.ok()) {
      const projects = (await response.json()) as Array<{ id: string; name: string }>;
      const created = projects.find((item) => item.name === name);
      if (created) {
        await page.goto(`/projects/${created.id}`);
        return name;
      }
    }
    await page.waitForTimeout(800);
  }
  throw new Error(`created project not listed: ${name}`);
}

test.describe("specialist stage journey - deterministic stack", () => {
  test.skip(!gate, "set E2E_SPECIALIST_STAGES=1 with the fake-adapter backend running");
  test.setTimeout(300000);

  test("TS-021: design, severity-gated review, and revise are visible end to end", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createAndOpenProject(page);

      // Upload: the source's analysis settles (eager fake adapter) and the
      // sources panel shows the badge + expandable digest.
      await page.locator('input[type="file"]').setInputFiles({
        name: "specialist-notes.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(SOURCE_TEXT, "utf-8"),
      });
      await page.getByText("我确认有权使用该材料用于备课").click();
      await page.getByRole("button", { name: "上传" }).click({ timeout: 30000 });
      await expect(page.getByText("已分析").first()).toBeVisible({ timeout: 60000 });
      await page.getByText("查看来源分析").first().click({ timeout: 30000 });
      await expect(page.getByText(/主题：/).first()).toBeVisible({ timeout: 30000 });

      // One lesson title carries REVIEW_SEVERE: its plan review finds a
      // severe issue, triggers the single revise round, then passes.
      await confirmedBlueprint(page, { index: 1, title: "第1课 REVIEW_SEVERE 阅读" });

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      // The artifact row expands to the read-only design + findings regions.
      await page.getByRole("button", { name: /查看活动设计与评审发现/ }).first().click({
        timeout: 30000,
      });
      await expect(page.getByText(/运行中间产物，仅查看/).first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/修订后第 2 轮/).first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/修订后评审通过/).first()).toBeVisible({ timeout: 30000 });
      // The latest (clean) round is disclosed: passed with no findings; the
      // severe round-1 finding shows in the evidence chips below.
      await expect(page.getByText("评审通过，无严重或轻微发现。").first()).toBeVisible({
        timeout: 30000,
      });

      // Evidence: review/revise rows with round/severity/outcome chips.
      // (The newest run is auto-selected; the kind filter shares its label
      // with the workspace nav tab, so no filter click is needed here.)
      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(
        page.getByRole("button", { name: /模型调用·活动设计/ }).first(),
      ).toBeVisible({ timeout: 60000 });
      await expect(
        page.getByRole("button", { name: /模型调用·质量评审（教案）/ }).first(),
      ).toBeVisible({ timeout: 30000 });
      await expect(page.getByText("第 1 轮").first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/严重 \d+ · 轻微 \d+/).first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText("触发修订").first()).toBeVisible({ timeout: 30000 });
      await expect(
        page.getByRole("button", { name: /模型调用·修订重写（教案）/ }).first(),
      ).toBeVisible({ timeout: 30000 });

      // Keyboard path: focus + Enter expands a review row's raw payload.
      const reviewRow = page.getByRole("button", { name: /模型调用·质量评审（教案）/ }).first();
      await reviewRow.focus();
      await page.keyboard.press("Enter");
      await expect(reviewRow).toHaveAttribute("aria-expanded", "true");
      await expect(page.getByText("复制原始数据").first()).toBeVisible({ timeout: 30000 });

      // Canonical reduced small-screen spot: the core plans surface stays
      // usable; technical evidence stays desktop-gated by design.
      await page.setViewportSize({ width: 420, height: 800 });
      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/课程进度/).first()).toBeVisible({ timeout: 30000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});
