import type { ProvenanceDownload } from "./api";
export function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
export function display(value: unknown): string {
  if (value === undefined || value === null) return "未记录";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}
const reasons: Record<string, string> = {
  withheld: "当前声明不允许分享", undeclared: "没有分享声明", stale: "来源已变化，声明失效",
  not_currently_allowed: "当前来源未获有效分享许可", invalid_source: "来源记录不完整或格式不符"
};
export function excerptRows(payload: ProvenanceDownload) {
  return (payload.provenance?.profiles ?? []).flatMap(profile => {
    const review = record(profile.values.field_review);
    const fields = Array.isArray(review.fields) ? review.fields : [];
    return fields.map((raw, index) => {
      const field = record(raw), source = record(field.source), sharing = record(source.sharing), delivery = record(source.excerpt_delivery);
      const allowed = !source.excerpt_delivery && sharing.decision === "allow" && sharing.actor === "human" && typeof source.excerpt === "string";
      return { key: `${profile.sha256}:${index}`, part: profile.part_number,
        refs: Object.entries(payload.provenance!.profile_bindings).filter(([, sha]) => sha === profile.sha256).map(([ref]) => ref).join(", "),
        field, source, sharing, identity: record(review.identity),
        excerpt: allowed ? source.excerpt as string : null,
        omission: reasons[String(delivery.reason)] ?? "未包含有效分享声明的原文；请向资料提供者核对",
        originalHash: profile.sha256, sharedHash: profile.share_projection?.shared_values_sha256,
      };
    });
  });
}
