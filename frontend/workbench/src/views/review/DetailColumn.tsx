import { useEffect, useState } from "react";
import { Bot, Download, FileSearch, Layers3, Loader2 } from "lucide-react";
import { fetchPrepPacketMarkdown } from "../../api";
import { CheckCard, InfoCell, StatusBadge, TrustBadge, VerdictBanner } from "../../components/ui";
import {
  documentStatusGroup,
  documentStatusLabel,
  formatSummary,
  pinStatusLabel,
  profileStatusLabel,
  statusGroup,
  taskKindLabel
} from "../../lib/format";
import type { ComponentDetail, DocumentCoverageView, ReviewTask } from "../../types";

export function DetailColumn({
  detail,
  loading,
  onAsk
}: {
  detail: ComponentDetail | null;
  loading: boolean;
  onAsk: () => void;
}) {
  const [prepPreview, setPrepPreview] = useState("");
  const [prepBusy, setPrepBusy] = useState(false);
  const [prepError, setPrepError] = useState("");

  useEffect(() => {
    setPrepPreview("");
    setPrepError("");
  }, [detail?.refdes]);

  const loadPrepPacket = async (download: boolean) => {
    if (!detail || prepBusy) return;
    setPrepBusy(true);
    setPrepError("");
    try {
      const markdown = await fetchPrepPacketMarkdown(detail.refdes);
      if (download) {
        const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `hardwise-prep-${detail.refdes}.md`;
        anchor.click();
        URL.revokeObjectURL(url);
      } else {
        setPrepPreview(markdown);
      }
    } catch (err) {
      setPrepError(err instanceof Error ? err.message : "准备包生成失败");
    } finally {
      setPrepBusy(false);
    }
  };

  if (loading) {
    return (
      <section className="panel detail-panel empty-panel">
        <Loader2 className="spin" />
        <p>正在读取器件详情...</p>
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="panel detail-panel empty-panel">
        <FileSearch size={32} />
        <p>请选择一个器件查看审查详情。</p>
      </section>
    );
  }

  return (
    <section className="panel detail-panel">
      <div className="detail-scroll" key={detail.refdes}>
        <div className="component-title detail-head">
          <span className="detail-glyph"><Layers3 size={24} /></span>
          <div className="detail-title">
            <span className="eyebrow">器件详情</span>
            <h2>{detail.refdes}</h2>
            <p>{detail.value}</p>
            <div className="detail-keyline">
              <span className="chip mono">{detail.part_number || "无 MPN"}</span>
              <span className="chip">{detail.package || "无封装"}</span>
              <span className="chip">{detail.manufacturer || "未知厂商"}</span>
              <span className="chip mono">{detail.profile_part_number || "待补档案"}</span>
            </div>
          </div>
          <div className="title-actions">
            <StatusBadge
              group={detail.deterministic_status_group}
              label={`电气 ${detail.deterministic_status_label}`}
            />
            <TrustBadge tier={detail.trust_tier} />
            <button className="icon-text-btn" type="button" onClick={onAsk}>
              <Bot size={14} />
              问 Copilot
            </button>
          </div>
        </div>
        <VerdictBanner group={detail.deterministic_status_group} />
        <div className="identity-grid">
          <InfoCell label="MPN" value={detail.part_number || "-"} />
          <InfoCell label="厂商" value={detail.manufacturer || "-"} />
          <InfoCell label="封装" value={detail.package || "-"} />
          <InfoCell label="器件档案" value={detail.profile_part_number || "待补"} />
          <InfoCell label="BOM 来源" value={detail.bom?.source || "-"} />
          <InfoCell label="档案状态" value={profileStatusLabel(detail.profile?.status || detail.match_status)} />
          <InfoCell label="原始任务" value={`${detail.task_counts.total} 条`} />
        </div>
        {detail.match_reason && <p className="scope-note">{formatSummary(detail.match_reason)}</p>}
        <DocumentCoverageSection document={detail.document} />
        <section className="prep-actions" aria-label="评审准备包">
          <div>
            <span className="eyebrow">Prep Packet</span>
            <strong>评审准备包</strong>
            <p>把当前器件身份、BOM/profile/document 状态、tasks、risk hints 和 evidence 汇总成可交接资料。</p>
          </div>
          <button className="icon-text-btn" type="button" onClick={() => void loadPrepPacket(false)} disabled={prepBusy}>
            {prepBusy ? <Loader2 className="spin" size={14} /> : <FileSearch size={14} />}
            预览
          </button>
          <button className="icon-text-btn" type="button" onClick={() => void loadPrepPacket(true)} disabled={prepBusy}>
            <Download size={14} />
            下载 MD
          </button>
        </section>
        {prepError && <p className="form-error detail-error">{prepError}</p>}
        {prepPreview && <pre className="prep-preview">{prepPreview}</pre>}
        <section className="detail-section">
          <div className="section-title">
            <h3>审查任务</h3>
            <span>{detail.tasks.length} tasks</span>
          </div>
          <div className="detail-task-list">
            {detail.tasks.length === 0 && <p className="muted">当前器件没有进入 finding 队列。</p>}
            {detail.tasks.map((task, index) => (
              <TaskCard task={task} index={index} key={task.id} />
            ))}
          </div>
        </section>
        <section className="detail-section">
          <div className="section-title">
            <h3>引脚 / 网络表</h3>
            <span>{detail.pins.length} pins</span>
          </div>
          <div className="pin-table">
            <div className="pin-head">Pin</div>
            <div className="pin-head">Name</div>
            <div className="pin-head">Net</div>
            <div className="pin-head">状态</div>
            {detail.pins.map((pin) => (
              <div className="pin-row" key={`${pin.number}-${pin.name}`}>
                <span className="mono">{pin.number}</span>
                <span>{pin.name}</span>
                <span className="mono net-name">{pin.net || "-"}</span>
                <span>{pin.status ? <StatusBadge group={statusGroup(pin.status)} label={pinStatusLabel(pin.status)} /> : "-"}</span>
              </div>
            ))}
          </div>
        </section>
        <section className="detail-section">
          <div className="section-title">
            <h3>确定性检查</h3>
            <span>{detail.checks.length} checks</span>
          </div>
          <div className="check-list">
            {detail.checks.length === 0 && <p className="muted">该器件没有组件级检查，或仍待人工补档案。</p>}
            {detail.checks.map((check) => (
              <CheckCard check={check} key={`${check.subject}-${check.summary}`} />
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function DocumentCoverageSection({ document }: { document: DocumentCoverageView | null | undefined }) {
  const coverage = document ?? {
    status: "not_configured",
    group_id: null,
    identity: "",
    identity_kind: "",
    suggested_family: "",
    title: null,
    url: null,
    source: null,
    candidates: 0,
    reason: "No document index was provided.",
    candidate_search: null
  };
  const matched = coverage.status === "matched" || coverage.status === "loaded";
  return (
    <section className="detail-section doc-coverage" aria-label="资料索引">
      <div className="section-title">
        <h3>资料索引</h3>
        <StatusBadge group={documentStatusGroup(coverage.status)} label={documentStatusLabel(coverage.status)} />
      </div>
      <div className="doc-coverage-card">
        {coverage.title && (
          <div className="doc-coverage-line">
            <strong className="doc-title">{coverage.title}</strong>
            {coverage.source && <span className="source-badge">{coverage.source}</span>}
          </div>
        )}
        {coverage.url && (
          <a className="doc-link" href={coverage.url} target="_blank" rel="noreferrer">
            {coverage.url}
          </a>
        )}
        {!matched && (
          <p className="doc-reason">
            {formatSummary(coverage.reason)}
            {coverage.candidates > 0 ? `（候选 ${coverage.candidates} 条）` : ""}
          </p>
        )}
        {coverage.candidate_search && (
          <DatasheetCandidateSearchBlock search={coverage.candidate_search} />
        )}
        <p className="doc-note">覆盖状态只说明本地公开资料索引是否有已审核链接，不构成电气结论。</p>
      </div>
    </section>
  );
}

function DatasheetCandidateSearchBlock({
  search
}: {
  search: NonNullable<DocumentCoverageView["candidate_search"]>;
}) {
  return (
    <div className="candidate-search-block" aria-label="公开资料候选">
      <div className="doc-coverage-line">
        <strong>公开候选</strong>
        <StatusBadge group={candidateStatusGroup(search.status)} label={candidateStatusLabel(search.status)} />
        <span className="source-badge">{search.provider}</span>
      </div>
      <p className="doc-reason">
        查询 {search.query || "-"}：{search.count} 个结果，direct PDF {search.direct_datasheet_count} 个
        {typeof search.remaining_month === "number" ? `，本月剩余 ${search.remaining_month}` : ""}
        {search.reason ? `；${search.reason}` : ""}
      </p>
      {search.candidates.length > 0 && (
        <div className="candidate-list">
          {search.candidates.slice(0, 3).map((candidate) => (
            <article className="candidate-card" key={`${candidate.mpn}-${candidate.datasheet_url ?? candidate.product_url ?? ""}`}>
              <div className="candidate-line">
                <strong>{candidate.mpn}</strong>
                <span>{candidate.manufacturer || "-"}</span>
                <span>{candidate.review_status}</span>
              </div>
              {candidate.title && <p>{candidate.title}</p>}
              {candidate.datasheet_url && (
                <code className="candidate-url">{candidate.datasheet_url}</code>
              )}
            </article>
          ))}
        </div>
      )}
      <p className="doc-note">候选只进入人工审核队列；不会下载 PDF、不会自动 approve，也不会改变 PASS/WARN/ERROR。</p>
    </div>
  );
}

function candidateStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    found: "有候选",
    no_result: "无结果",
    not_configured: "未配置",
    rate_limited: "限流",
    cloudflare_challenge: "被拦截",
    provider_error: "查询失败"
  };
  return labels[status] ?? status;
}

function candidateStatusGroup(status: string) {
  if (status === "found") return "warn";
  return "manual";
}

function TaskCard({ task, index }: { task: ReviewTask; index: number }) {
  const source = task.kind === "pin_table_check" ? "Capture 引脚表" : taskKindLabel(task.kind);
  return (
    <article className={`detail-task-card ${task.status_group}`}>
      <div className="card-line">
        <strong>问题 {index + 1}</strong>
        <StatusBadge group={task.status_group} label={task.status_label} />
        <span className={task.kind === "pin_table_check" ? "source-badge" : "task-source"}>
          {source}{task.pin_number ? ` · ${task.pin_number}脚` : ""}
        </span>
      </div>
      <p>{formatSummary(task.title)}</p>
    </article>
  );
}
