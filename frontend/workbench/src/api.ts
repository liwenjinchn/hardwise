import type {
  AIDisclosure,
  ChatMessage,
  ChatResponse,
  ComponentDetail,
  ImportResponse,
  ProjectReviewPrepPacket,
  ReviewPrepPacket,
  ReviewDecisionStatus,
  ReviewHistoryPage,
  WorkbenchOfflineSnapshot,
  WorkbenchState
} from "./types";
import type { RunProvenance, RunProvenanceResponse } from "./generated/workbench-contracts";

export type ProvenanceDownload = RunProvenanceResponse | {
  origin: "offline_export";
  exported_at: string;
  provenance: RunProvenance;
};

export async function fetchRunProvenance(
  projectId: string | null, runId: string | null
): Promise<ProvenanceDownload> {
  const snapshot = offlineSnapshot();
  if (snapshot) {
    if (runId) {
      const history = snapshot.review_history;
      const record = history?.run_provenance[runId];
      if (!record || history?.project_id !== projectId || record.project_id !== projectId || record.run_id !== runId) {
        throw new Error("离线快照未包含该历史运行清单，或项目不匹配。");
      }
      return record;
    }
    if (!snapshot.run_provenance) throw new Error("此旧离线快照未记录输入与版本清单，请重新导出。");
    return { origin: "offline_export", exported_at: snapshot.state.project.generated_at,
      provenance: snapshot.run_provenance };
  }
  if (!projectId || !runId) throw new Error("当前没有可下载清单的运行。");
  const query = new URLSearchParams({ expected_project_id: projectId });
  const result = await requestJson<RunProvenanceResponse>(
    `/api/workbench/review-runs/${encodeURIComponent(runId)}/provenance?${query}`
  );
  if (result.project_id !== projectId || result.run_id !== runId) {
    throw new Error("清单所属项目或运行已变化，请刷新后重试。");
  }
  return result;
}

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

export function updateReviewDecision(input: {
  expectedRunId?: string | null;
  stableKeys: string[];
  status: ReviewDecisionStatus;
  reason: string;
}): Promise<WorkbenchState> {
  if (offlineSnapshot()) {
    return Promise.reject(new Error("离线快照不能写入评审决策；请使用 serve-workbench。"));
  }
  return requestJson<WorkbenchState>("/api/workbench/review-decisions", {
    method: "PUT",
    body: JSON.stringify({
      stable_keys: input.stableKeys,
      status: input.status,
      reason: input.reason,
      expected_run_id: input.expectedRunId
    })
  });
}

export function fetchReviewHistory(projectId: string, offset = 0): Promise<ReviewHistoryPage> {
  const snapshot = offlineSnapshot();
  if (snapshot) {
    const history = snapshot.review_history;
    if (!history) return Promise.reject(new Error("离线快照未包含处理历史；请重新从本地服务下载离线评审包。"));
    if (history.project_id !== projectId) return Promise.reject(new Error("离线处理历史不属于当前项目。"));
    return Promise.resolve({ project_id: history.project_id, run_id: history.run_id,
      total: history.total, offset, limit: 20, events: history.events.slice(offset, offset + 20) });
  }
  const query = new URLSearchParams({ limit: "20", offset: String(offset), expected_project_id: projectId });
  return requestJson<ReviewHistoryPage>(`/api/workbench/review-decisions/history?${query}`);
}

export function rerunWorkbench(): Promise<WorkbenchState> {
  if (offlineSnapshot()) {
    return Promise.reject(new Error("离线快照不能重新运行检查；请使用 serve-workbench。"));
  }
  return requestJson<WorkbenchState>("/api/workbench/rerun", { method: "POST" });
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

export function isOfflineWorkbench(): boolean { return typeof window !== "undefined" && Boolean(offlineSnapshot()); }

export function fetchAIDisclosure(): Promise<AIDisclosure> {
  if (offlineSnapshot()) return Promise.resolve({
    version: "hardwise.ai_disclosure.v1", mode: "snapshot", available: true,
    context_id: "offline-snapshot", disclosure_id: null, destination: null, model: null,
    data_categories: [], notice: "离线审计快照，不调用云模型。"
  });
  return requestJson<AIDisclosure>("/api/workbench/ai-disclosure");
}

export function askCopilot(
  question: string,
  selectedRefdes: string | null,
  history: ChatMessage[],
  disclosureId?: string | null
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
      response_kind: "offline_notice",
      claim_verification: "unverified",
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
      history,
      disclosure_id: disclosureId
    })
  });
}

export function importWorkbench(files: {
  voltageFacts?: File | null;
  netlist: File;
  bom?: File | null;
  documentIndex?: File | null;
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
  if (files.documentIndex) body.append("document_index_csv", files.documentIndex);
  if (files.pinTable) body.append("pin_table_csv", files.pinTable);
  if (files.reviewPackage) body.append("review_package", files.reviewPackage);
  if (files.voltageFacts) body.append("voltage_facts_json", files.voltageFacts);
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


export async function downloadOfflineReport(projectId: string, runId: string): Promise<Blob> {
  if (offlineSnapshot()) throw new Error("当前已经是只读离线评审包；请保留原 HTML 文件。");
  const query = new URLSearchParams({ expected_project_id: projectId, expected_run_id: runId });
  const response = await fetch(`/api/workbench/offline-report?${query}`);
  if (!response.ok) throw new Error((await response.text()) || "离线评审包生成失败");
  return response.blob();
}
