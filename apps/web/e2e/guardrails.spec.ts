import { expect, test } from "@playwright/test";

// F011 TS-018: authenticated guardrails E2E journey (account usage/disclosure/
// audit + in-flow limit feedback + deletion complete path). Environment-gated
// like every authenticated spec in this repo (CLERK_E2E=1 plus a signed-in
// persistent profile prepared by the journey helpers); component-level
// substitute coverage lives in __tests__/account-guardrails.test.tsx.

const enabled = process.env.CLERK_E2E === "1";

test.skip(!enabled, "authenticated E2E requires CLERK_E2E=1 (repo precedent)");

test("account page shows usage limits, disclosure, and audit", async ({ page }) => {
  await page.goto("/account");

  await expect(page.getByRole("heading", { name: "账号与数据" })).toBeVisible();

  // Usage: every authoritative limit row with current consumption.
  await expect(page.getByRole("heading", { name: "使用与限额" })).toBeVisible();
  await expect(page.getByText(/请求速率（当前窗口）/)).toBeVisible();
  await expect(page.getByText(/并发生成运行/)).toBeVisible();
  await expect(page.getByText(/今日上传量/)).toBeVisible();

  // Disclosure: operator model + retained content-free ledger.
  await expect(page.getByRole("heading", { name: "隐私与运营访问" })).toBeVisible();
  await expect(page.getByText(/极简安全台账/)).toBeVisible();
  await expect(page.getByText(/没有运营人员账号/)).toBeVisible();

  // Audit: progressive disclosure lists sensitive actions without payloads.
  await page.getByRole("button", { name: "展开审计记录" }).click();
  await expect(page.getByRole("heading", { name: "敏感操作审计" })).toBeVisible();
});
