import { expect, test, type Page } from "@playwright/test";
import {
  confirmedBlueprint,
  deleteProject,
  domFill,
  HINTS,
  openWorkspace,
} from "./journey-helpers";

// The dev-server project list re-renders continuously (known F004 M-1
// actionability race); create at the DOM level and navigate by the API id,
// mirroring the retrieval-journey pattern.
async function createAndOpenProject(page: Page): Promise<string> {
  const name = `工具循环旅程 ${Date.now()}`;
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

// F015 governed tool-loop journey (test-design-f015-r1 TS-020).
//   E2E_TOOL_LOOP=1 -> fake-adapter backend (model_driven tool loop default).
// Drives: source upload -> planning completes with one refused round (the
// scripted specialist first requests an unbound tool, is refused, corrects)
// and one real self-requested standards round -> blueprint confirms with the
// unchanged contract -> the evidence tab renders the tool rounds with
// round/refusal/result chips -> keyboard expansion shows the raw payload ->
// canonical 420px spot. Refusal/cap/fallback degradation paths are covered
// deterministically by the backend suites (TS-004..TS-007).

const gate = process.env.E2E_TOOL_LOOP === "1";

// No 课时分配/课时数 lines: with them in the corpus the fake planner skips
// its gap questions (same constraint as the retrieval journey).
const SOURCE_TEXT = [
  "单元主题：TOOL_UNKNOWN 环境保护与可持续发展",
  "学情：高二学生，英语中等水平",
  "教学目标：提升环境保护主题的阅读与表达能力",
  "教材定位：外研社必修一 Unit 3",
  "输出语言：中英双语",
  "评估倾向：形成性评价为主",
].join("\n");

test.describe("tool loop journey - deterministic stack", () => {
  test.skip(!gate, "set E2E_TOOL_LOOP=1 with the fake-adapter backend running");
  test.setTimeout(300000);

  test("TS-020: self-requested tool rounds and the refusal are visible end to end", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createAndOpenProject(page);

      await page.locator('input[type="file"]').setInputFiles({
        name: "tool-loop-notes.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(SOURCE_TEXT, "utf-8"),
      });
      await page.getByText("我确认有权使用该材料用于备课").click();
      await page.getByRole("button", { name: "上传" }).click({ timeout: 30000 });

      // Planning completes through refusal -> correction -> final blueprint.
      await confirmedBlueprint(page);

      // Evidence: the planning run's tool rounds are visible with chips.
      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "蓝图规划" }).first().click({ timeout: 30000 });
      await expect(
        page.getByRole("button", { name: /工具请求（模型）/ }).first(),
      ).toBeVisible({ timeout: 60000 });
      await expect(page.getByText(/第 \d+ 轮 · search_curriculum_standards/).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByRole("button", { name: /工具拒绝/ }).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText(/拒绝：tool not in bound whitelist/).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(
        page.getByRole("button", { name: /工具结果/ }).first(),
      ).toBeVisible({ timeout: 30000 });

      // Keyboard path: focus + Enter expands the refused round's payload.
      const refusedRow = page.getByRole("button", { name: /工具拒绝/ }).first();
      await refusedRow.focus();
      await page.keyboard.press("Enter");
      await expect(refusedRow).toHaveAttribute("aria-expanded", "true");
      await expect(page.getByText("复制原始数据").first()).toBeVisible({ timeout: 30000 });

      // Canonical reduced small-screen spot: the core blueprint surface
      // stays usable; technical evidence stays desktop-gated by design.
      await page.setViewportSize({ width: 420, height: 800 });
      await page.getByRole("button", { name: "单元蓝图" }).click({ timeout: 30000 });
      await expect(page.getByText(/单元目标|教学目标/).first()).toBeVisible({ timeout: 30000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});
