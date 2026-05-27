"""Static assets for the multi-component validator UI."""

MULTI_UI_STYLE = """
:root{color-scheme:light;--ink:#16211d;--muted:#66736e;--line:#d7dfdb;--paper:#f3f5f4;--panel:#ffffff;--rail:#1f342d;--pass:#2f6b4b;--warn:#a96420;--error:#bc3b2c;--info:#2d667a;--soft:#eef2f0;--mono:"SFMono-Regular","Cascadia Code","Liberation Mono",monospace;--sans:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;--serif:"Iowan Old Style","Palatino Linotype",Georgia,serif;--shadow:0 24px 70px rgba(30,42,36,.12)}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.42}
body:before{content:"";position:fixed;inset:0;z-index:-1;background:linear-gradient(90deg,rgba(31,52,45,.06) 1px,transparent 1px),linear-gradient(0deg,rgba(31,52,45,.045) 1px,transparent 1px);background-size:30px 30px}
main{width:min(1480px,calc(100% - 24px));margin:0 auto;padding:18px 0 32px}
.app{border:1px solid var(--line);background:rgba(255,255,255,.97);box-shadow:var(--shadow)}
.topbar{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:22px;align-items:stretch;border-bottom:1px solid var(--line)}
.brand{padding:22px 28px 20px;border-left:8px solid var(--rail)}
.eyebrow{margin:0 0 8px;color:var(--muted);font-family:var(--mono);font-size:12px;text-transform:uppercase}
h1{margin:0;font-family:var(--serif);font-size:40px;line-height:1;letter-spacing:0}
.source{margin:11px 0 0;color:var(--muted);font-family:var(--mono);font-size:12px;overflow-wrap:anywhere}
.summary{display:grid;grid-template-columns:repeat(5,110px);border-left:1px solid var(--line);background:var(--soft)}
.metric{padding:17px 14px;border-right:1px solid var(--line)}
.metric:last-child{border-right:0}
.metric span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.metric strong{display:block;margin-top:8px;font-family:var(--serif);font-size:31px;line-height:1}
.metric.pass strong{color:var(--pass)}.metric.warn strong{color:var(--warn)}.metric.error strong{color:var(--error)}
.workspace{display:grid;grid-template-columns:360px minmax(300px,.47fr) minmax(480px,.8fr);min-height:760px}
.rail,.verify{border-right:1px solid var(--line);background:#fbfcfb}
.rail-head,.verify-head{padding:16px 18px;border-bottom:1px solid var(--line)}
.section-title{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
h2,h3{margin:0;font-size:18px;line-height:1.2}
.count{font-family:var(--serif);font-size:30px;line-height:1}
.filter{width:100%;min-height:36px;border:1px solid var(--line);background:#fff;padding:7px 10px;font:13px var(--mono);color:var(--ink)}
.filter:focus{outline:2px solid rgba(45,102,122,.22);border-color:var(--info)}
.table-wrap{max-height:680px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;z-index:1;background:#e5ebe8;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.component-row{cursor:pointer}
.component-row:hover,.component-row.active{background:#eef4ef}
.ref{font-family:var(--mono);font-weight:800;letter-spacing:0}
.sub{display:block;margin-top:3px;color:var(--muted);font-size:12px}
.status{display:inline-flex;align-items:center;justify-content:center;min-width:58px;min-height:24px;padding:3px 7px;border:1px solid currentColor;font-family:var(--mono);font-size:11px;font-weight:800}
.pass{color:var(--pass)}.warn{color:var(--warn)}.error{color:var(--error)}.pending{color:var(--info)}
.verified-list{padding:14px;display:grid;gap:10px}
.device-card{width:100%;text-align:left;border:1px solid var(--line);background:#fff;padding:12px 12px;cursor:pointer}
.device-card.active{outline:2px solid rgba(31,52,45,.18);background:#f5f9f5}
.device-line{display:flex;align-items:center;justify-content:space-between;gap:10px}
.device-title{font-family:var(--mono);font-weight:800}
.device-meta{margin:8px 0 0;color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.issue-list{display:grid;gap:8px;margin-top:12px}
.issue{border:1px solid var(--line);background:#fff8f4;padding:10px}
.issue strong{display:block;font-family:var(--mono);margin-bottom:4px}
.detail{min-width:0;background:var(--panel)}
.panel{display:none}
.panel.active{display:block}
.detail-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:start;padding:20px 24px;border-bottom:1px solid var(--line)}
.detail-title h2{font-family:var(--serif);font-size:36px;margin:0 0 9px;line-height:1}
.detail-title p{margin:0;color:var(--muted)}
.actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.button{display:inline-flex;align-items:center;min-height:34px;padding:7px 11px;border:1px solid var(--rail);background:var(--rail);color:#fff;text-decoration:none;font-size:13px}
.button.secondary{background:#fff;color:var(--rail)}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);border-bottom:1px solid var(--line)}
.kpi{padding:15px 16px;border-right:1px solid var(--line)}
.kpi:last-child{border-right:0}
.kpi span{display:block;color:var(--muted);font-family:var(--mono);font-size:11px;text-transform:uppercase}
.kpi strong{display:block;margin-top:7px;font-size:22px}
.section{padding:20px 24px;border-bottom:1px solid var(--line)}
.section:last-child{border-bottom:0}
.section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:13px}
.pin-feed{display:grid;gap:9px}
.pin-note{display:grid;grid-template-columns:76px minmax(0,1fr) auto;gap:12px;align-items:start;border:1px solid var(--line);background:#f8fbf9;padding:10px 12px}
.pin-note p{margin:0;color:#33413b}
.check-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.check-card{border:1px solid var(--line);background:#fff8f4;padding:12px}
.check-card p{margin:6px 0 0}
.table-section{overflow:auto}
.evidence code,.net code{display:inline-block;margin:0 4px 4px 0;padding:3px 5px;background:#edf3f0;font-family:var(--mono);font-size:12px}
.scope{margin:0;padding:13px 15px;border-left:5px solid var(--rail);background:#f2f6f4;color:#3d4742}
.net-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.net{padding:12px;border:1px solid var(--line);background:#f8fbf9}
.net b{display:block;margin-bottom:8px;font-family:var(--mono)}
ul.boundary-list{margin:0;padding-left:20px}
ul.boundary-list li{margin:8px 0}
.hidden{display:none!important}
@media(max-width:1180px){.topbar,.workspace,.detail-head,.kpis,.check-grid,.net-grid{grid-template-columns:1fr}.summary{grid-template-columns:repeat(5,1fr);border-left:0}.rail,.verify{border-right:0;border-bottom:1px solid var(--line)}.actions{justify-content:flex-start}.kpi{border-right:0;border-bottom:1px solid var(--line)}}
@media(max-width:680px){main{width:min(100% - 14px,1480px);padding:10px 0 22px}.summary{grid-template-columns:repeat(2,1fr)}.pin-note{grid-template-columns:1fr}.detail-title h2{font-size:30px}}
@media print{body{background:#fff}body:before{display:none}main{width:100%;padding:0}.app{box-shadow:none}.table-wrap{max-height:none}.button,.filter{display:none}}
"""

MULTI_UI_SCRIPT = """
(() => {
  const panels = Array.from(document.querySelectorAll('[data-panel]'));
  const cards = Array.from(document.querySelectorAll('[data-select-ref]'));
  const rows = Array.from(document.querySelectorAll('[data-row-ref]'));
  const activate = (ref) => {
    panels.forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === ref));
    cards.forEach((card) => card.classList.toggle('active', card.dataset.selectRef === ref));
    rows.forEach((row) => row.classList.toggle('active', row.dataset.rowRef === ref));
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
