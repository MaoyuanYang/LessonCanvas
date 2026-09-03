import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  deleteProject,
  domFill,
  HINTS,
  openWorkspace,
} from "./journey-helpers";

// The dev-server project list re-renders continuously (known F004 M-1
// actionability race); create at the DOM level and navigate by the API id,
// mirroring the memory-journey pattern.
async function createAndOpenProject(page: import("@playwright/test").Page): Promise<string> {
  const name = `检索旅程 ${Date.now()}`;
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
      `${process.env.E2E_API_BASE_URL ?? "http://localhost:8010"}/projects`,
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

// F014 retrieval journey (test-design-f014-r1 TS-025).
//   E2E_RETRIEVAL=1 -> fake-adapter backend (fake embedding + fake model).
// Drives: source upload (parsed + embedded) -> planning completes with
// retrieval-backed chunk citations on the blueprint (expandable, keyboard
// operable) -> lesson-plan generation shows per-lesson citations -> the
// evidence tab renders retrieval rows with hit/budget chips -> the sources
// tab expands the chunk view. Backend and component suites carry the
// degradation paths (zero relevance, exclusions) deterministically.

const gate = process.env.E2E_RETRIEVAL === "1";

// No 课时分配/课时数 lines here: with them in the retrieved corpus the fake
// planner skips its gap questions, leaving a second waivable finding the
// shared journey helper does not decide (its single decision click).
const SOURCE_TEXT = [
  "单元主题：环境保护与可持续发展",
  "学情：高二学生，英语中等水平",
  "教学目标：提升环境保护主题的阅读与表达能力",
  "教材定位：外研社必修一 Unit 3",
  "输出语言：中英双语",
  "评估倾向：形成性评价为主",
].join("\n");

test.describe("retrieval journey - deterministic stack", () => {
  test.skip(!gate, "set E2E_RETRIEVAL=1 with the fake-adapter backend running");
  test.setTimeout(300000);

  test("TS-025: chunk citations trace from blueprint to evidence and sources", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createAndOpenProject(page);

      // Upload a theme-related source; the eager parse embeds every chunk.
      // The workspace opens on the sources tab by default.
      await page.locator('input[type="file"]').setInputFiles({
        name: "retrieval-notes.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(SOURCE_TEXT, "utf-8"),
      });
      await page.getByText("我确认有权使用该材料用于备课").click();
      await page.getByRole("button", { name: "上传" }).click({ timeout: 30000 });
      // The chunk toggle appears once parsing settled (chunks persisted).
      await expect(page.getByRole("button", { name: /查看切块（\d+ 段/ }).first()).toBeVisible({
        timeout: 60000,
      });

      // Planning: blueprint objectives carry expandable chunk citations.
      await confirmedBlueprint(page);
      const chip = page.getByRole("button", { name: /来源：retrieval-notes\.txt · 第\d+段/ }).first();
      await expect(chip).toBeVisible({ timeout: 30000 });
      // Keyboard path: focus + Enter expands (aria-expanded flips).
      await chip.focus();
      await page.keyboard.press("Enter");
      await expect(chip).toHaveAttribute("aria-expanded", "true");
      await expect(page.getByText(/内容哈希：/).first()).toBeVisible({ timeout: 30000 });

      // Lesson-plan generation: per-lesson citations in the artifact rows.
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成并通过结构校验/)).toBeVisible({
        timeout: 240000,
      });
      await expect(
        page.getByRole("button", { name: /来源：retrieval-notes\.txt · 第\d+段/ }).first(),
      ).toBeVisible({ timeout: 30000 });

      // Evidence: retrieval rows with teacher-readable summary chips.
      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(page.getByText("命中 1", { exact: false }).first()).toBeVisible({
        timeout: 60000,
      });
      await expect(page.getByText(/预算 \d+\/2000 字/).first()).toBeVisible({ timeout: 30000 });

      // Sources: the full-fidelity chunk view.
      await page.getByRole("button", { name: "来源", exact: true }).click({ timeout: 30000 });
      const chunkToggle = page.getByRole("button", { name: /查看切块（\d+ 段/ }).first();
      await chunkToggle.click({ timeout: 30000 });
      await expect(page.getByText("第 0 段").first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/单元主题：环境保护与可持续发展/).first()).toBeVisible({
        timeout: 30000,
      });

      // Canonical reduced small-screen spot: citations stay visible at 420px.
      await page.setViewportSize({ width: 420, height: 800 });
      await page.getByRole("button", { name: "单元蓝图" }).click({ timeout: 30000 });
      await expect(
        page.getByRole("button", { name: /来源：retrieval-notes\.txt · 第\d+段/ }).first(),
      ).toBeVisible({ timeout: 30000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});
