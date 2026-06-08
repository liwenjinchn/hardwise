import type { ChatMessage, ChatResponse, ComponentDetail, WorkbenchState } from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
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
