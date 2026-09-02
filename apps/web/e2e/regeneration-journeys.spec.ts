import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  createProject,
  deleteProject,
  openWorkspace,
} from "./journey-helpers";

// F007 regeneration journeys (test-design-f007-r1 TS-014/015/016).
//   E2E_REGEN_LIVE=1   -> live model backend + real worker (TS-015)
//   E2E_REGEN_FAULT=1  -> fake-adapter backend (TS-014 journey + TS-016 keyboard pass)

const liveGate = process.env.E2E_REGEN_LIVE === "1";
const faultGate = process.env.E2E_REGEN_FAULT === "1";

async function openVersionsTab(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "版本对比" }).click({ timeout: 30000 });
}

async function completeUnit(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
  await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });
  await page.getByRole("button", { name: "课件生成" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
  await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 240000 });
  await page.getByRole("button", { name: "练习与答案" }).click({ timeout: 30000 });
  await page.getByLabel("基础").click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
  await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 240000 });
}

async function reviseLesson2(page: import("@playwright/test").Page) {
  const { domFill } = await import("./journey-helpers");
  await page.getByRole("button", { name: "单元蓝图" }).click({ timeout: 30000 });
  // After confirmation the panel keeps an editable draft seeded from the
  // confirmed payload; revise lesson 2's outline and save a new revision.
  const outline = page.getByRole("textbox", { name: "第2课活动提纲" });
  await domFill(outline, "修订后的活动纲要：聚焦迁移创新任务与小组展示");
  const save = page.getByRole("button", { name: "保存修订" }).first();
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const holds = await outline.inputValue().catch(() => "");
    if (holds && (await save.isEnabled().catch(() => false))) break;
    await page.waitForTimeout(800);
  }
  await save.evaluate((element) => (element as HTMLButtonElement).click());
  await expect(page.getByText(/已保存|草稿修订/).first()).toBeVisible({ timeout: 60000 });

  // A revised draft can re-open waivable planning findings; record the
  // teacher decision (same flow as the initial seeding helper).
  for (let round = 0; round < 3; round += 1) {
    const decide = page.getByRole("button", { name: "记录教师决策" });
    if (!(await decide.first().isVisible().catch(() => false))) break;
    await decide.first().click({ timeout: 30000 });
    await page.locator("#decision-reason").fill("以教材与教师判断为准");
    await page.getByRole("button", { name: "记录决策" }).click({ timeout: 30000 });
    await expect(page.getByText(/决策理由：/).first()).toBeVisible({ timeout: 60000 });
  }

  const confirm = page.getByRole("button", { name: "确认蓝图" });
  await expect(confirm).toBeEnabled({ timeout: 30000 });
  await confirm.evaluate((element) => (element as HTMLButtonElement).click());
  await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
  await expect(page.getByText(/已确认版本 2/).first()).toBeVisible({ timeout: 60000 });
}

test.describe("regeneration journeys - fault stack", () => {
  test.skip(!faultGate, "set E2E_REGEN_FAULT=1 with the fake-adapter backend running");
  test.setTimeout(480000);

  test("TS-014: revise, preview impact, confirm, regenerate scoped, compare", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);
      await completeUnit(page);

      await reviseLesson2(page);

      // Embedded transition impact in the comparison view.
      await openVersionsTab(page);
      await expect(page.getByText(/受影响课时：/)).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/蓝图课时层字段变更/).first()).toBeVisible({ timeout: 30000 });

      // Scoped plan regeneration: only lesson 2 runs; the rest are retained.
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/沿用课程（\d+）/)).toBeVisible({ timeout: 60000 });
      await expect(page.getByText(/源版本：简报 v1 · 蓝图 v1/).first()).toBeVisible();
      await expect(page.getByText(/全部 1 课教案已生成/)).toBeVisible({ timeout: 240000 });

      // Comparison shows verdicts and old/new status.
      await openVersionsTab(page);
      await expect(page.getByText("受影响").first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText("沿用").first()).toBeVisible({ timeout: 30000 });
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });

  test("TS-016: keyboard pass over the revision path", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);
      await completeUnit(page);
      await reviseLesson2(page);

      // Keyboard-only: reach the comparison tab and read the embedded scope.
      const tab = page.getByRole("button", { name: "版本对比" });
      await tab.focus();
      await expect(tab).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.getByText(/意图差异/)).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/受影响课时：/)).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/蓝图课时层字段变更/).first()).toBeVisible({ timeout: 30000 });

      // Keyboard-only scoped start from the generation panel.
      const generationTab = page.getByRole("button", { name: "教案生成" });
      await generationTab.focus();
      await page.keyboard.press("Enter");
      const start = page.getByRole("button", { name: "开始生成" });
      await start.focus();
      await page.keyboard.press("Enter");
      await expect(page.getByText(/沿用课程（\d+）/)).toBeVisible({ timeout: 60000 });
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });
});

test.describe("regeneration journeys - live stack", () => {
  test.skip(!liveGate, "set E2E_REGEN_LIVE=1 with the live backend + worker running");
  test.setTimeout(600000);

  test("TS-015: live revision regenerates only the affected lesson", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 360000 });

      await reviseLesson2(page);
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/沿用课程（\d+）/)).toBeVisible({ timeout: 60000 });
      await expect(page.getByText(/全部 1 课教案已生成/)).toBeVisible({ timeout: 360000 });
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });
});
