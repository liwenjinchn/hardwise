import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAIDisclosure } from "./api";
import type { AIDisclosure, WorkbenchState } from "./types";

export function useAIConsent(state: WorkbenchState | null) {
  const [descriptor, setDescriptor] = useState<AIDisclosure | null>(null);
  const [acknowledged, setAcknowledged] = useState<string | null>(null);
  const [error, setError] = useState("");
  const requestId = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++requestId.current;
    try {
      const next = await fetchAIDisclosure();
      if (id === requestId.current) {
        setDescriptor(next);
        setAcknowledged(old => old === next.disclosure_id ? old : null);
        setError("");
      }
      return next;
    } catch (err) {
      if (id === requestId.current) {
        setDescriptor(null);
        setAcknowledged(null);
        setError(err instanceof Error ? err.message : "无法取得 AI 发送说明");
      }
      throw err;
    }
  }, []);
  const project = state ? `${state.review_decisions?.project_id}|${state.project.netlist_source}|${state.project.bom_source}` : null;
  useEffect(() => {
    setAcknowledged(null);
    if (project) void refresh().catch(() => {});
  }, [project, refresh]);

  const prepare = async () => {
    const current = await refresh();
    if (!current.available) {
      setError(current.notice);
      return null;
    }
    if (current.mode === "real" && (!current.disclosure_id || acknowledged !== current.disclosure_id)) {
      setError("请先阅读并确认当前 AI 发送说明，再主动发送问题；不会自动提交暂存的问题。");
      return null;
    }
    return current;
  };
  return {
    descriptor, error, refresh, prepare,
    confirmed: Boolean(descriptor?.disclosure_id && acknowledged === descriptor.disclosure_id),
    acknowledge: (checked: boolean) => setAcknowledged(checked ? descriptor?.disclosure_id ?? null : null)
  };
}

export type AIConsent = ReturnType<typeof useAIConsent>;
