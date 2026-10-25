import { expect, test } from "@playwright/test";
import path from "node:path";

test.use({ baseURL: "http://127.0.0.1:4400" });

test("white save and open restore the saved project and reason after another import", async ({ page, request }, info) => {
  const initial = await (await request.get("/api/workbench/state")).json();
  const key = initial.review_tasks.find((t: { kind: string }) => t.kind === "pin_check").stable_key;
  expect((await request.put("/api/workbench/review-decisions", { data: {
    stable_keys: [key], status: "accepted_risk", reason: "白色页面保存重开理由", expected_run_id: initial.review_decisions.run_id
  }})).ok()).toBeTruthy();
  await page.goto("/");
  await page.getByRole("button", { name: "导入", exact: true }).click();
  const panel = page.getByRole("region", { name: "本地保存的项目" });
  await panel.getByRole("button", { name: "保存当前项目", exact: true }).click();
  await expect(panel.getByRole("status")).toContainText("已保存");
  await expect(panel.getByRole("button", { name: /打开项目/ })).toHaveCount(1);
  await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator.net"));
  await page.getByLabel("选择 BOM CSV").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator_bom.csv"));
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(page.getByRole("region", { name: "Hardwise 三栏审查工作台" })).toBeVisible();
  await page.getByRole("button", { name: "导入", exact: true }).click();
  await panel.getByRole("button", { name: /打开项目/ }).click();
  await expect(page.getByRole("region", { name: "Hardwise 三栏审查工作台" })).toBeVisible();
  const reopened = await (await request.get("/api/workbench/state")).json();
  expect(reopened.summary.components).toBe(initial.summary.components);
  expect(reopened.review_decisions.project_id).toBe(initial.review_decisions.project_id);
  expect(reopened.review_tasks.find((t: { stable_key: string }) => t.stable_key === key).review_decision.reason).toBe("白色页面保存重开理由");
  await page.getByRole("button", { name: "导入", exact: true }).click();
  await page.setViewportSize({ width: 760, height: 960 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
  await page.screenshot({ path: info.outputPath("saved-projects-white.png"), animations: "disabled" });
});

test("saved project list and stale open errors stay visible and can be retried", async ({ page, request }) => {
  const catalog = await (await request.get("/api/workbench/projects")).json();
  if (!catalog.projects.length) {
    const state = await (await request.get("/api/workbench/state")).json();
    expect((await request.post(`/api/workbench/projects/save?expected_run_id=${state.review_decisions.run_id}`)).ok()).toBeTruthy();
  }
  await page.route("**/api/workbench/projects", route => route.fulfill({ status: 503, body: JSON.stringify({ detail: "synthetic catalog outage" }) }));
  await page.goto("/");
  await page.getByRole("button", { name: "导入", exact: true }).click();
  const panel = page.getByRole("region", { name: "本地保存的项目" });
  await expect(panel.getByRole("alert")).toContainText("synthetic catalog outage");
  await page.unroute("**/api/workbench/projects");
  await panel.getByRole("button", { name: "刷新已保存项目" }).click();
  await expect(panel.getByRole("alert")).toHaveCount(0);
  const old = await (await request.get("/api/workbench/state")).json();
  expect((await request.post("/api/workbench/rerun")).ok()).toBeTruthy();
  await panel.getByRole("button", { name: /打开项目/ }).first().click();
  await expect(panel.getByRole("alert")).toContainText("Active review changed");
  const active = await (await request.get("/api/workbench/state")).json();
  expect(active.review_decisions.project_id).toBe(old.review_decisions.project_id);
  expect(active.review_decisions.run_id).not.toBe(old.review_decisions.run_id);
});

test("white backup download and upload restore into a separate usable copy", async ({ page, request }, info) => {
  await page.goto("/");
  await page.getByRole("button", { name: "导入", exact: true }).click();
  const panel = page.getByRole("region", { name: "本地保存的项目" });
  await panel.getByRole("button", { name: "保存当前项目", exact: true }).click();
  await expect(panel.getByRole("status").first()).toContainText("已保存");
  const before = await (await request.get("/api/workbench/state")).json();
  const archive = page.getByRole("region", { name: "项目备份与恢复" });
  const pendingDownload = page.waitForEvent("download");
  await archive.getByRole("button", { name: "下载已保存项目备份" }).click();
  const download = await pendingDownload;
  expect(download.suggestedFilename()).toBe("hardwise-projects.zip");
  const backup = info.outputPath("browser-project-backup.zip");
  await download.saveAs(backup);
  expect(await download.failure()).toBeNull();
  await expect(archive.getByRole("status")).toContainText("备份已生成");
  await archive.getByLabel("选择项目备份 ZIP").setInputFiles({ name: "corrupt.zip", mimeType: "application/zip", buffer: Buffer.from("broken ZIP") });
  await archive.getByRole("button", { name: "恢复到新目录" }).click();
  await expect(archive.getByRole("alert")).toContainText("could not be restored");
  await archive.getByLabel("选择项目备份 ZIP").setInputFiles(backup);
  const pendingRestore = page.waitForResponse(r => r.url().includes("/api/workbench/projects/restore?") && r.request().method() === "POST");
  await archive.getByRole("button", { name: "恢复到新目录" }).click();
  const restoredResponse = await pendingRestore;
  expect(restoredResponse.ok()).toBeTruthy();
  const restored = await restoredResponse.json();
  await expect(archive.getByRole("status")).toContainText("当前评审未切换");
  await expect(archive.locator(".restore-receipt")).toContainText(restored.journal);
  const after = await (await request.get("/api/workbench/state")).json();
  expect(after.review_decisions).toEqual(before.review_decisions);
  expect(after.summary).toEqual(before.summary);
  const { spawnSync } = await import("node:child_process");
  const probe = spawnSync("uv", ["run", "hardwise", "serve-workbench", "--review-db", restored.journal, "--open-project", restored.saved_project_ids[0], "--dry-run", "--no-auto-datasheet-candidates"], { cwd: path.resolve("../.."), encoding: "utf8" });
  expect(probe.status, probe.stderr).toBe(0);
  expect(probe.stdout).toContain("mode=real");
  await archive.getByLabel("恢复命令终端类型").selectOption("powershell");
  await expect(archive.locator("pre").first()).toContainText("& 'uv'");
  await page.setViewportSize({ width: 760, height: 1100 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
  await archive.screenshot({ path: info.outputPath("backup-restore-white.png"), animations: "disabled" });
});
