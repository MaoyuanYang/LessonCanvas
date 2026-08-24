import { expect, test } from "@playwright/test";

test.describe("public entry", () => {
  test("renders product boundary and privacy copy", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "LessonCanvas" })).toBeVisible();
    await expect(page.getByText(/仅属于你的工作区/)).toBeVisible();
  });

  test("keyboard user can reach the sign-in action", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const focused = page.getByRole("button", { name: "登录并开始备课" });
    await expect(focused).toBeFocused();
  });

  test("protected route redirects unauthenticated users to sign-in", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForURL(/\/sign-in/);
    await expect(page.getByText(/Welcome back|Please sign in/i)).toBeVisible();
  });
});
