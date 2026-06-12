"""Static CSS and JavaScript for the workbench Copilot panel."""

COPILOT_STYLE = """
.ai-fab{position:fixed;right:22px;bottom:22px;z-index:40;width:54px;height:54px;border:1px solid rgba(0,184,212,.65);background:#00b8d4;color:#001013;font-weight:900;font-family:var(--mono);box-shadow:0 16px 50px rgba(0,0,0,.45);cursor:pointer}
.ai-fab:hover{filter:brightness(1.08)}
.ai-root.ai-open .ai-fab{display:none}
.ai-panel{position:fixed;right:0;top:0;bottom:0;z-index:39;width:min(430px,100vw);display:grid;grid-template-rows:auto auto auto minmax(0,1fr) auto;border-left:1px solid var(--line);background:#0c100f;box-shadow:-22px 0 70px rgba(0,0,0,.48);transform:translateX(100%);transition:transform .18s ease}
.ai-panel.open{transform:translateX(0)}
.ai-panel-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:16px 16px 14px;border-bottom:1px solid var(--line);background:#111716}
.ai-panel-head h2{font-size:18px;margin:0 0 4px}
.ai-panel-head p{margin:0;color:var(--muted);font-size:12px}
.ai-close{width:32px;height:32px;border:1px solid var(--line);background:#070908;color:var(--ink);cursor:pointer;font-size:18px;line-height:1}
.ai-stream{min-height:0;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:11px}
.ai-guide{margin:8px 14px 0;padding:0;color:var(--muted);font-size:12px;line-height:1.55}
.ai-guide strong{display:inline;margin-right:8px;color:#b8c5c0;font-size:12px;font-weight:800}
.ai-guide span{display:inline;overflow-wrap:anywhere}
.ai-msg{max-width:92%;border:1px solid var(--line);padding:10px 12px;font-size:13px}
.ai-msg.user{align-self:flex-end;background:#12302f;border-color:rgba(0,184,212,.4)}
.ai-msg.assistant{align-self:flex-start;background:#111514}
.ai-msg p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
.ai-trace{margin-top:9px;border-top:1px solid var(--line);padding-top:7px}
.ai-trace summary{cursor:pointer;color:var(--muted);font:12px var(--mono)}
.ai-trace-row{margin-top:7px;padding:9px;border:1px solid var(--line);background:#0b0e0d;display:grid;gap:7px}
.ai-trace-row-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
.ai-trace-row strong{font:12px var(--mono);color:var(--rail);overflow-wrap:anywhere}
.ai-trace-status{font:11px var(--mono);color:var(--ink);border:1px solid var(--line);padding:2px 5px}
.ai-trace-summary{margin:0;color:var(--ink);font-size:12px}
.ai-trace-field{display:grid;grid-template-columns:82px minmax(0,1fr);gap:8px;align-items:start;font:12px var(--mono)}
.ai-trace-label{color:var(--muted)}
.ai-trace-value{color:var(--ink);overflow-wrap:anywhere}
.ai-trace-input{margin:0;padding:7px;border:1px solid var(--line);background:#070908;color:var(--muted);white-space:pre-wrap;overflow-wrap:anywhere;font:11px var(--mono)}
.evidence-chip{display:inline-block;margin:0 4px 4px 0;padding:3px 5px;border:1px solid #263f39;background:#17211f;color:#b7e8d7;font:11px var(--mono);text-decoration:none;cursor:pointer}
.evidence-chip:hover{border-color:var(--rail);color:#d8fff0}
.ai-suggest{padding:10px 14px 0;display:flex;flex-wrap:wrap;gap:7px}
.ai-chip{border:1px solid var(--line);background:#101413;color:var(--ink);padding:7px 9px;font-size:12px;cursor:pointer}
.ai-chip:hover{border-color:var(--rail)}
.ai-compose{border-top:1px solid var(--line);padding:12px;background:#0b0e0d}
.ai-compose form{display:grid;grid-template-columns:1fr auto;gap:8px}
.ai-input{min-height:38px;border:1px solid var(--line);background:#060808;color:var(--ink);padding:8px 10px;font:13px var(--sans)}
.ai-input:focus{outline:2px solid rgba(0,184,212,.24);border-color:var(--rail)}
.ai-send{min-width:42px;border:1px solid var(--rail);background:var(--rail);color:#001013;font-weight:900;cursor:pointer}
.ai-mode{font:11px var(--mono);color:var(--muted);margin-top:8px}
@media(max-width:680px){.ai-fab{right:14px;bottom:14px}.ai-panel{width:100vw;display:none}.ai-panel.open{display:grid}.ai-msg{max-width:96%}}
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

  const open = () => {
    panel.classList.add('open');
    root.classList.add('ai-open');
  };
  const close = () => {
    panel.classList.remove('open');
    root.classList.remove('ai-open');
  };
  openBtn.addEventListener('click', open);
  closeBtn.addEventListener('click', close);
  window.addEventListener('hardwise:refdes-selected', (event) => {
    selectedRefdes = event.detail && event.detail.refdes ? event.detail.refdes : selectedRefdes;
  });

  const scroll = () => { stream.scrollTop = stream.scrollHeight; };
  const toolLabels = {
    run_component_validation: '器件验证',
    search_datasheet: '数据手册检索',
    list_components: '器件清单',
    get_component: '器件详情',
    get_component_context: '连接上下文',
    get_nc_pins: 'NC 引脚',
    get_component_documents: '资料匹配',
    summarize_document_coverage: '资料覆盖',
    find_component_by_refdes: '位号查询',
    inspect_net: '网络查询',
    get_net_context: '网络详情',
    search_nets: '网络搜索',
    summarize_design: '设计摘要',
    summarize_project_topology: '项目拓扑摘要'
  };
  const statusLabels = {
    trace: '记录',
    validated: '已验证',
    found: '已找到',
    not_found: '未找到',
    not_configured: '未配置',
    configured: '已配置',
    skipped: '已跳过',
    matched: '已匹配',
    no_result: '无结果',
    ambiguous: '多候选',
    manual_needed: '需人工确认'
  };
  const trustLabels = {
    'L1 deterministic': 'L1 确定性',
    'L2 grounded': 'L2 有出处',
    'L3 manual': 'L3 人工确认',
    l1: 'L1 确定性',
    l2: 'L2 有出处',
    l3: 'L3 人工确认'
  };
  const evidenceClassLabels = {
    live_retrieved: '本轮检索证据',
    reviewed_profile: '已审 profile 证据',
    document_index: '资料索引证据',
    design_source: '设计来源证据',
    unknown: '未知证据来源'
  };
  const auditStatusLabels = {
    ok: '可定位',
    missing_local_source: '本地源缺失'
  };
  const traceSummaryLabel = (text) => {
    const value = String(text || '');
    if (value === 'skipped: vector store not configured') return '已跳过：未配置向量数据手册库';
    if (value === 'status=validated') return '状态：已完成确定性验证';
    if (value === 'status=found') return '状态：已找到';
    if (value === 'status=matched') return '状态：已匹配';
    if (value === 'status=not_found') return '状态：未找到';
    if (value === 'status=not_configured') return '状态：未配置';
    if (value.startsWith('hits=')) return `命中数：${value.slice(5)}`;
    if (value.startsWith('components=')) return value.replace('components=', '器件数：').replace(', nets=', '，网络数：');
    if (value.startsWith('groups=')) return value.replace('groups=', '分组数：');
    return value;
  };
  const evidenceClassSummary = (items) => {
    const classifications = items || [];
    if (!classifications.length) return '-';
    return classifications.map((item) => {
      const source = evidenceClassLabels[item.source_class] || item.source_class || '未知来源';
      const audit = auditStatusLabels[item.audit_status] || item.audit_status || '';
      return audit && audit !== '可定位' ? `${source} / ${audit}` : source;
    }).join('；');
  };
  const evidenceTargetId = (token, section) => {
    const value = String(token || '');
    const matches = [...document.querySelectorAll('.panel a.evidence-chip[data-evidence-token]')];
    const pageChip = matches.find((item) => item.dataset.evidenceToken === value);
    const panelNode = pageChip ? pageChip.closest('[data-panel]') : null;
    const target = panelNode ? panelNode.querySelector(`[data-section="${section}"]`) : null;
    if (target && target.id) return target.id;
    return selectedRefdes ? `${selectedRefdes}-${section}` : section;
  };
  const traceInputLabel = (tool, input) => {
    const payload = input || {};
    const parts = [];
    if (payload.refdes) parts.push(`位号：${payload.refdes}`);
    if (payload.net_name) parts.push(`网络：${payload.net_name}`);
    if (payload.query) parts.push(`查询：${payload.query}`);
    if (payload.limit) parts.push(`数量上限：${payload.limit}`);
    if (payload.top_k) parts.push(`候选片段：${payload.top_k}`);
    if (payload.candidate_limit) parts.push(`候选资料：${payload.candidate_limit}`);
    if (payload.neighbor_limit) parts.push(`邻接数量：${payload.neighbor_limit}`);
    if (payload.member_sample_limit) parts.push(`网络成员样例：${payload.member_sample_limit}`);
    if (payload.component_limit) parts.push(`器件样例：${payload.component_limit}`);
    if (payload.net_limit) parts.push(`网络样例：${payload.net_limit}`);
    if (payload.gap_limit) parts.push(`缺口样例：${payload.gap_limit}`);
    if (parts.length) return parts.join('；');
    if (tool === 'list_components') return '读取解析后的器件清单';
    if (tool === 'summarize_project_topology') return '汇总解析后的项目拓扑';
    return '无额外入参';
  };
  const evidenceHref = (token) => {
    const value = String(token || '');
    if (value.startsWith('http://') || value.startsWith('https://')) return value;
    if (value.startsWith('datasheet:')) {
      return `#${evidenceTargetId(value, 'evidence-details')}`;
    }
    if (value.startsWith('bom:') || value.startsWith('doc:')) return '#component-index';
    if (value.startsWith('sch:')) {
      return `#${evidenceTargetId(value, 'connection-path')}`;
    }
    return `#${evidenceTargetId(value, 'evidence-details')}`;
  };
  const evidenceTitle = (token) => {
    const value = String(token || '');
    if (value.startsWith('datasheet:')) return '数据手册页码来源 token；点击跳转并复制 token。';
    if (value.startsWith('bom:')) return 'BOM 行来源 token；点击跳转并复制 token。';
    if (value.startsWith('doc:')) return '本地公开资料索引 token；点击跳转并复制 token。';
    if (value.startsWith('sch:')) return '原理图拓扑来源 token；点击跳转并复制 token。';
    if (value.startsWith('http://') || value.startsWith('https://')) return '打开外部来源链接。';
    return '证据 token；点击复制。';
  };
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
    summary.textContent = `工具调用 / 证据 · ${trace.length}`;
    details.appendChild(summary);
    const traceField = (label, valueNode, sourceLabel = '') => {
      const field = document.createElement('div');
      field.className = 'ai-trace-field';
      const key = document.createElement('span');
      key.className = 'ai-trace-label';
      key.textContent = label;
      if (sourceLabel) key.title = sourceLabel;
      const value = document.createElement('div');
      value.className = 'ai-trace-value';
      if (typeof valueNode === 'string') {
        value.textContent = valueNode;
      } else {
        value.appendChild(valueNode);
      }
      field.appendChild(key);
      field.appendChild(value);
      return field;
    };
    const evidenceChips = (tokens) => {
      const wrap = document.createElement('span');
      const items = tokens || [];
      if (!items.length) {
        wrap.textContent = '-';
        return wrap;
      }
      items.forEach((token) => {
        const chip = document.createElement('a');
        chip.className = 'evidence-chip';
        chip.dataset.source = String(token).includes(':') ? String(token).split(':')[0] : 'source';
        chip.dataset.evidenceToken = String(token);
        chip.href = evidenceHref(token);
        chip.title = evidenceTitle(token);
        chip.textContent = String(token);
        wrap.appendChild(chip);
      });
      return wrap;
    };
    trace.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'ai-trace-row';
      const head = document.createElement('div');
      head.className = 'ai-trace-row-head';
      const title = document.createElement('strong');
      title.textContent = toolLabels[item.tool] || item.tool || '工具调用';
      if (item.tool) title.title = item.tool;
      const status = document.createElement('span');
      status.className = 'ai-trace-status';
      status.textContent = statusLabels[item.status] || item.status || '记录';
      head.appendChild(title);
      head.appendChild(status);
      row.appendChild(head);
      if (item.summary) {
        const traceSummary = document.createElement('p');
        traceSummary.className = 'ai-trace-summary';
        traceSummary.textContent = traceSummaryLabel(item.summary);
        row.appendChild(traceSummary);
      }
      const trust = item.trust_label || item.trust_tier || '-';
      row.appendChild(traceField('可信度', trustLabels[trust] || trust, '可信度'));
      row.appendChild(traceField('证据', evidenceChips(item.evidence), '证据 token'));
      row.appendChild(traceField(
        '证据来源分类',
        evidenceClassSummary(item.evidence_classification),
        '只说明证据来自本轮检索、已审 profile、资料索引或本地源审计；不是电气硬判定'
      ));
      row.appendChild(traceField('位号防护', String(item.wrapped || 0), '防护包裹次数'));
      const inputText = document.createElement('span');
      inputText.textContent = traceInputLabel(item.tool, item.input);
      inputText.title = JSON.stringify(item.input || {});
      row.appendChild(traceField('查询范围', inputText, '工具原始入参见悬停提示'));
      details.appendChild(row);
    });
    node.appendChild(details);
  };
  root.addEventListener('click', (event) => {
    const chip = event.target.closest('a.evidence-chip[data-evidence-token]');
    if (!chip) return;
    const token = chip.dataset.evidenceToken || chip.textContent || '';
    if (navigator.clipboard && token) navigator.clipboard.writeText(token).catch(() => {});
    const href = chip.getAttribute('href') || '';
    if (!href.startsWith('#')) return;
    event.preventDefault();
    const targetId = href.slice(1);
    const section = targetId.replace(/^[^-]+-/, '');
    let destination = null;
    if (targetId === 'component-index') {
      destination = document.getElementById('component-index');
    } else {
      destination = document.getElementById(targetId);
      const panel = selectedRefdes
        ? document.querySelector(`[data-panel="${selectedRefdes}"]`)
        : document.querySelector('.panel.active');
      destination = destination || (panel ? panel.querySelector(`[data-section="${section}"]`) : null);
    }
    if (destination) destination.scrollIntoView({block: 'start', behavior: 'smooth'});
  });
  const fallbackResponse = (question) => {
    const snapshots = config.snapshotResponses || {};
    if (snapshots[question]) return snapshots[question];
    if (/U999/i.test(question)) {
      const key = Object.keys(snapshots).find((item) => /U999/i.test(item));
      if (key) return snapshots[key];
    }
    return snapshots.__fallback__ || {
      answer: '这个静态快照只包含已审计的演示回答。',
      trace: [],
      suggestions: config.suggestions || []
    };
  };
  const ask = async (question) => {
    if (!question.trim()) return;
    open();
    addMessage('user', question);
    history.push({role: 'user', content: question});
    const pending = addMessage('assistant', 'Hardwise 正在核验证据...');
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
      response = {answer: `原理图检验工具对话失败：${error}`, trace: []};
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
