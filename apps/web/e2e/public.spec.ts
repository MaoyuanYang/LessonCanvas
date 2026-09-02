import { expect, test } from "@playwright/test";

test.describe("public entry", () => {
  test("renders product boundary and privacy copy", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "LessonCanvas" })).toBeVisible();
    await expect(page.getByText(/仅属于你的工作区/)).toBeVisible();
  });

  test("landing CTA links straight into the workspace", async ({ page }) => {
    await page.goto("/");
    const cta = page.getByRole("link", { name: "进入备课工作台" });
    await expect(cta).toHaveAttribute("href", "/projects");
    await expect(page.getByRole("button", { name: /登录/ })).toHaveCount(0);
  });

  test("workspace route loads the project list directly without a sign-in redirect", async ({
    page,
  }) => {
    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: "备课项目" })).toBeVisible({ timeout: 30000 });
    await expect(page).not.toHaveURL(/\/sign-in/);
  });

  test("keyboard user can reach the primary action via tab", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const focused = page.getByRole("link", { name: "进入备课工作台" });
    await expect(focused).toBeFocused();
  });
});
