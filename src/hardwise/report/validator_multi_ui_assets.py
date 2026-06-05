"""Static assets for the multi-component validator UI."""

MULTI_UI_STYLE = """
:root{color-scheme:dark;--ink:#e7ecea;--muted:#8f9d98;--line:#232b29;--paper:#090b0b;--panel:#101413;--rail:#00b8d4;--pass:#12d98b;--warn:#ffb02e;--error:#ff554a;--info:#4ea1ff;--soft:#141918;--mono:"SFMono-Regular","Cascadia Code","Liberation Mono",monospace;--sans:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;--serif:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;--shadow:0 24px 80px rgba(0,0,0,.42)}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.42}
body:before{content:"";position:fixed;inset:0;z-index:-1;background:radial-gradient(circle at 78% 4%,rgba(0,184,212,.12),transparent 26%),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(0deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:auto,30px 30px,30px 30px}
main{width:min(1520px,calc(100% - 16px));margin:0 auto;padding:8px 0 18px}
.app{border:1px solid var(--line);background:#0d100f;box-shadow:var(--shadow);min-height:calc(100vh - 18px)}
.topbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:22px;align-items:stretch;border-bottom:1px solid var(--line)}
.brand{padding:18px 24px 16px;border-left:4px solid var(--rail)}
.eyebrow{margin:0 0 8px;color:var(--muted);font-family:var(--mono);font-size:12px;text-transform:uppercase}
h1{margin:0;font-family:var(--serif);font-size:34px;line-height:1;letter-spacing:0;font-weight:800}
.source{margin:11px 0 0;color:var(--muted);font-family:var(--mono);font-size:12px;overflow-wrap:anywhere}
.summary{display:grid;grid-template-columns:repeat(7,110px);border-left:1px solid var(--line);background:var(--soft)}
.metric{padding:17px 14px;border-right:1px solid var(--line)}
.metric:last-child{border-right:0}
.metric span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.metric strong{display:block;margin-top:8px;font-family:var(--serif);font-size:31px;line-height:1}
.metric.pass strong{color:var(--pass)}.metric.warn strong{color:var(--warn)}.metric.error strong{color:var(--error)}
.workspace{display:grid;grid-template-columns:minmax(360px,480px) minmax(520px,1fr);min-height:760px}
.left-stack{display:grid;grid-template-rows:minmax(0,1fr) auto;min-height:760px;border-right:1px solid var(--line);background:#0b0e0d}
.rail,.verify{background:#0b0e0d}
.rail{min-height:0;border-bottom:1px solid var(--line)}
.rail-head,.verify-head{padding:16px 18px;border-bottom:1px solid var(--line)}
.section-title{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
h2,h3{margin:0;font-size:18px;line-height:1.2}
.count{font-family:var(--serif);font-size:30px;line-height:1}
.filter{width:100%;min-height:36px;border:1px solid var(--line);background:#060808;padding:7px 10px;font:13px var(--mono);color:var(--ink)}
.filter:focus{outline:2px solid rgba(45,102,122,.22);border-color:var(--info)}
.table-wrap{max-height:520px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;z-index:1;background:#121716;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.component-row{cursor:pointer}
.component-row:hover,.component-row.active{background:#111d1c}
.ref{font-family:var(--mono);font-weight:800;letter-spacing:0}
.sub{display:block;margin-top:3px;color:var(--muted);font-size:12px}
.status{display:inline-flex;align-items:center;justify-content:center;min-width:58px;min-height:24px;padding:3px 7px;border:1px solid currentColor;font-family:var(--mono);font-size:11px;font-weight:800}
.pass{color:var(--pass)}.warn{color:var(--warn)}.error{color:var(--error)}.pending{color:var(--info)}
.verified-list{padding:14px;display:grid;gap:10px}
.device-card{width:100%;text-align:left;border:1px solid var(--line);background:#101413;color:var(--ink);padding:12px 12px;cursor:pointer}
.device-card.active{outline:2px solid rgba(0,184,212,.3);background:#101b1b}
.device-line{display:flex;align-items:center;justify-content:space-between;gap:10px}
.device-title{font-family:var(--mono);font-weight:800}
.device-meta{margin:8px 0 0;color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.issue-list{display:grid;gap:8px;margin-top:12px}
.issue{border:1px solid rgba(255,85,74,.35);background:#1a1110;padding:10px}
.issue strong{display:block;font-family:var(--mono);margin-bottom:4px}
.gap-list{display:grid;gap:9px;margin-top:12px}
.gap-card{border:1px solid var(--line);background:#101413;padding:10px 12px}
.gap-card strong{display:block;font-family:var(--mono);margin-bottom:5px}
.gap-card p{margin:0;color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.coverage-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.detail{min-width:0;background:var(--panel)}
.panel{display:none}
.panel.active{display:block}
.detail-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:start;padding:20px 24px;border-bottom:1px solid var(--line)}
.detail-title h2{font-family:var(--serif);font-size:36px;margin:0 0 9px;line-height:1}
.detail-title p{margin:0;color:var(--muted)}
.actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.button{display:inline-flex;align-items:center;min-height:34px;padding:7px 11px;border:1px solid var(--rail);background:var(--rail);color:#001013;text-decoration:none;font-size:13px;font-weight:800}
.button.secondary{background:transparent;color:var(--rail)}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:1px solid var(--line)}
.kpi{padding:15px 16px;border-right:1px solid var(--line)}
.kpi:last-child{border-right:0}
.kpi span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.kpi strong{display:block;margin-top:7px;font-size:22px}
.section{padding:20px 24px;border-bottom:1px solid var(--line)}
.section:last-child{border-bottom:0}
.section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:13px}
.pin-feed{display:grid;gap:9px}
.pin-note{display:grid;grid-template-columns:76px minmax(0,1fr) auto;gap:12px;align-items:start;border:1px solid var(--line);background:#0d1211;padding:10px 12px}
.pin-note p{margin:0;color:#cdd8d4}
.check-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.check-card{border:1px solid var(--line);background:#14100f;padding:12px}
.check-card p{margin:6px 0 0}
.table-section{overflow:auto}
.evidence code,.net code,.evidence-chip{display:inline-block;margin:0 4px 4px 0;padding:3px 5px;background:#17211f;font-family:var(--mono);font-size:12px}
.evidence-chip{border:1px solid #263f39;color:#b7e8d7}
.evidence-gap{display:inline-block;margin:0 4px 4px 0;padding:3px 6px;border:1px solid #5a4a1f;background:#231d0e;color:#e8d3a0;font-family:var(--mono);font-size:11px;font-weight:700}
.trust{display:inline-flex;align-items:center;min-height:24px;padding:3px 7px;border:1px solid currentColor;font-family:var(--mono);font-size:11px;font-weight:800;white-space:nowrap}
.trust-l1{color:var(--pass)}.trust-l2{color:var(--info)}.trust-l3{color:var(--warn)}
.scope{margin:0;padding:13px 15px;border-left:5px solid var(--rail);background:#101918;color:#c4d0cc}
.net-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.net{padding:12px;border:1px solid var(--line);background:#0d1211}
.net b{display:block;margin-bottom:8px;font-family:var(--mono)}
ul.boundary-list{margin:0;padding-left:20px}
ul.boundary-list li{margin:8px 0}
.hidden{display:none!important}
@media(max-width:1180px){.topbar,.workspace,.detail-head,.kpis,.check-grid,.net-grid,.coverage-grid{grid-template-columns:1fr}.summary{grid-template-columns:repeat(3,1fr);border-left:0}.left-stack{border-right:0;border-bottom:1px solid var(--line)}.actions{justify-content:flex-start}.kpi{border-right:0;border-bottom:1px solid var(--line)}}
@media(max-width:680px){main{width:min(100% - 14px,1480px);padding:10px 0 22px}.summary{grid-template-columns:repeat(2,1fr)}.pin-note{grid-template-columns:1fr}.detail-title h2{font-size:30px}}
@media print{body{background:#fff}body:before{display:none}main{width:100%;padding:0}.app{box-shadow:none}.table-wrap{max-height:none}.button,.filter{display:none}}
"""

MULTI_UI_SCRIPT = """
(() => {
  const panels = Array.from(document.querySelectorAll('[data-panel]'));
  const cards = Array.from(document.querySelectorAll('[data-select-ref]'));
  const rows = Array.from(document.querySelectorAll('[data-row-ref]'));
  let activeRefdes = rows.find((row) => row.classList.contains('active'))?.dataset.rowRef || '';
  const activate = (ref) => {
    activeRefdes = ref;
    const hasPanel = panels.some((panel) => panel.dataset.panel === ref);
    if (hasPanel) {
      panels.forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === ref));
      cards.forEach((card) => card.classList.toggle('active', card.dataset.selectRef === ref));
    }
    rows.forEach((row) => row.classList.toggle('active', row.dataset.rowRef === ref));
    window.dispatchEvent(new CustomEvent('hardwise:refdes-selected', {detail: {refdes: activeRefdes}}));
  };
  [...cards, ...rows].forEach((node) => {
    node.addEventListener('click', () => activate(node.dataset.selectRef || node.dataset.rowRef));
  });
  const filter = document.querySelector('[data-filter]');
  if (filter) {
    filter.addEventListener('input', () => {
      const q = filter.value.trim().toLowerCase();
      rows.forEach((row) => {
        row.classList.toggle('hidden', q && !row.textContent.toLowerCase().includes(q));
      });
    });
  }
})();
"""
