"""Static assets for the Trust & Coverage dashboard."""

TRUST_DASHBOARD_STYLE = """
:root{--bg:#f4f5f1;--ink:#17211c;--muted:#617068;--line:#d6ddd3;--panel:#fffefa;--rail:#19392f;--ok:#1d6b44;--warn:#9b5f16;--bad:#9b2c2c;--blue:#214f7a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.shell{max-width:1180px;margin:0 auto;padding:28px}
.hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;padding:28px 0 18px;border-bottom:2px solid var(--ink)}
.eyebrow{margin:0 0 6px;text-transform:uppercase;letter-spacing:.08em;font-size:12px;color:var(--muted);font-weight:700}
h1,h2,h3{margin:0;letter-spacing:0}h1{font-size:34px}h2{font-size:23px}h3{font-size:15px}
.lede{max-width:760px;margin:10px 0 0;color:var(--muted)}
.stamp{text-align:right;min-width:220px}.stamp span,.card span,.card small{display:block;color:var(--muted);font-size:12px}.stamp strong{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.band{margin-top:22px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px}
.band.muted{background:#eef1ec}
.section-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px}
.pill,.status{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:3px 8px;font-size:12px;font-weight:700;color:var(--muted);white-space:nowrap}
.pill.ok{color:var(--ok);border-color:#9ec6ad}.pill.warn{color:var(--warn);border-color:#ddb574}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:10px;margin-bottom:16px}
.card{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fafbf7;min-height:92px}
.card strong{display:block;font-size:25px;margin:5px 0;color:var(--rail)}
.split{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.panel{border:1px solid var(--line);border-radius:8px;background:white;padding:12px;overflow:auto}.panel.full{margin-top:14px}
table{width:100%;border-collapse:collapse}th,td{padding:8px 9px;border-bottom:1px solid #e8ece5;text-align:left;vertical-align:top}th{font-size:12px;color:var(--muted);background:#f3f6f0}
.bar{height:10px;background:#e7ece4;border-radius:999px;overflow:hidden;min-width:90px}.bar i{display:block;height:100%;background:var(--blue)}
.num{text-align:right;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.note{color:var(--muted);margin:10px 0 0}.callout{margin-top:14px;border:1px solid var(--line);border-radius:8px;padding:12px}.callout.ok{border-color:#9ec6ad}.callout.warn{border-color:#ddb574}.notes{color:var(--muted)}
.status.loaded{color:var(--ok)}.status.missing,.status.invalid{color:var(--bad)}.status.not_provided,.status.empty{color:var(--warn)}
td{overflow-wrap:anywhere}
@media (max-width:760px){.shell{padding:16px}.hero,.section-head{display:block}.stamp{text-align:left;margin-top:14px}.split{grid-template-columns:1fr}h1{font-size:28px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""

