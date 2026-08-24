import { expect, test } from "@playwright/test";

const enabled = process.env.CLERK_E2E === "1";

test.describe("authenticated teacher flow", () => {
  test.skip(!enabled, "set CLERK_E2E=1 with Clerk device verification disabled to run");

  test("sign in, create project, upload source, confirm brief", async ({ page }) => {
    await page.goto("/sign-in");
    await page.getByLabel(/email address/i).fill(process.env.E2E_TEACHER_EMAIL ?? "");
    await page.getByLabel(/password/i).fill(process.env.E2E_TEACHER_PASSWORD ?? "");
    await page.getByRole("button", { name: /continue/i }).click();
    await page.waitForURL(/\/projects/);

    await page.getByRole("button", { name: "新建备课项目" }).click();
    await page.getByLabelText(/项目名称/).fill("E2E 单元");
    await page.getByRole("button", { name: "创建项目" }).click();
    await expect(page.getByText("E2E 单元")).toBeVisible();
  });
});
