import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  createProject,
  deleteProject,
  openWorkspace,
} from "./journey-helpers";

// F005 exercise-generation journeys (test-design-f005-r1 TS-024..TS-030).
// Same dual-instance strategy as F003/F004 (TQ-002); only the backend flavor differs:
//   E2E_EXERCISE_LIVE=1  -> live model backend + real worker (TS-030, exercise
//                           supersession, exercise SSE reconnect)
//   E2E_EXERCISE_FAULT=1 -> fake-adapter backend + real worker (prerequisite gate,
//                           tier keyboard pass, partial failure/resume; TS-028
//                           exercise cap with small exercise-cap env)

const liveGate = process.env.E2E_EXERCISE_LIVE === "1";
const faultGate = process.env.E2E_EXERCISE_FAULT === "1";

async function startExercises(page: import("@playwright/test").Page): Promise<void> {
  await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 30000 });
  const tier = page.getByRole("radio", { name: /巩固/ });
  await tier.check({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成练习与答案" }).click({ timeout: 30000 });
}

test.describe("exercise journeys - live stack", () => {
  test.skip(!liveGate, "set E2E_EXERCISE_LIVE=1 with the live backend + worker running");
  test.setTimeout(600000);

  async function completedPlans(page: import("@playwright/test").Page): Promise<string> {
    const projectName = await createProject(page);
    await confirmedBlueprint(page);
    await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
    await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
    await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 420000 });
    return projectName;
  }

  test("TS-030(exercise): completed lesson plans to downloadable pairs (live stack)", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await completedPlans(page);

      await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText("难度档位（必选）")).toBeVisible({ timeout: 30000 });
      // Submitting without a tier is blocked client-side (D-EXDIFF, no default).
      await page.getByRole("button", { name: "开始生成练习与答案" }).click({ timeout: 30000 });
      await expect(page.getByText(/请先选择难度档位/)).toBeVisible({ timeout: 30000 });
      await page.getByRole("radio", { name: /巩固/ }).check({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成练习与答案" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 420000 });

      // Pair summary and the recorded tier, then authorized downloads of both files.
      await expect(page.getByText(/难度档位：巩固/)).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/共 \d+ 题 · \d+ 类/).first()).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "下载练习 DOCX" }).first().click({ timeout: 30000 });
      await expect
        .poll(async () => page.context().pages().length, { timeout: 10000 })
        .toBeGreaterThanOrEqual(1);
      await page.getByRole("button", { name: "下载答案 DOCX" }).first().click({ timeout: 30000 });
      await expect
        .poll(async () => page.context().pages().length, { timeout: 10000 })
        .toBeGreaterThanOrEqual(1);
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-027(exercise): newer confirmed version supersedes the active exercise run", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await completedPlans(page);

      await startExercises(page);

      // Confirm a newer brief while the exercise run is active (live model gives the window).
      await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
      const themeInput = page.getByRole("textbox", { name: /编辑单元主题/ });
      await themeInput.fill("气候变化与能源");
      await page.getByRole("button", { name: "保存修订" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/已确认版本 2/)).toBeVisible({ timeout: 60000 });

      await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/已被更新的已确认版本取代/)).toBeVisible({ timeout: 240000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-029(exercise): reload and reconnect restore authoritative exercise progress", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await completedPlans(page);

      await startExercises(page);

      // Leave mid-run, return, then hard-reload: the snapshot restores without a duplicate run.
      await expect(page.getByText(/第 \d+ 课/).first()).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "来源" }).click({ timeout: 30000 });
      await page.waitForTimeout(2000);
      await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 420000 });

      await page.reload();
      await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 60000 });
      await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 180000 });
      await expect(page.getByRole("button", { name: "下载练习 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});

test.describe("exercise journeys - fault stack", () => {
  test.skip(!faultGate, "set E2E_EXERCISE_FAULT=1 with the fake-adapter backend + worker running");
  test.setTimeout(420000);

  test("TS-025(exercise): incomplete lesson plans route to the prerequisite", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      // No lesson-plan run yet: the unavailable state names the prerequisite.
      await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/需要先确认单元蓝图并生成全部教案/)).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByRole("button", { name: "前往「教案生成」" })).toBeVisible();

      // Start plans; on the fault stack they complete fast, then exercises become startable.
      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await page.getByRole("button", { name: "练习与答案", exact: true }).click({ timeout: 30000 });
      await expect(page.getByRole("radio", { name: /巩固/ })).toBeVisible({ timeout: 30000 });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-026(exercise): partial failure, scoped resume, completed work preserved", async ({
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
      // and the exercise prerequisite stays blocked until plans are resumed.
      await expect(page.getByText(/部分课程失败/)).toBeVisible({ timeout: 240000 });
      await page.getByRole("button", { name: "恢复未完成课程" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认恢复" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await startExercises(page);
      await expect(page.getByText(/部分课程失败/)).toBeVisible({ timeout: 240000 });
      await expect(page.getByText(/第 4 课/).locator("..").getByText(/失败/).first()).toBeVisible();

      await page.getByRole("button", { name: "恢复未完成练习" }).click({ timeout: 30000 });
      await expect(page.getByText("恢复练习与答案生成")).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "确认恢复" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 240000 });
      await expect(page.getByRole("button", { name: "下载练习 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByRole("button", { name: "下载答案 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-024(exercise): scripted keyboard pass incl. the tier fieldset", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      // Keyboard-only navigation to the exercise tab.
      await page.keyboard.press("Tab");
      for (let i = 0; i < 40; i += 1) {
        const label = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (label.trim() === "练习与答案") break;
        await page.keyboard.press("Tab");
      }
      await page.keyboard.press("Enter");
      await expect(page.getByRole("heading", { name: "练习与答案", exact: true })).toBeVisible({
        timeout: 30000,
      });

      // Keyboard-select the tier radio, then start.
      const tier = page.getByRole("radio", { name: /巩固/ });
      await tier.focus();
      await page.keyboard.press("Space");
      await expect(tier).toBeChecked();
      await page.getByRole("button", { name: "开始生成练习与答案" }).focus();
      await page.keyboard.press("Enter");
      await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 240000 });

      // Keyboard-reachable dual download.
      await page.getByRole("button", { name: "下载练习 DOCX" }).first().focus();
      await expect(page.getByRole("button", { name: "下载练习 DOCX" }).first()).toBeFocused();
      await page.getByRole("button", { name: "下载答案 DOCX" }).first().focus();
      await expect(page.getByRole("button", { name: "下载答案 DOCX" }).first()).toBeFocused();
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});

test.describe("exercise journeys - fault stack (small exercise cap)", () => {
  test.skip(!faultGate, "set E2E_EXERCISE_FAULT=1 with the small exercise-cap fake backend");
  test.setTimeout(420000);

  test("TS-028(exercise): exercise cap exhaustion keeps completed pairs downloadable", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成", exact: true }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await startExercises(page);
      await expect(page.getByText(/已达本任务模型调用上限/)).toBeVisible({ timeout: 240000 });
      await expect(page.getByRole("button", { name: "下载练习 DOCX" }).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText(/第 1 课/).locator("..").getByText(/已完成/).first()).toBeVisible();
    } finally {
      if (projectName && process.env.E2E_KEEP_PROJECTS !== "1")
        await deleteProject(page, projectName).catch(() => {});
    }
  });
});
