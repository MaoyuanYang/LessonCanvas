import { expect, test } from "@playwright/test";
import { deleteProject, openWorkspace, PROFILE_DIR } from "./journey-helpers";

// F009 technical-evaluation journey (test-design-f009-r1 TS-016).
//   E2E_EVAL_FAULT=1 -> fake-adapter backend (deterministic; no live model).
//   Drives: 证据 panel -> 技术评估 region -> 启动评估 modal (deterministic mode,
//   cost sentence checked for live mode) -> queued/active states -> completed
//   criterion outcomes with evidence expansion -> print-styled report route.
//   If the browser environment is unavailable (Clerk credentials/backend),
//   substitute coverage is green (backend TS-004/005/012; component TS-014/015)
//   and the block is recorded in the Test Design execution snapshot.

const evalGate = process.env.E2E_EVAL_FAULT === "1";

test.describe("technical evaluation journey - fault stack", () => {
  test.skip(!evalGate, "set E2E_EVAL_FAULT=1 with the fake-adapter backend running");
  test.setTimeout(600000);

  test.beforeAll(async () => {
    const { clerkSetup } = await import("@clerk/testing/playwright");
    await clerkSetup();
  });

  test("TS-016: start deterministic pass, inspect outcomes, open report", async () => {
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = `技术评估旅程 ${Date.now()}`;
      await page.getByRole("button", { name: "新建备课项目" }).click({ timeout: 30000 });
      await page.locator("#project-name").fill(projectName);
      await page.locator("#project-hints").fill("技术评估锚点项目");
      await page.getByRole("button", { name: "创建项目" }).click({ timeout: 30000 });
      await page.getByRole("link", { name: projectName }).first().click({ timeout: 30000 });

      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });
      await expect(page.getByRole("heading", { name: "技术评估" })).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText("尚未运行技术评估")).toBeVisible({ timeout: 30000 });

      await page.getByRole("button", { name: "启动评估" }).click({ timeout: 30000 });
      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible({ timeout: 30000 });
      await dialog.getByLabel("真实模型").check({ timeout: 30000 });
      await expect(
        dialog.getByText("真实模型运行将产生实际模型费用"),
      ).toBeVisible({ timeout: 30000 });
      await dialog.getByLabel("确定性（脚本模型）").check({ timeout: 30000 });
      await dialog.getByRole("button", { name: "确认启动" }).click({ timeout: 30000 });

      await expect(page.getByText(/第 1 遍/).first()).toBeVisible({ timeout: 240000 });
      await expect(page.getByText("已完成").first()).toBeVisible({ timeout: 240000 });

      const passRow = page.getByRole("button").filter({ hasText: "第 1 遍" }).first();
      await passRow.click({ timeout: 30000 });
      await expect(page.getByText("阻断判定")).toBeVisible({ timeout: 30000 });
      await expect(page.getByText("诊断指标（非阻断）")).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/记忆状态：/).first()).toBeVisible({ timeout: 30000 });

      const pagePromise = context.waitForEvent("page");
      await page.getByRole("link", { name: "打印技术评估报告" }).click({ timeout: 30000 });
      const reportPage = await pagePromise;
      await expect(reportPage.getByRole("heading", { name: "技术评估报告" })).toBeVisible({
        timeout: 30000,
      });
      await expect(reportPage.getByText(/产品验证状态 = 未评估/)).toBeVisible({
        timeout: 30000,
      });
      await expect(reportPage.getByText(/阻断判定结果|阻断判据/).first()).toBeVisible({
        timeout: 30000,
      });
      await reportPage.close();
    } finally {
      await deleteProject(page, projectName).catch(() => {});
      await context.close();
    }
  });
});
