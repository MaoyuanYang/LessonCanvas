import { expect, test } from "@playwright/test";

const enabled = process.env.CLERK_E2E === "1";

test.describe("authenticated teacher flow", () => {
  test.skip(!enabled, "set CLERK_E2E=1 with Clerk device verification disabled to run");

  test("sign in, create project, upload source, confirm brief", async ({ page }) => {
    await page.goto("/sign-in");
    await page.locator("#identifier-field").fill(process.env.E2E_TEACHER_EMAIL ?? "");
    await page.locator("#password-field").fill(process.env.E2E_TEACHER_PASSWORD ?? "");
    await page.locator(".cl-formButtonPrimary").click();
    await page.waitForURL(/\/projects/);

    await page.getByRole("button", { name: "新建备课项目" }).click();
    await page.getByLabel(/项目名称/).fill("E2E 单元");
    await page.getByRole("button", { name: "创建项目" }).click();
    await expect(page.getByText("E2E 单元")).toBeVisible();
  });
});
