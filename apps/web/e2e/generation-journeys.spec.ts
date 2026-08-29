import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  createProject,
  deleteProject,
  openWorkspace,
  PROFILE_DIR,
} from "./journey-helpers";

// F003 generation journeys (test-design-f003-r2 TS-024..TS-029).
// Two stack profiles share the same web build; only the backend flavor differs:
//   E2E_GEN_LIVE=1  -> live model backend + real worker (TS-027 mid-run, TS-029)
//   E2E_GEN_FAULT=1 -> fake-adapter backend + real worker (TS-024/025/026 + TS-028 with small cap)

const liveGate = process.env.E2E_GEN_LIVE === "1";
const faultGate = process.env.E2E_GEN_FAULT === "1";

test.describe("generation journeys - live stack", () => {
  test.skip(!liveGate, "set E2E_GEN_LIVE=1 with the live backend + worker running");
  test.setTimeout(480000);

  test.beforeAll(async () => {
    const { clerkSetup } = await import("@clerk/testing/playwright");
    await clerkSetup();
  });

  test("TS-029: leaving, reconnecting, and reloading restore authoritative progress", async ({
    page: _,
  }) => {
    test.skip(!liveGate, "live gate");
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });

      // Leave mid-run (narration/progress display stops; the run continues).
      await expect(page.getByText(/第 \d+ 课/).first()).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "来源" }).click({ timeout: 30000 });
      await page.waitForTimeout(2000);

      // Return: progress restores from the authoritative snapshot, then completes.
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      // Hard reload mid-completed state: snapshot restores without a duplicate run.
      await page.reload();
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 60000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 180000 });
      await expect(page.getByRole("button", { name: "下载 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
    void _;
  });

  test("TS-027: newer confirmed version supersedes the active run", async ({ page: _ }) => {
    test.skip(!liveGate, "live gate");
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });

      // Confirm a newer brief while the run is active (live model gives the window).
      await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
      const themeInput = page.getByRole("textbox", { name: /编辑单元主题/ });
      await themeInput.fill("气候变化与能源");
      await page.getByRole("button", { name: "保存修订" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/已确认版本 2/)).toBeVisible({ timeout: 60000 });

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/已被更新的已确认版本取代/)).toBeVisible({ timeout: 240000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
    void _;
  });
});

test.describe("generation journeys - fault stack", () => {
  test.skip(!faultGate, "set E2E_GEN_FAULT=1 with the fake-adapter backend + worker running");
  test.setTimeout(300000);

  test.beforeAll(async () => {
    const { clerkSetup } = await import("@clerk/testing/playwright");
    await clerkSetup();
  });

  test("TS-025: start without a confirmed blueprint routes to the gate", async () => {
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/需要先确认教学简报与单元蓝图/)).toBeVisible({ timeout: 30000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
  });

  test("TS-026: partial failure, scoped resume, completed work preserved", async () => {
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page, { index: 4, title: "第4课 TRANSIENT_FAIL 写作训练" });

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/部分课程失败/)).toBeVisible({ timeout: 120000 });
      await expect(page.getByText(/第 4 课/).locator("..").getByText(/失败/).first()).toBeVisible();

      await page.getByRole("button", { name: "恢复未完成课程" }).click({ timeout: 30000 });
      await expect(page.getByText("恢复生成")).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "确认恢复" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 180000 });
      await expect(page.getByRole("button", { name: "下载 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
  });

  test("TS-024: scripted keyboard pass on the generation flow", async () => {
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      // Keyboard-only navigation to the generation tab and start.
      await page.keyboard.press("Tab");
      for (let i = 0; i < 12; i += 1) {
        const label = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (label.trim() === "教案生成") break;
        await page.keyboard.press("Tab");
      }
      await page.keyboard.press("Enter");
      await expect(page.getByRole("heading", { name: "教案生成" })).toBeVisible({
        timeout: 30000,
      });

      await page.getByRole("button", { name: "开始生成" }).focus();
      await page.keyboard.press("Enter");
      await expect(page.getByText(/全部 \d+ 课教案已生成|生成中|排队中/).first()).toBeVisible({
        timeout: 60000,
      });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 180000 });

      // Keyboard-reachable download.
      await page.getByRole("button", { name: "下载 DOCX" }).first().focus();
      await expect(page.getByRole("button", { name: "下载 DOCX" }).first()).toBeFocused();
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
  });
});

test.describe("generation journeys - fault stack (small cap)", () => {
  test.skip(!faultGate, "set E2E_GEN_FAULT=1 with the small-cap fake backend");
  test.setTimeout(300000);

  test.beforeAll(async () => {
    const { clerkSetup } = await import("@clerk/testing/playwright");
    await clerkSetup();
  });

  test("TS-028: cap exhaustion keeps completed lessons downloadable", async () => {
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/已达本任务模型调用上限/)).toBeVisible({ timeout: 120000 });
      await expect(page.getByRole("button", { name: "下载 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText(/第 1 课/).locator("..").getByText(/已完成/).first()).toBeVisible();
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
  });
});
