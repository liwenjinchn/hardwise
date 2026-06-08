import type { ChatMessage, ChatResponse, ComponentDetail, ImportResponse, WorkbenchState } from "./types";

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
  return requestJson<WorkbenchState>("/api/workbench/state");
}

export function fetchComponentDetail(refdes: string): Promise<ComponentDetail> {
  return requestJson<ComponentDetail>(`/api/workbench/components/${encodeURIComponent(refdes)}`);
}

export function askCopilot(
  question: string,
  selectedRefdes: string | null,
  history: ChatMessage[]
): Promise<ChatResponse> {
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
  riskHints?: File | null;
}): Promise<ImportResponse> {
  const body = new FormData();
  body.append("netlist", files.netlist);
  if (files.bom) body.append("bom", files.bom);
  if (files.riskHints) body.append("risk_hints_json", files.riskHints);
  return requestJson<ImportResponse>("/api/workbench/import", {
    method: "POST",
    body
  });
}

export async function exportWorkbench(format: "json" | "csv" | "annotations"): Promise<string> {
  const response = await fetch(`/api/workbench/export?format=${encodeURIComponent(format)}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return response.text();
}
