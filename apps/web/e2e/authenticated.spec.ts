import { chromium, expect, test } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

const CODE_FILE = process.env.E2E_CODE_FILE ?? "";
const enabled = process.env.CLERK_E2E === "1";
const PROFILE_DIR = path.join(__dirname, ".auth", "profile");

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForCode(timeoutMs = 300000): Promise<string> {
  const started = Date.now();
  for (;;) {
    if (CODE_FILE && fs.existsSync(CODE_FILE)) {
      const code = fs.readFileSync(CODE_FILE, "utf8").trim();
      if (code.length >= 6) return code;
    }
    if (Date.now() - started > timeoutMs) throw new Error("verification code not provided in time");
    await sleep(2000);
  }
}

test.describe("authenticated teacher flow", () => {
  test.skip(!enabled, "set CLERK_E2E=1 to run");
  test.setTimeout(480000);

  test("sign in, create project, run discovery, confirm brief", async () => {
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());

    await page.goto("/sign-in");
    const alreadySignedIn = await page
      .waitForURL(/\/projects/, { timeout: 5000 })
      .then(() => true)
      .catch(() => false);

    if (!alreadySignedIn) {
      await page.locator("#identifier-field").fill(process.env.E2E_TEACHER_EMAIL ?? "");
      await page.locator("#password-field").fill(process.env.E2E_TEACHER_PASSWORD ?? "");
      await page.locator(".cl-formButtonPrimary").click();

      const needsCode = await Promise.race([
        page.waitForURL(/\/projects/, { timeout: 90000 }).then(() => false),
        page
          .getByText(/signing in from a new device/i)
          .waitFor({ timeout: 90000 })
          .then(() => true),
      ]);
      if (needsCode) {
        if (CODE_FILE) fs.writeFileSync(`${CODE_FILE}.requested`, new Date().toISOString());
        const code = await waitForCode();
        await page.locator("input[aria-label='Enter verification code']").fill(code);
        await page.locator(".cl-formButtonPrimary").click();
        await page.waitForURL(/\/projects/, { timeout: 90000 });
      }
    }

    await page.getByRole("button", { name: "新建备课项目" }).click();
    await page.locator("#project-name").fill(`E2E 自动化单元 ${Date.now()}`);
    await page
      .locator("#project-hints")
      .fill(
        "单元主题：环境保护与可持续发展\n课时数：6\n学情：高二学生，英语中等水平\n教学目标：提升阅读与表达能力\n教材定位：外研社必修一 Unit 3\n输出语言：中英双语\n评估倾向：形成性评价为主",
      );
    await page.getByRole("button", { name: "创建项目" }).click();
    await page.getByRole("link", { name: /E2E 自动化单元/ }).first().click();

    await page.getByRole("button", { name: "需求访谈" }).click();
    await page.getByRole("button", { name: "开始访谈" }).click();
    await expect(page.getByText(/访谈已完成/)).toBeVisible({ timeout: 120000 });

    await page.getByRole("button", { name: "教学简报" }).click();
    await expect(page.getByText("教师陈述").first()).toBeVisible({ timeout: 30000 });
    await page.getByRole("button", { name: "确认简报" }).click();
    await page.getByRole("button", { name: "确认", exact: true }).click();
    await expect(page.getByText(/已确认版本 1/)).toBeVisible({ timeout: 30000 });

    await context.close();
  });
});
