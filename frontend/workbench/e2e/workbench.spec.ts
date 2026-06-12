import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

// Automated replacement for the manual browser smoke checklist in
// docs/workbench_spa_handoff.md ("Completed Visual / Offline Work").

async function openReview(page: Page) {
  await page.goto("/");
  await expect(page.locator(".queue-list .queue-row").first()).toBeVisible();
}

function queueRow(page: Page, refdes: string) {
  return page.locator(".queue-row").filter({
    has: page.locator("span.refdes", { hasText: new RegExp(`^${refdes}$`) })
  });
}

async function pickComponent(page: Page, refdes: string) {
  const row = queueRow(page, refdes);
  await row.click();
  await expect(row).toHaveClass(/selected/);
  // Detail column reflects the picked component.
  await expect(page.locator(".detail-panel h2")).toHaveText(refdes);
  // Evidence column follows the same selection.
  await expect(page.locator(".evidence-panel h2")).toHaveText(`${refdes} 为什么被提醒`);
}

test("queue clicks on Q12 / U8 / U12 update detail and evidence columns", async ({ page }) => {
  await openReview(page);
  for (const refdes of ["Q12", "U8", "U12"]) {
    await pickComponent(page, refdes);
  }
});

test("copilot wraps unknown refdes U999 as ⟨?U999⟩", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "AI 助手" }).click();
  const input = page.locator(".composer-box input");
  await input.fill("板上有没有 U999?");
  await page.locator(".composer-box button[type=submit]").click();
  await expect(page.locator(".msg.ai .mtext").last()).toContainText("⟨?U999⟩", {
    timeout: 30_000
  });
});

test("prep packet preview opens for Q12", async ({ page }) => {
  await openReview(page);
  await pickComponent(page, "Q12");
  await page.locator(".prep-actions").getByRole("button", { name: "预览" }).click();
  const preview = page.locator(".prep-preview");
  await expect(preview).toBeVisible();
  await expect(preview).toContainText("Q12");
});

test("import page can reload the built-in demo files", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "导入" }).click();
  await expect(page.locator(".upload-slot").first()).toContainText("拖入文件或点击选择");
  await page
    .locator('input[accept=".net,.dat,.txt,.pst"]')
    .setInputFiles(path.resolve("../../tests/fixtures/allegro/mixed_controller_power_stage.net"));
  await page
    .locator('input[accept=".csv,.tsv,.txt"]')
    .setInputFiles(
      path.resolve("../../tests/fixtures/allegro/mixed_controller_power_stage_bom.csv")
    );
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(page.locator(".parse-step").first()).toBeVisible();
  await expect(page.locator(".queue-list .queue-row").first()).toBeVisible({ timeout: 30_000 });
});

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 760, height: 900 }
]) {
  test(`no horizontal overflow at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openReview(page);
    const overflow = await page.evaluate(() => {
      const root = document.documentElement;
      return {
        scrollWidth: Math.max(root.scrollWidth, document.body.scrollWidth),
        clientWidth: root.clientWidth
      };
    });
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth);
  });
}
