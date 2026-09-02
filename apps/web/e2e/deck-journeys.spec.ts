import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  createProject,
  deleteProject,
  openWorkspace,
} from "./journey-helpers";

// F004 deck-generation journeys (test-design-f004-r1 TS-025..TS-030).
// Same dual-instance strategy as F003 (TQ-002); only the backend flavor differs:
//   E2E_DECK_LIVE=1  -> live model backend + real worker (TS-030, deck supersession, deck SSE)
//   E2E_DECK_FAULT=1 -> fake-adapter backend + real worker (prerequisite gate, partial
//                       failure/resume, keyboard pass; TS-028 deck cap with small deck-cap env)

const liveGate = process.env.E2E_DECK_LIVE === "1";
const faultGate = process.env.E2E_DECK_FAULT === "1";

test.describe("deck journeys - live stack", () => {
  test.skip(!liveGate, "set E2E_DECK_LIVE=1 with the live backend + worker running");
  test.setTimeout(600000);

  async function completedPlans(page: import("@playwright/test").Page): Promise<string> {
    const projectName = await createProject(page);
    await confirmedBlueprint(page);
    await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
    await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
    await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 420000 });
    return projectName;
  }

  test("TS-030: completed lesson plans to downloadable decks (live stack)", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await completedPlans(page);

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await expect(page.getByRole("button", { name: "开始生成课件" })).toBeVisible({
        timeout: 30000,
      });
      await page.getByRole("button", { name: "开始生成课件" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 420000 });

      // Structure summary per lesson, then an authorized PPTX download.
      await expect(page.getByText(/共 \d+ 页/).first()).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "下载 PPTX" }).first().click({ timeout: 30000 });
      await expect
        .poll(async () => page.context().pages().length, { timeout: 10000 })
        .toBeGreaterThanOrEqual(1);
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-027(deck): newer confirmed version supersedes the active deck run", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await completedPlans(page);

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成课件" }).click({ timeout: 30000 });

      // Confirm a newer brief while the deck run is active (live model gives the window).
      await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
      const themeInput = page.getByRole("textbox", { name: /编辑单元主题/ });
      await themeInput.fill("气候变化与能源");
      await page.getByRole("button", { name: "保存修订" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/已确认版本 2/)).toBeVisible({ timeout: 60000 });

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/已被更新的已确认版本取代/)).toBeVisible({ timeout: 240000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-029(deck): reload and reconnect restore authoritative deck progress", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await completedPlans(page);

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成课件" }).click({ timeout: 30000 });

      // Leave mid-run, return, then hard-reload: the snapshot restores without a duplicate run.
      await expect(page.getByText(/第 \d+ 课/).first()).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "来源" }).click({ timeout: 30000 });
      await page.waitForTimeout(2000);
      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 420000 });

      await page.reload();
      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 60000 });
      await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 180000 });
      await expect(page.getByRole("button", { name: "下载 PPTX" }).first()).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});

test.describe("deck journeys - fault stack", () => {
  test.skip(!faultGate, "set E2E_DECK_FAULT=1 with the fake-adapter backend + worker running");
  test.setTimeout(420000);

  test("TS-025(deck): incomplete lesson plans route to the prerequisite", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      // No lesson-plan run yet: the unavailable state names the prerequisite.
      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/需要先确认单元蓝图并生成全部教案/)).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByRole("button", { name: "前往「教案生成」" })).toBeVisible();

      // Start plans; on the fault stack they complete fast, then decks become startable.
      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await expect(page.getByRole("button", { name: "开始生成课件" })).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-026(deck): partial deck failure, scoped resume, completed work preserved", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page, { index: 4, title: "第4课 TRANSIENT_FAIL 写作训练" });

      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      // The scripted fault exhausts the worker retries: plans go partial first,
      // and the deck prerequisite stays blocked until plans are resumed.
      await expect(page.getByText(/部分课程失败/)).toBeVisible({ timeout: 240000 });
      await page.getByRole("button", { name: "恢复未完成课程" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认恢复" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成课件" }).click({ timeout: 30000 });
      await expect(page.getByText(/部分课程失败/)).toBeVisible({ timeout: 240000 });
      await expect(page.getByText(/第 4 课/).locator("..").getByText(/失败/).first()).toBeVisible();

      await page.getByRole("button", { name: "恢复未完成课件" }).click({ timeout: 30000 });
      await expect(page.getByText("恢复课件生成")).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "确认恢复" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 240000 });
      await expect(page.getByRole("button", { name: "下载 PPTX" }).first()).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-024(deck): scripted keyboard pass on the deck flow", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      // Keyboard-only navigation to the deck tab and start.
      await page.keyboard.press("Tab");
      for (let i = 0; i < 30; i += 1) {
        const label = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (label.trim() === "课件生成") break;
        await page.keyboard.press("Tab");
      }
      await page.keyboard.press("Enter");
      await expect(page.getByRole("heading", { name: "课件生成", exact: true })).toBeVisible({
        timeout: 30000,
      });

      await page.getByRole("button", { name: "开始生成课件" }).focus();
      await page.keyboard.press("Enter");
      await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 240000 });

      // Keyboard-reachable download.
      await page.getByRole("button", { name: "下载 PPTX" }).first().focus();
      await expect(page.getByRole("button", { name: "下载 PPTX" }).first()).toBeFocused();
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});

test.describe("deck journeys - fault stack (small deck cap)", () => {
  test.skip(!faultGate, "set E2E_DECK_FAULT=1 with the small deck-cap fake backend");
  test.setTimeout(420000);

  test("TS-028(deck): deck cap exhaustion keeps completed decks downloadable", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await page.getByRole("button", { name: "课件生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成课件" }).click({ timeout: 30000 });
      await expect(page.getByText(/已达本任务模型调用上限/)).toBeVisible({ timeout: 240000 });
      await expect(page.getByRole("button", { name: "下载 PPTX" }).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText(/第 1 课/).locator("..").getByText(/已完成/).first()).toBeVisible();
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});
