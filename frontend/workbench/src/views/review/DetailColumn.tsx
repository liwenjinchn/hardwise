import { useEffect, useState } from "react";
import { Bot, Download, FileSearch, Layers3, Loader2 } from "lucide-react";
import { fetchPrepPacketMarkdown } from "../../api";
import { CheckCard, InfoCell, StatusBadge, TrustBadge, VerdictBanner } from "../../components/ui";
import {
  documentStatusLabel,
  formatSummary,
  pinStatusLabel,
  profileStatusLabel,
  statusGroup
} from "../../lib/format";
import type { ComponentDetail } from "../../types";

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
            <StatusBadge group={detail.status_group} label={detail.status_label} />
            <TrustBadge tier={detail.trust_tier} />
            <button className="icon-text-btn" type="button" onClick={onAsk}>
              <Bot size={14} />
              问 Copilot
            </button>
          </div>
        </div>
        <VerdictBanner group={detail.status_group} />
        <div className="identity-grid">
          <InfoCell label="MPN" value={detail.part_number || "-"} />
          <InfoCell label="厂商" value={detail.manufacturer || "-"} />
          <InfoCell label="封装" value={detail.package || "-"} />
          <InfoCell label="器件档案" value={detail.profile_part_number || "待补"} />
          <InfoCell label="BOM 来源" value={detail.bom?.source || "-"} />
          <InfoCell label="档案状态" value={profileStatusLabel(detail.profile?.status || detail.match_status)} />
          <InfoCell label="文档索引" value={documentStatusLabel(detail.document?.status || "not_configured")} />
          <InfoCell label="任务数" value={`${detail.task_counts.total} 项`} />
        </div>
        {detail.match_reason && <p className="scope-note">{formatSummary(detail.match_reason)}</p>}
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
