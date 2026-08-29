import { expect, type Locator, type Page } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

// Shared teacher-journey helpers for Playwright E2E specs (extracted unchanged
// from generation-journeys.spec.ts so deck journeys (F004) and lesson-plan
// journeys (F003) drive the identical UI path).

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

export const PROFILE_DIR = `${__dirname}/.auth/profile`;

// React-controlled programmatic fill: bypasses actionability races with
// continuously re-rendered question boxes (native setter + input event).
export async function domFill(locator: Locator, value: string): Promise<void> {
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

export const EMAIL = process.env.E2E_TEACHER_EMAIL ?? "";
export const PASSWORD = process.env.E2E_TEACHER_PASSWORD ?? "";

export const HINTS = [
  "单元主题：环境保护与可持续发展",
  "课时数：6",
  "学情：高二学生，英语中等水平",
  "教学目标：提升阅读与表达能力",
  "教材定位：外研社必修一 Unit 3",
  "输出语言：中英双语",
  "评估倾向：形成性评价为主",
  "课时分配：共12课时，每课2课时，评估聚焦综合输出",
].join("\n");

export async function openWorkspace(page: Page): Promise<void> {
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

export async function createProject(page: Page): Promise<string> {
  const name = `生成旅程 ${Date.now()}`;
  await page.getByRole("button", { name: "新建备课项目" }).click({ timeout: 30000 });
  await page.locator("#project-name").fill(name);
  await page.locator("#project-hints").fill(HINTS);
  await page.getByRole("button", { name: "创建项目" }).click({ timeout: 30000 });
  await page.getByRole("link", { name }).first().click({ timeout: 30000 });
  return name;
}

export async function confirmedBlueprint(page: Page, lessonTitleOverride?: { index: number; title: string }) {
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
    const saveButton = page.getByRole("button", { name: "保存修订" }).first();
    // The blueprint panel re-renders from authoritative state while open; a
    // re-render between fill and save can revert the input. Re-fill until the
    // input still holds the override AND save is enabled, then save and verify
    // the saved draft kept it before confirming.
    for (let attempt = 0; attempt < 6; attempt += 1) {
      await domFill(titleBox, lessonTitleOverride.title);
      const holds = await titleBox.inputValue().catch(() => "");
      const enabled = await saveButton.isEnabled().catch(() => false);
      if (holds === lessonTitleOverride.title && enabled) break;
      await page.waitForTimeout(800);
    }
    await expect(titleBox).toHaveValue(lessonTitleOverride.title, { timeout: 10000 });
    await saveButton.click({ timeout: 30000 });
    // Wait for the saved revision, then verify the persisted draft carries the
    // override (the PATCH races the confirm otherwise).
    await expect(page.getByText(/草稿修订 2/)).toBeVisible({ timeout: 60000 });
    await expect(
      page.getByRole("textbox", { name: `第${lessonTitleOverride.index}课标题` }),
    ).toHaveValue(lessonTitleOverride.title, { timeout: 30000 });
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

export async function deleteProject(page: Page, name: string): Promise<void> {
  await page.goto("/projects").catch(() => {});
  await page.waitForTimeout(2000);
  const item = page.locator("li").filter({ hasText: name }).first();
  if (await item.isVisible().catch(() => false)) {
    await item.getByRole("button", { name: "删除" }).click({ timeout: 30000 });
    await page.getByRole("button", { name: "确认删除" }).click({ timeout: 30000 });
    await page.getByText(name, { exact: true }).waitFor({ state: "hidden", timeout: 20000 }).catch(() => {});
  }
}

