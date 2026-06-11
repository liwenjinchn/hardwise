export type ViewId = "import" | "parse" | "review" | "copilot" | "findings" | "export";

export const NAV_ITEMS: Array<{ id: ViewId; label: string }> = [
  { id: "import", label: "导入" },
  { id: "parse", label: "解析" },
  { id: "review", label: "审查" },
  { id: "copilot", label: "AI 助手" },
  { id: "findings", label: "问题清单" },
  { id: "export", label: "导出" }
];
