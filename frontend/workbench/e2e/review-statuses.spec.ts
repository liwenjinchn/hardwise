import { expect, test } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:4400" });

test("legacy judgments keep their labels while new risk and false-positive decisions persist", async ({ page, request }, info) => {
  const before = await (await request.get("/api/workbench/state")).json();
  const group = before.review_groups[0];
  const reason = "公开合成判断：保留原始电气检查，不作为签核";
  // Model a response from a legacy persisted journal; new mutations reject these values.
  const showLegacy = async (status: string) => {
    await page.route("**/api/workbench/state", async route => {
      const response = await route.fetch();
      const state = await response.json();
      for (const task of state.review_tasks) if (group.stable_keys.includes(task.stable_key)) {
        task.review_decision = { stable_key: task.stable_key, status, reason: "旧版原始理由",
          updated_at: "2026-10-24T00:00:00Z", previous_status: null, fingerprint: "old", current_fingerprint: "old" };
      }
      await route.fulfill({ response, json: state });
    }, { times: 1 });
    await page.goto("/");
    await page.getByRole("button", { name: "问题清单", exact: false }).click();
  };
  const row = page.locator(".finding-row").filter({ hasText: `${group.id} ·` });
  await showLegacy("accepted");
  await expect(row).toContainText("评审 旧版接受");
  await showLegacy("waived");
  await expect(row).toContainText("评审 旧版豁免");
  await row.getByLabel(`${group.id} 评审理由`).fill(reason);
  await row.getByRole("button", { name: "接受风险", exact: true }).click();
  await expect(row).toContainText("评审 接受风险");
  await page.reload();
  await page.getByRole("button", { name: "问题清单", exact: false }).click();
  await expect(row).toContainText("评审 接受风险");
  await row.getByLabel(`${group.id} 评审理由`).fill(reason);
  await row.getByRole("button", { name: "误报", exact: true }).click();
  await expect(row).toContainText("评审 误报");
  const after = await (await request.get("/api/workbench/state")).json();
  expect(after.summary).toEqual(before.summary);
  for (const key of group.stable_keys) {
    const old = before.review_tasks.find((t: { stable_key: string }) => t.stable_key === key);
    const current = after.review_tasks.find((t: { stable_key: string }) => t.stable_key === key);
    expect(current.assessment).toEqual(old.assessment);
    expect(current.review_decision.status).toBe("false_positive");
    expect(current.review_decision.reason).toBe(reason);
  }
  await row.getByText("已有处理理由", { exact: true }).click();
  await page.getByRole("button", { name: "查看处理历史", exact: true }).click();
  const history = page.getByRole("region", { name: "评审处理历史" });
  await expect(history).toContainText("接受风险");
  await expect(history).toContainText("误报");
  await page.screenshot({ path: info.outputPath("white-review-statuses.png"), fullPage: true });
});
