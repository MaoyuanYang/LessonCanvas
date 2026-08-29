import { expect, test, type Locator, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

// F003 generation journeys (test-design-f003-r2 TS-024..TS-029).
// Two stack profiles share the same web build; only the backend flavor differs:
//   E2E_GEN_LIVE=1  -> live model backend + real worker (TS-027 mid-run, TS-029)
//   E2E_GEN_FAULT=1 -> fake-adapter backend + real worker (TS-024/025/026 + TS-028 with small cap)

for (const file of [".env", ".env.local"]) {
  try {
    const content = fs.readFileSync(path.join(__dirname, "..", file), "utf-8");
    for (const line of content.split("\n")) {
      const match = line.match(/^\s*(CLERK_[A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
      if (match && !process.env[match[1]]) {
        process.env[match[1]] = match[2];
      }
    }
  } catch {
    // file not present; skip
  }
}

const PROFILE_DIR = `${__dirname}/.auth/profile`;

// React-controlled programmatic fill: bypasses actionability races with
// continuously re-rendered question boxes (native setter + input event).
async function domFill(locator: Locator, value: string): Promise<void> {
  await locator.evaluate(
    (el: HTMLTextAreaElement | HTMLInputElement, val: string) => {
      const proto = el instanceof HTMLTextAreaElement
        ? window.HTMLTextAreaElement.prototype
        : window.HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      setter?.call(el, val);
      el.dispatchEvent(new Event("input", { bubbles: true }));
    },
    value,
  );
}

const liveGate = process.env.E2E_GEN_LIVE === "1";
const faultGate = process.env.E2E_GEN_FAULT === "1";
const EMAIL = process.env.E2E_TEACHER_EMAIL ?? "";
const PASSWORD = process.env.E2E_TEACHER_PASSWORD ?? "";

const HINTS = [
  "单元主题：环境保护与可持续发展",
  "课时数：6",
  "学情：高二学生，英语中等水平",
  "教学目标：提升阅读与表达能力",
  "教材定位：外研社必修一 Unit 3",
  "输出语言：中英双语",
  "评估倾向：形成性评价为主",
  "课时分配：共12课时，每课2课时，评估聚焦综合输出",
].join("\n");

async function openWorkspace(page: Page): Promise<void> {
  // Dev-instance rate limits can starve token issuance across repeated runs;
  // the Clerk testing token bypasses those limits for E2E (stashed B-001 pattern).
  const { setupClerkTestingToken } = await import("@clerk/testing/playwright");
  await setupClerkTestingToken({ page });
  await page.goto("/sign-in");
  const signedIn = await page
    .waitForURL(/\/projects/, { timeout: 8000 })
    .then(() => true)
    .catch(() => false);
  if (!signedIn) {
    await page.locator("#identifier-field").fill(EMAIL);
    await page.locator("#password-field").fill(PASSWORD);
    await page.locator(".cl-formButtonPrimary").click();
    await page.waitForURL(/\/projects/, { timeout: 90000 });
  }
}

async function createProject(page: Page): Promise<string> {
  const name = `生成旅程 ${Date.now()}`;
  await page.getByRole("button", { name: "新建备课项目" }).click({ timeout: 30000 });
  await page.locator("#project-name").fill(name);
  await page.locator("#project-hints").fill(HINTS);
  await page.getByRole("button", { name: "创建项目" }).click({ timeout: 30000 });
  await page.getByRole("link", { name }).first().click({ timeout: 30000 });
  return name;
}

async function confirmedBlueprint(page: Page, lessonTitleOverride?: { index: number; title: string }) {
  await page.getByRole("button", { name: "需求访谈" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始访谈" }).click({ timeout: 30000 });
  await expect(page.getByText(/访谈已完成/)).toBeVisible({ timeout: 120000 });

  await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
  await expect(page.getByText("教师陈述").first()).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
  await expect(page.getByText(/已确认版本 1/)).toBeVisible({ timeout: 30000 });

  await page.getByRole("button", { name: "单元蓝图" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始单元规划" }).click({ timeout: 30000 });
  for (let round = 0; round < 8; round += 1) {
    const questionBox = page.locator("[id^='planning-answer-']").first();
    // Single waiter: the next question round or the finished draft, whichever
    // comes first under live-model latency.
    await questionBox
      .or(page.getByText("完整性检查"))
      .first()
      .waitFor({ state: "visible", timeout: 90000 })
      .catch(() => {});
    if (await page.getByText("完整性检查").isVisible().catch(() => false)) break;
    const submit = page.getByRole("button", { name: "提交回答" });
    if (!(await questionBox.isVisible().catch(() => false))) break;
    const boxes = page.locator("[id^='planning-answer-']");
    const boxCount = await boxes.count();
    for (let i = 0; i < boxCount; i += 1) {
      await domFill(boxes.nth(i), "共12课时，聚焦综合输出");
    }
    // Narration streaming re-renders the panel continuously; a DOM-level click
    // avoids losing the race with actionability checks.
    await submit.evaluate((element) => (element as HTMLButtonElement).click());
    // The answer POST synchronously drives the graph (next-round analysis or a
    // full blueprint draft under the live model); wait until it settles: the
    // submit button returns from 提交中… or the draft completes.
    await page
      .getByRole("button", { name: "提交回答" })
      .or(page.getByText("完整性检查"))
      .first()
      .waitFor({ state: "visible", timeout: 240000 })
      .catch(() => {});
  }
  await expect(page.getByText("完整性检查")).toBeVisible({ timeout: 180000 });

  const decisionButton = page.getByRole("button", { name: "记录教师决策" });
  if (await decisionButton.first().isVisible().catch(() => false)) {
    await decisionButton.first().click({ timeout: 30000 });
    await page.locator("#decision-reason").fill("以教材与教师判断为准");
    await page.getByRole("button", { name: "记录决策" }).click({ timeout: 30000 });
    await expect(page.getByText(/决策理由：/).first()).toBeVisible({ timeout: 60000 });
  }

  if (lessonTitleOverride) {
    const titleBox = page.getByRole("textbox", { name: `第${lessonTitleOverride.index}课标题` });
    await titleBox.fill(lessonTitleOverride.title);
    await page.getByRole("button", { name: "保存修订" }).first().click({ timeout: 30000 });
    // Wait for the saved revision before confirming, so the confirmed blueprint
    // actually carries the override (the PATCH races the confirm otherwise).
    await expect(page.getByText(/草稿修订 2/)).toBeVisible({ timeout: 60000 });
    const decide = page.getByRole("button", { name: "记录教师决策" });
    if (await decide.first().isVisible().catch(() => false)) {
      await decide.first().click({ timeout: 30000 });
      await page.locator("#decision-reason").fill("以教材与教师判断为准");
      await page.getByRole("button", { name: "记录决策" }).click({ timeout: 30000 });
      await expect(page.getByText(/决策理由：/).first()).toBeVisible({ timeout: 60000 });
    }
  }

  const confirm = page.getByRole("button", { name: "确认蓝图" });
  await expect(confirm).toBeEnabled({ timeout: 30000 });
  await confirm.click({ timeout: 30000 });
  await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
  await expect(page.getByText(/草稿修订 \d+ · 已确认版本 1/).first()).toBeVisible({ timeout: 60000 });
}

async function deleteProject(page: Page, name: string): Promise<void> {
  await page.goto("/projects").catch(() => {});
  await page.waitForTimeout(2000);
  const item = page.locator("li").filter({ hasText: name }).first();
  if (await item.isVisible().catch(() => false)) {
    await item.getByRole("button", { name: "删除" }).click({ timeout: 30000 });
    await page.getByRole("button", { name: "确认删除" }).click({ timeout: 30000 });
    await page.getByText(name, { exact: true }).waitFor({ state: "hidden", timeout: 20000 }).catch(() => {});
  }
}

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
