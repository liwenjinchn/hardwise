// Legacy decisions retain their original meaning; never map them to risk or false positive.
export const reviewStatusLabel = (status: string): string => ({
  open: "待处理", accepted_risk: "接受风险", false_positive: "误报", resolved: "已解决",
  needs_review: "需复核", accepted: "旧版接受", waived: "旧版豁免", mixed: "混合处理"
}[status] ?? status);
