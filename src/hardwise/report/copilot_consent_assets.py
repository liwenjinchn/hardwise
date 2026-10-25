"""Disclosure gate for the legacy panel; the SPA has its own page-memory controller."""

COPILOT_CONSENT_SCRIPT = """
  const disclosureBox = root.querySelector('[data-ai-disclosure]');
  let confirmedDisclosure = null;
  let disclosedContext = null;
  const loadDisclosure = async () => {
    const res = await fetch('/api/workbench/ai-disclosure');
    if (!res.ok) throw new Error('无法取得 AI 发送说明，未发送问题。');
    const data = await res.json();
    if (disclosedContext && data.context_id !== disclosedContext) {
      history.length = 0;
      stream.replaceChildren();
    }
    disclosedContext = data.context_id;
    if (confirmedDisclosure !== data.disclosure_id) confirmedDisclosure = null;
    disclosureBox.replaceChildren();
    const heading = document.createElement('strong');
    heading.textContent = data.mode === 'real' ? 'AI 发送前确认 · 当前页面有效' : 'AI 模式与发送边界';
    disclosureBox.appendChild(heading);
    const lines = data.mode === 'real'
      ? ['配置接收地址：' + (data.destination || '不可用'), '模型标识：' + (data.model || '不可用'), ...(data.data_categories || []), data.notice]
      : [data.notice];
    lines.forEach(text => { const line = document.createElement('p'); line.textContent = text; disclosureBox.appendChild(line); });
    if (data.mode === 'real' && data.available) {
      const label = document.createElement('label');
      const checkbox = document.createElement('input'); checkbox.type = 'checkbox';
      checkbox.checked = confirmedDisclosure === data.disclosure_id;
      checkbox.addEventListener('change', () => { confirmedDisclosure = checkbox.checked ? data.disclosure_id : null; });
      label.append(checkbox, document.createTextNode('我已了解，允许本页面将上述内容发往该服务'));
      disclosureBox.appendChild(label);
      const hint = document.createElement('p'); hint.textContent = '刷新、切换项目或接收配置变化后需重新确认；不会自动发送问题。'; disclosureBox.appendChild(hint);
    }
    return data;
  };
  const prepareAISend = async () => {
    if (config.mode !== 'live') return {allowed: true};
    try {
      const data = await loadDisclosure();
      return {allowed: data.available && (data.mode !== 'real' || confirmedDisclosure === data.disclosure_id), receipt: data.disclosure_id};
    } catch (_) {
      disclosureBox.textContent = '无法取得 AI 发送说明，未发送问题。请刷新页面后重试。';
      return {allowed: false};
    }
  };
  if (config.mode === 'live') loadDisclosure().catch(() => { disclosureBox.textContent = '尚未取得发送说明，暂不发送。'; });
  else disclosureBox.textContent = '离线审计快照，不调用云模型。';
"""
