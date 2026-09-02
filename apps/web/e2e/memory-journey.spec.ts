import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import {
  createProject,
  deleteProject,
  domFill,
  HINTS,
  openWorkspace,
} from "./journey-helpers";

// F013 memory journeys (test-design-f013-r1 TS-023/TS-024/TS-025).
//   E2E_MEM_FAULT=1 -> fake-adapter backend (+ worker for proposal passes).
// Drives: brief confirm -> badge + proposal card -> confirm-with-edit ->
// account 教师记忆 management -> applied context in evidence (per-project
// toggle) -> record deletion -> honest no-application afterwards; plus the
// keyboard-only decision path and the 420px canonical reduced spot.
// When the browser environment is unavailable, substitute coverage is green
// (backend tests/test_memory.py; component __tests__/account-memory.test.tsx)
// and the block is recorded in the Test Design execution evidence snapshot.

const faultGate = process.env.E2E_MEM_FAULT === "1";

// The dev-server project list re-renders continuously (the known F004 M-1
// actionability race); this journey drives creation and navigation at the
// DOM level with bounded retries instead of losing the race.
async function createAndOpenProject(page: Page): Promise<{ name: string; id: string }> {
  const name = `生成旅程 ${Date.now()}`;
  await page.getByRole("button", { name: "新建备课项目" }).click({ timeout: 30000 });
  await domFill(page.locator("#project-name"), name);
  await domFill(page.locator("#project-hints"), HINTS);
  await page
    .getByRole("button", { name: "创建项目" })
    .evaluate((element) => (element as HTMLButtonElement).click());
  // The list item nodes are replaced on every poll re-render; resolve the
  // project id from the API and navigate directly instead of racing clicks.
  const token = await page.evaluate(() =>
    localStorage.getItem("lessoncanvas_workspace_token"),
  );
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const response = await page.request.get(
      `${process.env.E2E_API_BASE_URL ?? "http://localhost:8010"}/projects`,
      { headers: { authorization: `Bearer ${token}` } },
    );
    if (response.ok()) {
      const projects = (await response.json()) as Array<{ id: string; name: string }>;
      const created = projects.find((item) => item.name === name);
      if (created) {
        await page.goto(`/projects/${created.id}`);
        return { name, id: created.id };
      }
    }
    await page.waitForTimeout(800);
  }
  throw new Error(`created project not listed: ${name}`);
}

test.describe("teacher memory journeys - deterministic stack", () => {
  test.skip(!faultGate, "set E2E_MEM_FAULT=1 with the fake-adapter backend + worker running");
  test.setTimeout(900000);

  test("TS-023: propose -> confirm with edit -> apply in evidence -> delete", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      const created = await createAndOpenProject(page);
      projectName = created.name;

      // Interview to draft, then confirm the brief (proposal trigger D3).
      await page.getByRole("button", { name: "需求访谈" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始访谈" }).click({ timeout: 30000 });
      await expect(page.getByText(/访谈已完成/)).toBeVisible({ timeout: 120000 });

      await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
      await expect(page.getByText(/已确认版本 1/)).toBeVisible({ timeout: 30000 });

      // The badge appears and the brief panel hosts the proposal region; the
      // default fake derivation proposes the bilingual language preference.
      await expect(page.getByRole("button", { name: /条待处理记忆提议/ })).toBeVisible({
        timeout: 60000,
      });
      await expect(page.getByRole("heading", { name: "记忆提议" })).toBeVisible({
        timeout: 60000,
      });

      // Confirm with an inline edit first (live counter in the DOM).
      await page.getByRole("button", { name: "编辑后确认" }).first().click({ timeout: 30000 });
      const editor = page.getByLabel("编辑记忆内容").first();
      await domFill(editor, "输出语言偏好保持「中英双语」教学材料");
      await expect(page.getByText(/\/300 字符/).first()).toBeVisible({ timeout: 30000 });
      await page.getByRole("button", { name: "确认记住" }).first().click({ timeout: 30000 });

      // The default derivation proposes two candidates; deciding both
      // (confirm the language preference, reject the assessment one) clears
      // the pending badge honestly.
      // The badge accessible name is its aria-label (count first).
      await expect(
        page.getByRole("button", { name: /1 条待处理记忆提议/ }),
      ).toBeVisible({ timeout: 60000 });
      await page.getByRole("button", { name: "拒绝" }).first().click({ timeout: 30000 });
      await expect(
        page.getByRole("button", { name: /条待处理记忆提议/ }),
      ).toBeHidden({ timeout: 60000 });

      // Account management lists the confirmed record with the quota.
      await page.getByRole("link", { name: "账号与数据" }).click({ timeout: 30000 });
      await expect(page.getByRole("heading", { name: "教师记忆" })).toBeVisible({
        timeout: 30000,
      });
      await expect(
        page.getByText("输出语言偏好保持「中英双语」教学材料").first(),
      ).toBeVisible({ timeout: 30000 });
      await expect(page.getByText("1/20 条")).toBeVisible({ timeout: 30000 });

      // A later project applies the confirmed record end to end: its
      // discovery run is new evidence for the applied-context region
      // (planning/generation application is proven by backend TS-008).
      await page.goto("/projects");
      await createAndOpenProject(page);
      await page.getByRole("button", { name: "需求访谈" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始访谈" }).click({ timeout: 30000 });
      await expect(page.getByText(/访谈已完成/)).toBeVisible({ timeout: 120000 });

      // The evidence panel's 教师记忆（本项目） region shows the applied record
      // for the discovery run and offers the project-scoped toggle.
      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(page.getByRole("heading", { name: "教师记忆（本项目）" })).toBeVisible({
        timeout: 60000,
      });
      await expect(
        page.getByText("输出语言偏好保持「中英双语」教学材料").first(),
      ).toBeVisible({ timeout: 60000 });
      await expect(page.getByText(/当前运行的应用快照（1 条/)).toBeVisible({
        timeout: 60000,
      });

      // Project-scoped disable affects only this project's future runs.
      const toggle = page.getByLabel("在本项目停用该记忆");
      await toggle.click({ timeout: 30000 });
      await expect(page.getByText("本项目应用")).toBeVisible({ timeout: 30000 });

      // Delete the record from the account section; the honest empty state
      // returns and future runs apply nothing.
      await page
        .getByLabel("项目导航")
        .getByRole("link", { name: "账号与数据" })
        .click({ timeout: 30000 });
      await page.getByRole("button", { name: "删除", exact: true }).click({
        timeout: 30000,
      });
      await page.getByRole("button", { name: "确认删除" }).click({ timeout: 30000 });
      await expect(page.getByText("记忆已删除；今后的运行将不再应用它。")).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText("尚未确认任何教师记忆")).toBeVisible({ timeout: 30000 });
    } finally {
      await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-024: keyboard-only proposal decision path", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await page.getByRole("button", { name: "需求访谈" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始访谈" }).click({ timeout: 30000 });
      await expect(page.getByText(/访谈已完成/)).toBeVisible({ timeout: 120000 });
      await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });

      await expect(page.getByRole("button", { name: /条待处理记忆提议/ })).toBeVisible({
        timeout: 60000,
      });
      // Keyboard-only decision: Tab-walk verifies the path is reachable
      // without a pointer; locator.press focuses the target and sends the
      // Enter keypress (a real keyboard activation, no synthetic click).
      for (let step = 0; step < 60; step += 1) {
        const active = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (active.includes("确认记住")) break;
        await page.keyboard.press("Tab");
      }
      await expect
        .poll(async () => page.evaluate(() => document.activeElement?.textContent ?? ""))
        .toContain("确认记住");
      await page.getByRole("button", { name: "确认记住" }).first().press("Enter");
      // One candidate remains (the assessment proposal); reject it by
      // keyboard too, then the badge clears.
      await expect(
        page.getByRole("button", { name: /1 条待处理记忆提议/ }),
      ).toBeVisible({ timeout: 60000 });
      for (let step = 0; step < 60; step += 1) {
        const active = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (active.includes("拒绝")) break;
        await page.keyboard.press("Tab");
      }
      await page.getByRole("button", { name: "拒绝" }).first().press("Enter");
      await expect(page.getByRole("button", { name: /条待处理记忆提议/ })).toBeHidden({
        timeout: 60000,
      });
    } finally {
      await deleteProject(page, projectName).catch(() => {});
    }
  });

  test("TS-025: 420px canonical reduced experience spot", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);

      // Structured confirmation is a desktop flow; run it at full width,
      // then shrink for the reduced-experience spot on the memory surfaces.
      await page.getByRole("button", { name: "需求访谈" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始访谈" }).click({ timeout: 30000 });
      await expect(page.getByText(/访谈已完成/)).toBeVisible({ timeout: 120000 });
      await page.getByRole("button", { name: "教学简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认简报" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "确认", exact: true }).click({ timeout: 30000 });
      await page.setViewportSize({ width: 420, height: 900 });

      // The proposal surface stays usable at the reduced width.
      await expect(page.getByRole("heading", { name: "记忆提议" })).toBeVisible({
        timeout: 60000,
      });
      await expect(page.getByRole("button", { name: "确认记住" }).first()).toBeVisible({
        timeout: 30000,
      });
      // No horizontal overflow on the memory region.
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);

      // Structured record editing follows the desktop-required convention.
      await page.getByRole("link", { name: "账号与数据" }).click({ timeout: 30000 });
      await expect(page.getByRole("heading", { name: "教师记忆" })).toBeVisible({
        timeout: 60000,
      });
    } finally {
      await deleteProject(page, projectName).catch(() => {});
    }
  });
});
