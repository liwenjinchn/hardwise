import { expect, test, type Page } from "@playwright/test";
import path from "node:path";
import { realpath, writeFile } from "node:fs/promises";

test("review history pages retain original reasons and machine totals", async ({ page, request }) => {
  const original = await (await request.get("/api/workbench/state")).json();
  const key = original.review_tasks[0].stable_key;
  for (let i = 1; i <= 21; i++) {
    const response = await request.put("/api/workbench/review-decisions", { data: {
      stable_keys: [key], status: "accepted_risk", reason: `历史分页理由 ${i}`,
      expected_run_id: original.review_decisions.run_id
    }});
    expect(response.ok()).toBeTruthy();
  }
  const updated = await (await request.get("/api/workbench/state")).json();
  expect(updated.summary).toEqual(original.summary);
  await openReview(page);
  await page.getByRole("button", { name: "问题清单" }).click();
  await page.getByRole("button", { name: "查看处理历史" }).click();
  const history = page.getByRole("region", { name: "评审处理历史" });
  await expect(history.locator(".history-event")).toHaveCount(20);
  await expect(history.locator(".history-event").first()).toContainText("历史分页理由 21");
  await history.getByRole("button", { name: "下一页历史" }).click();
  await expect(history.locator(".history-event")).toHaveCount(1);
  await expect(history).toContainText("历史分页理由 1");
  await history.getByRole("button", { name: "上一页历史" }).click();
  await expect(history.locator(".history-event")).toHaveCount(20);
  await history.locator("summary").first().click();
  await expect(history).toContainText(key);
  await expect(history).toContainText(original.review_decisions.run_id);
  await page.setViewportSize({ width: 760, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
});

test("history read failure can be retried in the white findings page", async ({ page }) => {
  let failedOnce = false;
  await page.route("**/api/workbench/review-decisions/history?*", async route => {
    if (!failedOnce) {
      failedOnce = true;
      await route.fulfill({ status: 503, body: "synthetic history read outage" });
    } else await route.continue();
  });
  await openReview(page);
  await page.getByRole("button", { name: "问题清单" }).click();
  await page.getByRole("button", { name: "查看处理历史" }).click();
  const history = page.getByRole("region", { name: "评审处理历史" });
  await expect(history.getByRole("alert")).toContainText("synthetic history read outage");
  await history.getByRole("button", { name: "刷新历史" }).click();
  await expect(history.getByRole("alert")).toHaveCount(0);
  await expect(history.locator(".history-events")).toBeVisible();
});

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

test("unknown check shows its result, severity and evidence kind independently", async ({ page }) => {
  await openReview(page);
  await pickComponent(page, "R1");
  const check = page.locator(".check-card").filter({ hasText: "电阻功耗未知" });
  await expect(check).toContainText("结果：待补资料 / 未评估");
  await expect(check).toContainText("严重度：信息");
  await expect(check).toContainText("规则推导");
  await expect(check).toHaveClass(/manual/);
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
  await expect(page.locator(".msg.ai .cop-disclaimer").last()).toContainText("参数和推断未经逐项核验");
});

test("prep packet preview opens for Q12", async ({ page }) => {
  await openReview(page);
  await pickComponent(page, "Q12");
  await page.locator(".prep-actions").getByRole("button", { name: "预览" }).click();
  const preview = page.locator(".prep-preview");
  await expect(preview).toBeVisible();
  await expect(preview).toContainText("Q12");
});

test("review decision survives reload and deterministic rerun, then reopens", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "问题清单" }).click();
  const firstGroup = page.locator(".finding-row").first();
  await expect(firstGroup).toBeVisible();
  await firstGroup.locator("input").fill("Public regression fixture intentionally retains this fault.");
  await firstGroup.getByRole("button", { name: "接受风险" }).click();
  await expect(firstGroup).toContainText("评审 接受风险");

  await page.reload();
  await page.getByRole("button", { name: "问题清单" }).click();
  await expect(page.locator(".finding-row").first()).toContainText("评审 接受风险");
  await page.getByRole("button", { name: "重新运行确定性检查" }).click();
  await expect(page.locator(".finding-row").first()).toContainText("评审 接受风险");

  await page.locator(".finding-row").first().getByRole("button", { name: "重新打开" }).click();
  await expect(page.locator(".finding-row").first()).toContainText("评审 待处理");
});

test("export JSON preview is a compact handoff summary", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "导出" }).click();
  await page.getByRole("button", { name: "生成预览" }).click();
  const preview = page.locator(".export-preview");
  await expect(preview).toContainText("grouped_review_workload");
  await expect(preview).toContainText("预览仅显示交接摘要");
  const text = await preview.textContent();
  expect(text?.length ?? 0).toBeLessThan(10_000);
});

test("import page can reload the built-in demo files", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "导入" }).click();
  await expect(page.locator(".upload-slot").first()).toContainText("本次必选");
  await expect(page.getByLabel("选择 BOM CSV").locator("..")).toContainText("本次可选");
  await expect(page.locator(".evidence-lane-card")).toHaveCount(6);
  await page
    .locator('input[accept=".net,.dat,.txt,.pst"]')
    .setInputFiles(path.resolve("../../tests/fixtures/allegro/mixed_controller_power_stage.net"));
  await expect(page.locator(".upload-slot").first()).toContainText("本次已选择");
  await expect(page.locator(".upload-slot").first()).toContainText(
    "本次文件：mixed_controller_power_stage.net"
  );
  await page
    .getByLabel("选择 BOM CSV")
    .setInputFiles(
      path.resolve("../../tests/fixtures/allegro/mixed_controller_power_stage_bom.csv")
    );
  await page
    .getByLabel("选择 public document index CSV")
    .setInputFiles(path.resolve("../../tests/fixtures/allegro/document_match/docs.csv"));
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(page.locator(".parse-step").first()).toBeVisible();
  await expect(page.locator(".evidence-lane-card")).toHaveCount(6);
  await expect(page.locator(".evidence-lane-card").filter({ hasText: "Public document index" }))
    .toContainText("doc:docs.csv#summary");
  await expect(page.locator(".queue-list .queue-row").first()).toBeVisible({ timeout: 30_000 });
});

test("confirmed DC input produces a bipolar stress error and survives rerun", async ({ page }) => {
  await openReview(page);
  await page.getByRole("button", { name: "导入" }).click();
  const fixture = path.resolve("../../tests/fixtures/allegro/bipolar_dc");
  await page.getByLabel("选择 netlist / PST").setInputFiles(path.join(fixture, "design.net"));
  await page.getByLabel("选择 BOM CSV").setInputFiles(path.join(fixture, "bom.csv"));
  await page.getByLabel("选择 已确认电压事实").setInputFiles(path.join(fixture, "voltage_facts.json"));
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(queueRow(page, "C1")).toBeVisible({ timeout: 30_000 });
  await expect(queueRow(page, "C1")).toHaveClass(/error/);
  await expect(queueRow(page, "C1")).toContainText("24 V");
  await page.getByRole("button", { name: "问题清单" }).click();
  await page.getByRole("button", { name: "重新运行确定性检查" }).click();
  await page.getByRole("button", { name: "导入" }).click();
  await expect(page.getByLabel("当前电压确认记录")).toContainText("synthetic fixture author");
  await expect(page.getByLabel("当前电压确认记录")).toContainText("P12");
  await expect(page.getByLabel("当前电压确认记录")).toContainText("N12");
});

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 760, height: 900 }
]) {
  test(`no horizontal overflow at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openReview(page);
    for (const view of ["审查", "导入", "问题清单", "导出"]) {
      await page.getByRole("button", { name: view }).click();
      const overflow = await page.evaluate(() => {
        const root = document.documentElement;
        return {
          scrollWidth: Math.max(root.scrollWidth, document.body.scrollWidth),
          clientWidth: root.clientWidth
        };
      });
      expect(overflow.scrollWidth, `${view} view overflow`).toBeLessThanOrEqual(
        overflow.clientWidth
      );
    }
  });
}

test("white import keeps conflicting BOM rating premises unknown and accepts an explicit correction", async ({ page, request }, testInfo) => {
  await openReview(page);
  await page.getByRole("button", { name: "导入", exact: true }).click();
  await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator.net"));
  const bom = (rating: string) => Buffer.from(
    "Reference,Quantity,Value,Voltage Rating,Manufacturer,MPN\n" +
    "U1,1,L7805,,ST,L7805\nC1,1,100nF 25V," + rating + ",Fixture,CAP-100N\nC2,1,100nF,,Fixture,CAP-OTHER\n"
  );
  await page.getByLabel("选择 BOM CSV").setInputFiles({ name: "ratings.csv", mimeType: "text/csv", buffer: bom("16V") });
  const voltageFacts = Buffer.from(JSON.stringify({
    schema_version: "hardwise.voltage_facts.v1", active_mode: "dc",
    facts: [{ net: "+12V", minimum: 20, maximum: 20 }, { net: "GND", minimum: 0, maximum: 0 }].map(fact => ({
      ...fact, reference_net: "GND", confirmed: true, confirmed_by: "public synthetic author", source: "public rating conflict fixture"
    }))
  }));
  await page.getByLabel("选择 已确认电压事实").setInputFiles({ name: "facts.json", mimeType: "application/json", buffer: voltageFacts });
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(queueRow(page, "C1")).toBeVisible();
  await page.getByRole("button", { name: "问题清单" }).click();
  await expect(page.locator(".findings-list")).toContainText("Value=25V");
  await expect(page.locator(".findings-list")).toContainText("Voltage Rating=16V");
  const exported = await (await request.get("/api/workbench/export?format=json")).json();
  const task = exported.review_tasks.find((item: { refdes: string; check: string }) => item.refdes === "C1" && item.check === "capacitor_voltage_margin");
  expect(task.assessment.result).toBe("UNKNOWN");
  expect(task.assessment.needs_review).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("bom-rating-conflict-white.png"), animations: "disabled" });
  await page.getByRole("button", { name: "导入", exact: true }).click();
  await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator.net"));
  await page.getByLabel("选择 BOM CSV").setInputFiles({ name: "ratings.csv", mimeType: "text/csv", buffer: bom("25000mV") });
  await page.getByLabel("选择 已确认电压事实").setInputFiles({ name: "facts.json", mimeType: "application/json", buffer: voltageFacts });
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(queueRow(page, "C1")).toBeVisible();
  const state = await (await request.get("/api/workbench/state")).json();
  expect(state.queue.find((row: { refdes: string }) => row.refdes === "C1").deterministic_status).toBe("PASS");
});

test("white import exposes every competing identity column and clears the block after correction", async ({ page, request }, testInfo) => {
  const bom = (conflicting: boolean) => Buffer.from(
    "Reference,Quantity,Value,MPN,MPN,Manufacturer,Mfr,Package,Footprint\n" +
    (conflicting ? "U1,1,L7805,WRONG_PUBLIC_FIXTURE,L7805,VendorA,VendorB,TO220,SOT23\n"
      : "U1,1,L7805,L7805,L7805,ST,ST,TO220,TO220\n") +
    "C1,1,100nF,,,,,,\nC2,1,100nF,,,,,,\n"
  );
  const load = async (conflicting: boolean) => {
    await page.getByRole("button", { name: "导入", exact: true }).click();
    await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator.net"));
    await page.getByLabel("选择 BOM CSV").setInputFiles({ name: "identity-columns.csv", mimeType: "text/csv", buffer: bom(conflicting) });
    await page.getByRole("button", { name: "导入并解析" }).click();
    await expect(queueRow(page, "U1")).toBeVisible();
  };
  await openReview(page);
  await load(true);
  await page.getByRole("button", { name: "问题清单" }).click();
  for (const value of ["WRONG_PUBLIC_FIXTURE", "VendorA", "VendorB", "TO220", "SOT23", "column4", "column5", "#line2"]) {
    await expect(page.locator(".findings-list")).toContainText(value);
  }
  const state = await (await request.get("/api/workbench/export?format=json")).json();
  const blocked = state.review_tasks.find((task: { refdes: string; check: string }) => task.refdes === "U1" && task.check === "bom_identity_conflict");
  expect(blocked.assessment.result).toBe("UNKNOWN");
  expect(blocked.assessment.needs_review).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("identity-columns-white.png"), animations: "disabled" });
  await page.setViewportSize({ width: 760, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("identity-columns-narrow.png"), animations: "disabled" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await load(false);
  const repaired = await (await request.get("/api/workbench/state")).json();
  expect(repaired.review_tasks.some((task: { check: string }) => task.check === "bom_identity_conflict")).toBe(false);
});

test("quantity column warnings preserve an independently passing electrical check", async ({ page, request }, testInfo) => {
  const bom = (qty: string) => Buffer.from(
    "Reference,Quantity,Qty,Value,Manufacturer,MPN\n" +
    `C1,1,${qty},100nF 25V,Fixture,CAP-100N\n` +
    "U1,1,1,L7805,ST,L7805\nC2,1,1,100nF,Fixture,CAP-100N\n"
  );
  const facts = Buffer.from(JSON.stringify({ schema_version: "hardwise.voltage_facts.v1", active_mode: "dc",
    facts: [{ net: "+12V", minimum: 11, maximum: 13 }, { net: "GND", minimum: 0, maximum: 0 }].map(item => ({
      ...item, reference_net: "GND", confirmed: true, confirmed_by: "public synthetic author", source: "public quantity example; not measured"
    })) }));
  const load = async (qty: string) => {
    await page.getByRole("button", { name: "导入", exact: true }).click();
    await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator.net"));
    await page.getByLabel("选择 BOM CSV").setInputFiles({ name: "quantity-columns.csv", mimeType: "text/csv", buffer: bom(qty) });
    await page.getByLabel("选择 已确认电压事实").setInputFiles({ name: "facts.json", mimeType: "application/json", buffer: facts });
    await page.getByRole("button", { name: "导入并解析" }).click();
    await expect(queueRow(page, "C1")).toBeVisible();
  };
  await openReview(page);
  await load("1");
  const before = await (await request.get("/api/workbench/state")).json();
  expect(before.queue.find((row: { refdes: string }) => row.refdes === "C1").deterministic_status).toBe("PASS");
  await load("99");
  await queueRow(page, "C1").click();
  await expect(page.getByRole("region", { name: "BOM 数量列冲突" })).toContainText("Qty=99");
  const current = await (await request.get("/api/workbench/state")).json();
  expect(current.summary).toEqual(before.summary);
  expect(current.evidence_package.bom_quantity_conflicts).toHaveLength(1);
  expect(current.evidence_package.lanes.find((lane: { id: string }) => lane.id === "bom").status_label).toBe("quantity gaps");
  await page.screenshot({ path: testInfo.outputPath("quantity-detail-white.png"), animations: "disabled" });
  await page.getByRole("button", { name: "导出", exact: true }).click();
  const warning = page.getByRole("region", { name: "BOM 数量列冲突" });
  await expect(warning).toContainText("Quantity=1");
  await expect(warning).toContainText("Qty=99");
  await warning.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("quantity-columns-white.png"), animations: "disabled" });
  await page.setViewportSize({ width: 760, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await warning.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("quantity-columns-narrow.png"), animations: "disabled" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await load("1");
  const repaired = await (await request.get("/api/workbench/state")).json();
  expect(repaired.evidence_package.bom_quantity_conflicts).toEqual([]);
});

test("control review survives distant BOM changes and reopens for a direct branch", async ({ page, request }, testInfo) => {
  const original = "Reference,Quantity,Value,Manufacturer,MPN\n" +
    ["U1", "U2", "U3"].map(ref => `${ref},1,74LV165PW,Nexperia,74LV165PW`).join("\n") + "\n" +
    ["RCLK1", "RCLK2", "RCLK3", "RCE1", "RCE2", "RCE3", "RCHAIN1", "RCHAIN2"].map(ref => `${ref},1,33R,Fixture,GW_RESISTOR`).join("\n") + "\n";
  await openReview(page);
  await page.getByRole("button", { name: "导入", exact: true }).click();
  await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/shift_register_chain.net"));
  await page.getByLabel("选择 BOM CSV").setInputFiles({ name: "control-neighborhood.csv", mimeType: "text/csv", buffer: Buffer.from(original) });
  await page.getByRole("button", { name: "导入并解析" }).click();
  await expect(queueRow(page, "U1")).toBeVisible();
  const state = async () => (await (await request.get("/api/workbench/state")).json());
  const initial = await state();
  const task = initial.review_tasks.find((item: { refdes: string; check: string }) => item.refdes === "U1" && item.check === "shift_register_clock_enable");
  const group = initial.review_groups.find((item: { stable_keys: string[] }) => item.stable_keys.includes(task.stable_key));
  await page.getByRole("button", { name: "问题清单" }).click();
  const row = page.locator(".finding-row").filter({ hasText: `${group.id} ·` });
  await row.getByLabel(`${group.id} 评审理由`).fill("公开合成控制连接复核理由");
  await row.getByRole("button", { name: "接受风险", exact: true }).click();
  await expect(row).toContainText("评审 接受风险");
  const reviewed = await state();
  const ownedBom = await realpath(reviewed.project.bom_source);
  expect(path.basename(ownedBom)).toBe("control-neighborhood.csv");
  expect(path.basename(path.dirname(ownedBom))).toMatch(/^hardwise-workbench-import-/);
  const rerun = async (body: string, previous: string) => {
    await writeFile(ownedBom, body);
    await page.getByRole("button", { name: "重新运行确定性检查" }).click();
    await expect.poll(async () => (await state()).review_decisions.run_id).not.toBe(previous);
    return state();
  };
  const lines = original.trimEnd().split("\n");
  const administrative = [lines[0], ...lines.slice(1).reverse()].join("\n") + "\n";
  const quantities = administrative.replace("U1,1,", "U1,7,").replace("RCE1,1,", "RCE1,7,");
  expect(quantities).not.toBe(administrative);
  const metadataOnly = await rerun(quantities, reviewed.review_decisions.run_id);
  const preserved = metadataOnly.review_tasks.find((item: { stable_key: string }) => item.stable_key === task.stable_key);
  expect(preserved.assessment).toEqual(task.assessment);
  expect(preserved.review_decision.status).toBe("accepted_risk");
  expect(metadataOnly.review_decisions.history_count).toBe(reviewed.review_decisions.history_count);
  await expect(row).toContainText("评审 接受风险");
  const distant = quantities.replace("RCLK3,1,33R,", "RCLK3,1,47R,");
  expect(distant).not.toBe(quantities);
  const kept = await rerun(distant, metadataOnly.review_decisions.run_id);
  expect(kept.review_tasks.find((item: { stable_key: string }) => item.stable_key === task.stable_key).review_decision.status).toBe("accepted_risk");
  expect(kept.review_decisions.history_count).toBe(reviewed.review_decisions.history_count);
  await expect(row).toContainText("评审 接受风险");
  const branch = distant.replace("RCE1,7,33R,", "RCE1,7,22K,");
  const changed = await rerun(branch, kept.review_decisions.run_id);
  const current = changed.review_tasks.find((item: { stable_key: string }) => item.stable_key === task.stable_key);
  expect(current.assessment).toEqual(task.assessment);
  expect(current.review_decision.status).toBe("needs_review");
  expect(current.review_decision.reason).toBe("公开合成控制连接复核理由");
  await expect(row).toContainText("评审 需复核");
  await row.getByText("已有处理理由", { exact: true }).click();
  await row.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("control-dependency-recheck-white.png"), animations: "disabled" });
});


test("competing reference columns quarantine every candidate and clear after correction", async ({ page, request }, testInfo) => {
  const bom = (conflict: boolean) => Buffer.from(
    "Reference,Refdes,Quantity,Value\n" +
    `U1,${conflict ? "C1" : "U1"},1,L7805\n` +
    "C1,C1,1,100nF 25V\nC2,C2,1,100nF 25V\n"
  );
  const load = async (conflict: boolean) => {
    await page.getByRole("button", { name: "导入", exact: true }).click();
    await page.getByLabel("选择 netlist / PST").setInputFiles(path.resolve("../../tests/fixtures/allegro/l78_regulator.net"));
    await page.getByLabel("选择 BOM CSV").setInputFiles({ name: "references.csv", mimeType: "text/csv", buffer: bom(conflict) });
    await page.getByRole("button", { name: "导入并解析" }).click();
    await expect(queueRow(page, "U1")).toBeVisible();
    await expect(queueRow(page, "C1")).toBeVisible();
  };
  await openReview(page);
  await load(true);
  const state = await (await request.get("/api/workbench/state")).json();
  const blocked = state.review_tasks.filter((t: { check: string }) => t.check === "bom_identity_conflict");
  expect(blocked.map((t: { refdes: string }) => t.refdes).sort()).toEqual(["C1", "U1"]);
  expect(blocked.every((t: { assessment: { result: string; rule_version: string } }) => t.assessment.result === "UNKNOWN" && t.assessment.rule_version === "4")).toBe(true);
  await page.getByRole("button", { name: "问题清单" }).click();
  await expect(page.locator(".findings-list")).toContainText("column1 [Reference=U1]");
  await expect(page.locator(".findings-list")).toContainText("column2 [Refdes=C1]");
  await page.screenshot({ path: testInfo.outputPath("reference-quarantine-white.png"), animations: "disabled" });
  await page.setViewportSize({ width: 760, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("reference-quarantine-narrow.png"), animations: "disabled" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await load(false);
  const fixed = await (await request.get("/api/workbench/state")).json();
  expect(fixed.review_tasks.some((t: { check: string }) => t.check === "bom_identity_conflict")).toBe(false);
});
