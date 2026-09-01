import { expect, test } from "@playwright/test";
import { openWorkspace, PROFILE_DIR } from "./journey-helpers";

// F010 product-validation journey (test-design-f010-r1 TS-013).
//   E2E_EVAL_FAULT=1 -> fake-adapter backend (deterministic; zero model calls
//   in the Feature itself). Drives: 证据 panel -> 产品验证 region -> (one
//   deterministic technical pass first, which produces the complete package)
//   -> 创建评审分派 -> rubric sheet -> 导入量表证据 with a severe finding ->
//   honest 失败 outcome -> separate technical/product status on the alignment
//   panel. If the browser environment is unavailable (Clerk credentials or
//   backend), substitute coverage is green (backend TS-001..TS-009; component
//   TS-011/TS-012) and the block is recorded in the execution snapshot.

const evalGate = process.env.E2E_EVAL_FAULT === "1";

test.describe("product validation journey - fault stack", () => {
  test.skip(!evalGate, "set E2E_EVAL_FAULT=1 with the fake-adapter backend running");
  test.setTimeout(600000);

  test.beforeAll(async () => {
    const { clerkSetup } = await import("@clerk/testing/playwright");
    await clerkSetup();
  });

  test("TS-013: assign a package, import failing rubric evidence, see honest statuses", async () => {
    const { chromium } = await import("@playwright/test");
    const context = await chromium.launchPersistentContext(PROFILE_DIR);
    const page = context.pages()[0] ?? (await context.newPage());
    try {
      await openWorkspace(page);
      const projectName = `产品验证旅程 ${Date.now()}`;
      await page.getByRole("button", { name: "新建备课项目" }).click({ timeout: 30000 });
      await page.locator("#project-name").fill(projectName);
      await page.locator("#project-hints").fill("产品验证锚点项目");
      await page.getByRole("button", { name: "创建项目" }).click({ timeout: 30000 });
      await page.getByRole("link", { name: projectName }).first().click({ timeout: 30000 });

      await page.getByRole("button", { name: "运行证据" }).click({ timeout: 30000 });

      // Produce the complete package with one deterministic evaluation pass.
      await page.getByRole("button", { name: "启动评估" }).click({ timeout: 30000 });
      const dialog = page.getByRole("dialog");
      await dialog.getByLabel("确定性（脚本模型）").check({ timeout: 30000 });
      await dialog.getByRole("button", { name: "确认启动" }).click({ timeout: 30000 });
      await expect(page.getByText("已完成").first()).toBeVisible({ timeout: 240000 });

      // The product-validation region sits below the technical region.
      await expect(page.getByRole("heading", { name: "产品验证" })).toBeVisible({
        timeout: 30000,
      });
      await expect(page.getByText("尚未进行产品验证").first()).toBeVisible({ timeout: 30000 });

      // Fix the review assignment for the completed package.
      await page.getByRole("button", { name: "创建评审分派" }).click({ timeout: 30000 });
      const assignDialog = page.getByRole("dialog");
      await assignDialog.getByLabel("评估单元").selectOption("travelling-around");
      await assignDialog.getByRole("button", { name: "确认分派" }).click({ timeout: 30000 });
      const assignmentRow = page
        .getByRole("button")
        .filter({ hasText: "环游世界（英文输出）" })
        .first();
      await expect(assignmentRow).toBeVisible({ timeout: 30000 });
      await expect(page.getByText("待证据").first()).toBeVisible({ timeout: 30000 });

      // Expand the detail: bound package summary and the rubric hand-out.
      await assignmentRow.click({ timeout: 30000 });
      await expect(page.getByText(/绑定包：简报版本/)).toBeVisible({ timeout: 30000 });
      await expect(
        page.getByRole("button", { name: /评审量表（rubric-r1/ }),
      ).toBeVisible({ timeout: 30000 });

      // Import the evaluator's completed rubric with one severe finding.
      await page.getByRole("button", { name: "导入量表证据" }).click({ timeout: 30000 });
      for (const label of [
        "知识准确性证据说明",
        "语言质量证据说明",
        "练习与答案正确性证据说明",
        "目标对齐证据说明",
        "教学可用性证据说明",
      ]) {
        await page.getByLabel(label).fill(`${label}：内容准确、结构清晰，可支撑备课。`);
      }
      await page.getByRole("button", { name: "添加严重问题" }).click({ timeout: 30000 });
      await page.getByLabel("严重问题 1 类别").selectOption("answer_error");
      await page.getByLabel("严重问题 1 课时").fill("1");
      await page.getByLabel("严重问题 1 证据").fill("第 1 课练习参考答案与题目不匹配。");
      await page
        .getByLabel("原始量表文档")
        .setInputFiles({
          name: "rubric.pdf",
          mimeType: "application/pdf",
          buffer: Buffer.from("%PDF-1.4 evaluator original"),
        });

      await page.getByRole("button", { name: "导入量表证据" }).last().click({ timeout: 30000 });

      // Honest failure recorded; overall status failed; evidence visible.
      await expect(page.getByText(/产品验证状态：失败/)).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/判定：失败/).first()).toBeVisible({ timeout: 30000 });
      await expect(
        page.getByText(/答案错误（第 1 课）：第 1 课练习参考答案与题目不匹配。/),
      ).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/下载原始文档（私有）/)).toBeVisible({ timeout: 30000 });

      // Separation: the alignment panel keeps technical and product statuses
      // adjacent but distinct (technical validated, product failed).
      await page.getByRole("button", { name: "对齐与交付" }).click({ timeout: 30000 });
      await expect(
        page.getByText(/技术校验状态：技术校验通过/),
      ).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(/产品验证状态：失败/)).toBeVisible({ timeout: 30000 });
    } finally {
      await context.close();
    }
  });
});
