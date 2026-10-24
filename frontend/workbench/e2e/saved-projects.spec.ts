import { expect, test } from "@playwright/test";
import path from "node:path";

test.use({ baseURL: "http://127.0.0.1:4400" });

test("white save and open restore the saved project and reason after another import", async ({ page, request }, info) => {
  const initial = await (await request.get("/api/workbench/state")).json();
  const key = initial.review_tasks.find((t: { kind: string }) => t.kind === "pin_check").stable_key;
  expect((await request.put("/api/workbench/review-decisions", { data: {
    stable_keys: [key], status: "waived", reason: "白色页面保存重开理由", expected_run_id: initial.review_decisions.run_id
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
