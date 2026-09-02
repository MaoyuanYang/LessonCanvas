import { expect, test } from "@playwright/test";
import {
  confirmedBlueprint,
  createProject,
  deleteProject,
  openWorkspace,
} from "./journey-helpers";

// F008 alignment journeys (test-design-f008-r1 TS-016/TS-017).
//   E2E_ALIGN_FAULT=1 -> fake-adapter backend (deterministic; no model needed
//   by design). TS-016 drives the validated-package browser path end to end
//   (alignment view -> status pair -> validated export -> labelled ZIP
//   download -> printable report). The scripted-override browser journey
//   (DECK_TOO_LONG revision -> override) is recorded as an environment
//   residual in the Test Design execution snapshot: substitute coverage is
//   green (backend TS-005/006/007 override lifecycle; component TS-015
//   override dialog with recalculation), same owner-accepted pattern as the
//   F004 M-1 browser-environment residual.

const faultGate = process.env.E2E_ALIGN_FAULT === "1";

async function completeUnit(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
  await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });
  await page.getByRole("button", { name: "课件生成" }).click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
  await expect(page.getByText(/全部 \d+ 课课件已生成/)).toBeVisible({ timeout: 240000 });
  await page.getByRole("button", { name: "练习与答案" }).click({ timeout: 30000 });
  await page.getByLabel("基础").click({ timeout: 30000 });
  await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
  await expect(page.getByText(/全部 \d+ 课练习已生成/)).toBeVisible({ timeout: 240000 });
}

test.describe("alignment journeys - fault stack", () => {
  test.skip(!faultGate, "set E2E_ALIGN_FAULT=1 with the fake-adapter backend running");
  test.setTimeout(900000);

  test("TS-016: alignment view, validated export, labelled ZIP, print report", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);
      await completeUnit(page);

      // Alignment view: status pair with validated technical status and the
      // separate, always-visible not-evaluated product status.
      await page.getByRole("button", { name: "对齐与交付" }).click({ timeout: 30000 });
      await expect(page.getByText(/技术校验状态：技术校验通过/)).toBeVisible({ timeout: 60000 });
      await expect(page.getByText(/产品验证状态：未评估/)).toBeVisible();
      await expect(page.getByText("教学目标覆盖")).toBeVisible();
      await expect(page.getByText("未发现覆盖缺口或冲突。")).toBeVisible();

      // Validated export is enabled and labelled; history records it.
      await page.getByRole("button", { name: "交付校验包" }).click({ timeout: 30000 });
      await expect(page.getByText("导出历史")).toBeVisible({ timeout: 120000 });
      await expect(page.getByText("校验包").first()).toBeVisible({ timeout: 60000 });

      // Keyboard path: focus and activate the ZIP download.
      const downloadButton = page.getByRole("button", { name: "下载 ZIP" }).first();
      await downloadButton.focus();
      await expect(downloadButton).toBeFocused();
      await downloadButton.press("Enter");
      const download = await page.waitForEvent("download", { timeout: 60000 });
      expect((await download.suggestedFilename()).startsWith("lessoncanvas-")).toBeTruthy();

      // Printable report route carries versions, status pair, and coverage.
      const reportPage = await page.context().newPage();
      await reportPage.goto(`${page.url().split("?")[0]}/report?source=current`);
      await expect(reportPage.getByRole("heading", { name: "单元对齐报告" })).toBeVisible({
        timeout: 60000,
      });
      await expect(reportPage.getByText(/简报 v1 · 蓝图 v1/)).toBeVisible();
      await expect(reportPage.getByText(/技术校验状态 = 技术校验通过/)).toBeVisible();
      await expect(reportPage.getByText(/产品验证状态 = 未评估/)).toBeVisible();
      await expect(reportPage.getByText("目标覆盖汇总")).toBeVisible();
      await expect(reportPage.getByText("未发现覆盖缺口或冲突。")).toBeVisible();
      await reportPage.close();
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });

  test("TS-017: family completion banner links into the alignment view", async ({ page }) => {
    let projectName = "";
    try {
      await openWorkspace(page);
      projectName = await createProject(page);
      await confirmedBlueprint(page);
      await page.getByRole("button", { name: "教案生成" }).click({ timeout: 30000 });
      await page.getByRole("button", { name: "开始生成" }).click({ timeout: 30000 });
      await expect(page.getByText(/全部 \d+ 课教案已生成/)).toBeVisible({ timeout: 240000 });

      const link = page.getByRole("button", { name: "查看对齐情况" });
      await expect(link).toBeVisible();
      await link.click();
      await expect(page.getByText(/技术校验状态：/)).toBeVisible({ timeout: 60000 });
    } finally {
      if (projectName) await deleteProject(page, projectName);
    }
  });
});
