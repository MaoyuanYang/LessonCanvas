import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  createProject,
  deleteProject,
  openWorkspace,
} from "./journey-helpers";

// F006 evidence journeys (test-design-f006-r1 TS-020/021/022).
// Two stack profiles share the same web build; only the backend flavor differs:
//   E2E_EVID_LIVE=1   -> live model backend + real worker (TS-021)
//   E2E_EVID_FAULT=1  -> fake-adapter backend (TS-020 fault stack + TS-022 keyboard pass)

const liveGate = process.env.E2E_EVID_LIVE === "1";
const faultGate = process.env.E2E_EVID_FAULT === "1";

test.describe("evidence journeys - fault stack", () => {
  test.skip(!faultGate, "set E2E_EVID_FAULT=1 with the fake-adapter backend running");
  test.setTimeout(300000);

  test("TS-020a: empty evidence view explains emptiness and names the first action", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(page.getByText("还没有任何运行记录")).toBeVisible({ timeout: 30000 });
      await expect(page.getByRole("button", { name: "前往「来源」开始" })).toBeVisible();
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });

  test("TS-020: inventory, summary, technical expansion, and narration", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(page.getByText("教案生成").first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/需求访谈/).first()).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/蓝图规划/).first()).toBeVisible({ timeout: 30000 });

      // Teacher summary first: versions, status, usage, estimate labeling.
      await expect(page.getByText(/绑定版本：教学简报 v1 · 单元蓝图 v1/)).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText(/模型调用/).first()).toBeVisible();
      await expect(page.getByText(/估算/).first()).toBeVisible();

      // Technical expansion: labelled rows with metrics, payload disclosure.
      await expect(page.getByRole("heading", { name: "技术证据" })).toBeVisible({
        timeout: 30000,
      });
      await expect(
        page.getByRole("button", { name: /模型调用·撰写教案/ }).first(),
      ).toBeVisible({ timeout: 30000 });
      const firstRow = page.getByRole("button", { name: /模型调用·撰写教案/ }).first();
      await firstRow.click({ timeout: 30000 });
      await expect(page.getByRole("button", { name: "复制原始数据" }).first()).toBeVisible();
      await expect(page.locator("pre").first()).toBeVisible();

      // Narration streams and lands; nothing about the run changes.
      await page.getByRole("button", { name: "讲解本任务" }).click({ timeout: 30000 });
      await expect(page.locator("[aria-label='任务讲解']")).toContainText(/。/, {
        timeout: 60000,
      });
      await expect(page.getByText("教案生成").first()).toBeVisible();
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });

  test("TS-022: keyboard-only pass over the evidence view (B-001)", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      // Keyboard-only: reach the evidence tab by Tab/Enter from the tab bar.
      await page.getByRole("button", { name: "运行证据" }).focus();
      await page.keyboard.press("Enter");
      await expect(page.getByText(/绑定版本：教学简报 v1/)).toBeVisible({ timeout: 30000 });

      // Inventory rows are reachable and operable by keyboard.
      const inventoryButton = page.locator("[aria-label='运行清单'] button").first();
      await inventoryButton.focus();
      await expect(inventoryButton).toBeFocused();
      await page.keyboard.press("Enter");

      // Technical rows expand by keyboard and the disclosure state is announced.
      const evidenceRow = page.getByRole("button", { name: /模型调用·撰写教案/ }).first();
      await evidenceRow.focus();
      await expect(evidenceRow).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.getByRole("button", { name: "复制原始数据" }).first()).toBeVisible();
      await expect(evidenceRow).toHaveAttribute("aria-expanded", "true");

      // Narration start/stop by keyboard; stop is available while streaming.
      const narrateButton = page.getByRole("button", { name: "讲解本任务" });
      await narrateButton.focus();
      await page.keyboard.press("Enter");
      await expect(page.locator("[aria-label='任务讲解']")).toBeVisible({ timeout: 60000 });
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });
});

test.describe("evidence journeys - live stack", () => {
  test.skip(!liveGate, "set E2E_EVID_LIVE=1 with the live backend + worker running");
  test.setTimeout(480000);

  test("TS-021: live run carries token/cost/model evidence and streams a real explanation", async ({
    page,
  }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);

      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 360000 });

      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(page.getByText(/绑定版本：教学简报 v1 · 单元蓝图 v1/)).toBeVisible({
        timeout: 30000,
      });

      // Post-F006 events on the live provider carry token usage and model ids.
      await expect(page.getByText(/输入 \d+ \/ 输出 \d+/).first()).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText(/deepseek/).first()).toBeVisible({ timeout: 30000 });

      // Payload text renders inertly as data.
      const firstRow = page.getByRole("button", { name: /模型调用·撰写教案/ }).first();
      await firstRow.click({ timeout: 30000 });
      await expect(page.locator("pre").first()).toBeVisible();

      // Real explanation narration completes against the live provider.
      await page.getByRole("button", { name: "讲解本任务" }).click({ timeout: 30000 });
      await expect(page.locator("[aria-label='任务讲解']")).toContainText(/。/, {
        timeout: 120000,
      });
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });
});
