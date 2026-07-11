import type {
  ChatMessage,
  ChatResponse,
  ComponentDetail,
  ImportResponse,
  ProjectReviewPrepPacket,
  ReviewPrepPacket,
  WorkbenchOfflineSnapshot,
  WorkbenchState
} from "./types";

function offlineSnapshot(): WorkbenchOfflineSnapshot | null {
  return window.__HARDWISE_OFFLINE_SNAPSHOT__ ?? null;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(url, {
    ...init,
    headers: isFormData
      ? init?.headers
      : {
          "Content-Type": "application/json",
          ...(init?.headers ?? {})
        }
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function fetchWorkbenchState(): Promise<WorkbenchState> {
  const snapshot = offlineSnapshot();
  if (snapshot) return Promise.resolve(snapshot.state);
  return requestJson<WorkbenchState>("/api/workbench/state");
}

export function fetchComponentDetail(refdes: string): Promise<ComponentDetail> {
  const snapshot = offlineSnapshot();
  if (snapshot) {
    const detail = snapshot.components[refdes.toUpperCase()] ?? snapshot.components[refdes];
    if (!detail) return Promise.reject(new Error(`offline snapshot missing component ${refdes}`));
    return Promise.resolve(detail);
  }
  return requestJson<ComponentDetail>(`/api/workbench/components/${encodeURIComponent(refdes)}`);
}

export function fetchPrepPacket(refdes: string): Promise<ReviewPrepPacket> {
  return requestJson<ReviewPrepPacket>(
    `/api/workbench/components/${encodeURIComponent(refdes)}/prep-packet?format=json`
  );
}

export async function fetchPrepPacketMarkdown(refdes: string): Promise<string> {
  const snapshot = offlineSnapshot();
  if (snapshot) {
    const markdown =
      snapshot.component_prep_markdown[refdes.toUpperCase()] ??
      snapshot.component_prep_markdown[refdes];
    if (!markdown) throw new Error(`offline snapshot missing prep packet ${refdes}`);
    return markdown;
  }
  const response = await fetch(
    `/api/workbench/components/${encodeURIComponent(refdes)}/prep-packet?format=markdown`
  );
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return response.text();
}

export function fetchProjectPrepPacket(): Promise<ProjectReviewPrepPacket> {
  return requestJson<ProjectReviewPrepPacket>("/api/workbench/prep-packet?format=json");
}

export async function fetchProjectPrepPacketMarkdown(): Promise<string> {
  const snapshot = offlineSnapshot();
  if (snapshot) return snapshot.project_prep_markdown;
  const response = await fetch("/api/workbench/prep-packet?format=markdown");
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return response.text();
}

export function askCopilot(
  question: string,
  selectedRefdes: string | null,
  history: ChatMessage[]
): Promise<ChatResponse> {
  const snapshot = offlineSnapshot();
  if (snapshot) {
    const clean = question.trim();
    const exact = snapshot.chat_responses[clean];
    if (exact) return Promise.resolve(exact);
    if (clean.includes("U999")) {
      const u999 = snapshot.chat_responses["板上有没有 U999?"];
      if (u999) return Promise.resolve(u999);
    }
    const fallback = snapshot.chat_responses.__fallback__;
    if (fallback) return Promise.resolve(fallback);
    return Promise.resolve({
      answer: "这个离线演示只包含已审计的快照问题。请切换到 live workbench 提问更多问题。",
      mode: "snapshot",
      selected_refdes: selectedRefdes,
      trace: [],
      wrapped_count: 0,
      suggestions: [],
      datasheet_search_enabled: false,
      unsupported_evidence_tokens: []
    });
  }
  return requestJson<ChatResponse>("/api/workbench/chat", {
    method: "POST",
    body: JSON.stringify({
      question,
      selected_refdes: selectedRefdes,
      history
    })
  });
}

export function importWorkbench(files: {
  netlist: File;
  bom?: File | null;
  pinTable?: File | null;
  reviewPackage?: File | null;
  riskHints?: File | null;
}): Promise<ImportResponse> {
  if (offlineSnapshot()) {
    return Promise.reject(new Error("离线快照不能导入新文件；请使用 serve-workbench。"));
  }
  const body = new FormData();
  body.append("netlist", files.netlist);
  if (files.bom) body.append("bom", files.bom);
  if (files.pinTable) body.append("pin_table_csv", files.pinTable);
  if (files.reviewPackage) body.append("review_package", files.reviewPackage);
  if (files.riskHints) body.append("risk_hints_json", files.riskHints);
  return requestJson<ImportResponse>("/api/workbench/import", {
    method: "POST",
    body
  });
}

export async function exportWorkbench(format: "json" | "csv" | "annotations"): Promise<string> {
  const snapshot = offlineSnapshot();
  if (snapshot) return snapshot.exports[format];
  const response = await fetch(`/api/workbench/export?format=${encodeURIComponent(format)}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return response.text();
}
