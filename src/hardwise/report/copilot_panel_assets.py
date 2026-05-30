"""Static CSS and JavaScript for the workbench Copilot panel."""

COPILOT_STYLE = """
.ai-fab{position:fixed;right:22px;bottom:22px;z-index:40;width:54px;height:54px;border:1px solid rgba(0,184,212,.65);background:#00b8d4;color:#001013;font-weight:900;font-family:var(--mono);box-shadow:0 16px 50px rgba(0,0,0,.45);cursor:pointer}
.ai-fab:hover{filter:brightness(1.08)}
.ai-panel{position:fixed;right:0;top:0;bottom:0;z-index:39;width:min(430px,100vw);display:grid;grid-template-rows:auto 1fr auto;border-left:1px solid var(--line);background:#0c100f;box-shadow:-22px 0 70px rgba(0,0,0,.48);transform:translateX(100%);transition:transform .18s ease}
.ai-panel.open{transform:translateX(0)}
.ai-panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:16px 16px 14px;border-bottom:1px solid var(--line);background:#111716}
.ai-panel-head h2{font-size:18px;margin:0 0 4px}
.ai-panel-head p{margin:0;color:var(--muted);font-size:12px}
.ai-close{width:32px;height:32px;border:1px solid var(--line);background:#070908;color:var(--ink);cursor:pointer;font-size:18px;line-height:1}
.ai-stream{min-height:0;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:11px}
.ai-msg{max-width:92%;border:1px solid var(--line);padding:10px 12px;font-size:13px}
.ai-msg.user{align-self:flex-end;background:#12302f;border-color:rgba(0,184,212,.4)}
.ai-msg.assistant{align-self:flex-start;background:#111514}
.ai-msg p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.ai-trace{margin-top:9px;border-top:1px solid var(--line);padding-top:7px}
.ai-trace summary{cursor:pointer;color:var(--muted);font:12px var(--mono)}
.ai-trace-row{margin-top:7px;padding:8px;border:1px solid var(--line);background:#0b0e0d}
.ai-trace-row strong{display:block;font:12px var(--mono);margin-bottom:5px;color:var(--rail)}
.ai-trace-row code{font:12px var(--mono);color:var(--muted);overflow-wrap:anywhere}
.ai-suggest{padding:10px 14px 0;display:flex;flex-wrap:wrap;gap:7px}
.ai-chip{border:1px solid var(--line);background:#101413;color:var(--ink);padding:7px 9px;font-size:12px;cursor:pointer}
.ai-chip:hover{border-color:var(--rail)}
.ai-compose{border-top:1px solid var(--line);padding:12px;background:#0b0e0d}
.ai-compose form{display:grid;grid-template-columns:1fr auto;gap:8px}
.ai-input{min-height:38px;border:1px solid var(--line);background:#060808;color:var(--ink);padding:8px 10px;font:13px var(--sans)}
.ai-input:focus{outline:2px solid rgba(0,184,212,.24);border-color:var(--rail)}
.ai-send{min-width:42px;border:1px solid var(--rail);background:var(--rail);color:#001013;font-weight:900;cursor:pointer}
.ai-mode{font:11px var(--mono);color:var(--muted);margin-top:8px}
@media(max-width:680px){.ai-fab{right:14px;bottom:14px}.ai-panel{width:100vw}.ai-msg{max-width:96%}}
@media print{.ai-fab,.ai-panel{display:none}}
"""

COPILOT_SCRIPT = """
(() => {
  const configNode = document.getElementById('hardwise-copilot-config');
  const root = document.querySelector('[data-ai-root]');
  if (!configNode || !root) return;
  const config = JSON.parse(configNode.textContent || '{}');
  const panel = root.querySelector('[data-ai-panel]');
  const openBtn = root.querySelector('[data-ai-open]');
  const closeBtn = root.querySelector('[data-ai-close]');
  const stream = root.querySelector('[data-ai-stream]');
  const form = root.querySelector('[data-ai-form]');
  const input = root.querySelector('[data-ai-input]');
  const suggestions = root.querySelector('[data-ai-suggest]');
  let selectedRefdes = config.selectedRefdes || '';
  const history = [];

  const open = () => panel.classList.add('open');
  const close = () => panel.classList.remove('open');
  openBtn.addEventListener('click', open);
  closeBtn.addEventListener('click', close);
  window.addEventListener('hardwise:refdes-selected', (event) => {
    selectedRefdes = event.detail && event.detail.refdes ? event.detail.refdes : selectedRefdes;
  });

  const scroll = () => { stream.scrollTop = stream.scrollHeight; };
  const addMessage = (role, text) => {
    const node = document.createElement('div');
    node.className = `ai-msg ${role}`;
    const p = document.createElement('p');
    node.appendChild(p);
    stream.appendChild(node);
    if (role === 'assistant') {
      let i = 0;
      const tick = () => {
        p.textContent = text.slice(0, i);
        i += Math.max(1, Math.ceil(text.length / 48));
        scroll();
        if (i <= text.length) window.setTimeout(tick, 12);
      };
      tick();
    } else {
      p.textContent = text;
    }
    scroll();
    return node;
  };
  const renderTrace = (node, response) => {
    const trace = response.trace || [];
    if (!trace.length) return;
    const details = document.createElement('details');
    details.className = 'ai-trace';
    const summary = document.createElement('summary');
    summary.textContent = 'Evidence / Tool trace';
    details.appendChild(summary);
    trace.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'ai-trace-row';
      const title = document.createElement('strong');
      title.textContent = `${item.tool || 'tool'} · ${item.status || item.summary || ''}`;
      const body = document.createElement('code');
      const evidence = (item.evidence || []).join(', ') || '-';
      body.textContent = `input=${JSON.stringify(item.input || {})} evidence=${evidence} wrapped=${item.wrapped || 0}`;
      row.appendChild(title);
      row.appendChild(body);
      details.appendChild(row);
    });
    node.appendChild(details);
  };
  const fallbackResponse = (question) => {
    const snapshots = config.snapshotResponses || {};
    if (snapshots[question]) return snapshots[question];
    if (/U999/i.test(question)) {
      const key = Object.keys(snapshots).find((item) => /U999/i.test(item));
      if (key) return snapshots[key];
    }
    const key = Object.keys(snapshots).find((item) => item !== '__fallback__' && !/U999/i.test(item));
    return snapshots[key] || snapshots.__fallback__ || {
      answer: 'This static snapshot only contains audited demo answers.',
      trace: [],
      suggestions: config.suggestions || []
    };
  };
  const ask = async (question) => {
    if (!question.trim()) return;
    open();
    addMessage('user', question);
    history.push({role: 'user', content: question});
    const pending = addMessage('assistant', 'Hardwise is checking evidence...');
    let response;
    try {
      if (config.mode === 'live') {
        const res = await fetch(config.apiEndpoint, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({question, selected_refdes: selectedRefdes, history: history.slice(-6)})
        });
        response = await res.json();
      } else {
        response = fallbackResponse(question);
      }
    } catch (error) {
      response = {answer: `Workbench chat failed: ${error}`, trace: []};
    }
    pending.remove();
    const answer = response.answer || '';
    const node = addMessage('assistant', answer);
    renderTrace(node, response);
    history.push({role: 'assistant', content: answer});
  };
  (config.suggestions || []).forEach((text) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ai-chip';
    button.textContent = text;
    button.addEventListener('click', () => ask(text));
    suggestions.appendChild(button);
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const question = input.value.trim();
    input.value = '';
    ask(question);
  });
})();
"""
