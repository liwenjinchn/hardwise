import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

test("current and historical downloads retain their actual run identities", async ({ page, request }, testInfo) => {
  const before = await (await request.get("/api/workbench/state")).json();
  const old = before.review_decisions;
  const decision = await request.put("/api/workbench/review-decisions", { data: {
    stable_keys: [before.review_tasks[0].stable_key], status: "waived",
    reason: "provenance synthetic reason", expected_run_id: old.run_id
  } });
  expect(decision.ok()).toBeTruthy();
  const rerun = await request.post("/api/workbench/rerun");
  expect(rerun.ok()).toBeTruthy();
  const current = (await rerun.json()).review_decisions;
  await page.goto("/");
  await page.getByRole("button", { name: "问题清单" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载本次输入与版本清单" }).click();
  const download = await downloadPromise;
  const payload = JSON.parse(await readFile((await download.path())!, "utf8"));
  expect(payload.run_id).toBe(current.run_id);
  expect(payload.project_id).toBe(current.project_id);
  expect(payload.status).toBe("recorded");
  expect(payload.provenance.inputs.files.length).toBeGreaterThan(0);
  expect(payload.provenance.raw_inputs_archived).toBe(false);
  expect(payload.provenance.emitted_records).toBeGreaterThan(0);
  await page.getByRole("button", { name: "查看处理历史" }).click();
  const event = page.locator(".history-event").filter({ hasText: "provenance synthetic reason" }).first();
  await event.locator("summary").click();
  const historicalPromise = page.waitForEvent("download");
  await event.getByRole("button", { name: "下载该次输入与版本清单" }).click();
  const historical = await historicalPromise;
  expect(JSON.parse(await readFile((await historical.path())!, "utf8")).run_id).toBe(old.run_id);
  await page.screenshot({ path: testInfo.outputPath("provenance-white.png") });
  // Restore a fresh public demo namespace for other shared-service tests.
  const restored = await request.post("/api/workbench/import", { multipart: {
    netlist: { name: "mixed_controller_power_stage.net", mimeType: "text/plain",
      buffer: await readFile(path.resolve("../../tests/fixtures/allegro/mixed_controller_power_stage.net")) },
    bom: { name: "mixed_controller_power_stage_bom.csv", mimeType: "text/csv",
      buffer: await readFile(path.resolve("../../tests/fixtures/allegro/mixed_controller_power_stage_bom.csv")) }
  } });
  expect(restored.ok()).toBeTruthy();
});

test("download failures retry and legacy runs explicitly download a missing-record notice", async ({ page, request }) => {
  const ids = (await (await request.get("/api/workbench/state")).json()).review_decisions;
  let fail = true;
  await page.route("**/api/workbench/review-runs/**/provenance?*", async (route) => {
    if (fail) { await route.fulfill({ status: 503, body: "synthetic manifest read failure" }); return; }
    await route.fulfill({ json: { project_id: ids.project_id, run_id: ids.run_id,
      created_at: null, status: "not_recorded", reason: "Legacy run did not record provenance.", provenance: null } });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "问题清单" }).click();
  await page.getByRole("button", { name: "下载本次输入与版本清单" }).click();
  await expect(page.getByRole("alert")).toContainText("synthetic manifest read failure");
  fail = false;
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载本次输入与版本清单" }).click();
  const file = await downloaded;
  const notice = JSON.parse(await readFile((await file.path())!, "utf8"));
  expect(notice.status).toBe("not_recorded");
  expect(notice.provenance).toBeNull();
  await expect(page.getByRole("status").filter({ hasText: "已下载缺失说明" })).toBeVisible();
});

test("real single-file export downloads embedded evidence with zero API requests and rejects old missing payloads", async ({ page }, testInfo) => {
  const directory = await mkdtemp(path.join(tmpdir(), "hardwise-offline-provenance-"));
  try {
    const output = path.join(directory, "public.html");
    execFileSync("uv", ["run", "hardwise", "design-validator-ui",
      "tests/fixtures/allegro/l78_regulator.net", "tests/fixtures/allegro/l78_regulator_bom.csv",
      "--profiles", "data/datasheet_profiles", "--ai-snapshot", "--output", output],
      { cwd: path.resolve("../.."), env: process.env });
    let html = await readFile(output, "utf8");
    const calls: string[] = [];
    await page.route("**/api/**", async (route) => { calls.push(route.request().url()); await route.abort(); });
    await page.route("**/offline-provenance.html", async (route) => {
      await route.fulfill({ contentType: "text/html", body: html });
    });
    await page.goto("/offline-provenance.html");
    await page.getByRole("button", { name: "导出", exact: true }).click();
    const promise = page.waitForEvent("download");
    await page.getByRole("button", { name: "下载本次输入与版本清单" }).click();
    const file = await promise;
    const payload = JSON.parse(await readFile((await file.path())!, "utf8"));
    expect(payload.origin).toBe("offline_export");
    expect(payload.run_id).toBeUndefined();
    expect(payload.provenance.inputs.files.some((f: { roles: string[] }) => f.roles.includes("netlist"))).toBe(true);
    expect(payload.provenance.profiles.length).toBeGreaterThan(0);
    const contentBox = await page.locator(".project-prep-card").first().locator("div").first().boundingBox();
    expect(contentBox!.width).toBeGreaterThan(160);
    await page.getByRole("heading", { name: "导出当前审查状态" }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("offline-provenance-white.png") });
    expect(calls).toEqual([]);
    // Simulate an older artifact by removing only its additive manifest field.
    html = html.replace('"run_provenance":', '"old_unavailable_provenance":');
    await page.reload();
    await page.getByRole("button", { name: "导出", exact: true }).click();
    await page.getByRole("button", { name: "下载本次输入与版本清单" }).click();
    await expect(page.getByRole("alert")).toContainText("旧离线快照未记录");
    expect(calls).toEqual([]);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
