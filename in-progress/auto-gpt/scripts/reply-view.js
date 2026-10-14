// 只读：选择器必须先由 Agent 在实际页面核验，不猜测消息或工具区域。
function viewVisible(el) {
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') return false;
    if (el.getClientRects().length > 0) return true;
    if (style.display !== 'contents') return false;
    return [...el.childNodes].some(node => {
      if (node instanceof Element) return viewVisible(node);
      if (node.nodeType !== Node.TEXT_NODE || !node.textContent.trim()) return false;
      const range = document.createRange(); range.selectNode(node);
      return range.getClientRects().length > 0;
    });
}

function userView(options) {
  const nodes = [...document.querySelectorAll(options.user_selector)].filter(viewVisible);
  return {user_count: nodes.length, latest_user: nodes.at(-1)?.innerText.trim() || ''};
}

async function replyView(options) {
  const fail = (error_code, message) => {
    throw new Error('BROWSER_ERROR:' + JSON.stringify({error_code, message}));
  };
  const visible = viewVisible;
  const all = selector => [...document.querySelectorAll(selector)].filter(visible);
  const unique = selector => {
    const nodes = all(selector);
    if (nodes.length !== 1) fail(nodes.length ? 'ELEMENT_AMBIGUOUS' : 'ELEMENT_NOT_FOUND',
                               'Expected one visible reply or model element');
    return nodes[0];
  };
  const digest = async text => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)))]
    .map(n => n.toString(16).padStart(2, '0')).join('');
  const reply = unique(options.reply_selector);
  const model = unique(options.model_selector).innerText.trim();
  const editors = all('main [contenteditable="true"][role="textbox"],main textarea');
  const editor = editors.length === 1 ? editors[0] : null;
  const ui = options.ui_selector ? [...reply.querySelectorAll(options.ui_selector)] : [];
  const payloadNodes = options.payload_selector ? [...reply.querySelectorAll(options.payload_selector)] : [];
  if (options.encoded_text) {
    // 仅单独的长编码文本节点；含解释、错误或指令的节点保持全文。
    const walker = document.createTreeWalker(reply, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const text = node.textContent.trim();
      if (text.length >= 512 && text.length % 4 === 0 && /^[A-Za-z0-9+/]+={0,2}$/.test(text)
          && visible(node.parentElement) && !payloadNodes.some(el => el.contains(node))) payloadNodes.push(node);
    }
  }
  if (ui.some(el => payloadNodes.some(node => el.contains(node) || node.contains(el))))
    fail('INVALID_ARGUMENT', 'UI and payload scopes overlap');
  const payloads = await Promise.all(payloadNodes.map(async (el, index) => {
    const text = el.nodeType === Node.TEXT_NODE ? el.textContent : el.innerText;
    return {index, length: text.length, sha: await digest(text), ...(options.payload_text ? {text} : {})};
  }));
  // 按实际可见 DOM 顺序保留文字，去除已核验的界面控件，单列机械载荷。
  const render = node => {
    if (payloadNodes.includes(node)) return '\n[机械载荷 ' + payloadNodes.indexOf(node) + ']\n';
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    if (!(node instanceof Element)) return '';
    const style = getComputedStyle(node);
    // display:contents 自身没有矩形，其子节点仍可见；显式换行保留语句边界。
    if (style.visibility === 'hidden' || (style.display !== 'contents' && !visible(node))) return '';
    if (ui.includes(node)) return '';
    if (payloadNodes.includes(node)) return '\n[机械载荷 ' + payloadNodes.indexOf(node) + ']\n';
    if (node.tagName === 'BR') return '\n';
    const text = [...node.childNodes].map(render).join('');
    const block = /^(block|flex|grid|list-item|table)/.test(style.display);
    return block ? '\n' + text + '\n' : text;
  };
  const text = render(reply).replace(/\n{3,}/g, '\n\n').trim();
  const userNodes = all(options.user_selector);
  const latestUser = userNodes.at(-1)?.innerText.trim() || '';
  const replyId = reply.getAttribute('data-message-id') || reply.getAttribute('data-turn-id') || reply.id || '';
  const version = await digest(JSON.stringify({text, replyId,
    payloads: payloads.map(({index,length,sha}) => ({index,length,sha})), users: userNodes.length, latestUser}));
  const rect = editor?.getBoundingClientRect();
  const x = rect ? rect.x + rect.width / 2 : null;
  const y = rect ? rect.y + rect.height / 2 : null;
  const hit = rect ? document.elementFromPoint(x, y) : null;
  return {url: location.href, text, length: text.length, version, reply_id: replyId, model,
    user_count: userNodes.length, latest_user: latestUser, payloads, omitted_ui: ui.length,
    editor_count: editors.length, draft: editor ? (editor.value ?? editor.innerText).trim() : null,
    editable: !!editor && !editor.disabled && !editor.readOnly,
    focused: !!editor && (document.activeElement === editor || editor.contains(document.activeElement)),
    point: rect && rect.width > 0 && rect.height > 0 && (hit === editor || editor.contains(hit)) ? {x,y} : null,
    stop: all('button[aria-label="停止"],button[aria-label="Stop"],button[aria-label="Stop generating"],button[data-testid="stop-button"]').length,
    dialogs: all('[role="dialog"]').length,
    attachments: all('[data-testid="attachment"],button[aria-label^="删除附件"],button[aria-label^="Remove attachment"]').length,
    connection_lost: all('main [role="status"] .text-chatgpt-recovery')
      .some(el => /^连接已中断[，,]正在等待完整答复[。.…]*$/.test(el.textContent.trim().replace(/\s/g, '')))};
}
