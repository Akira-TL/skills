// 只使用页面公开的消息身份；虚拟列表序号和正文不能充当消息 ID。
function messageIdentity(node) {
  for (const attribute of ['data-message-id', 'data-chatgpt-search-message-ids', 'data-turn-id', 'data-turn-key']) {
    const owner = node?.closest('[' + attribute + ']');
    const value = owner?.getAttribute(attribute)?.trim();
    if (value) return attribute + ':' + value;
  }
  return node?.closest('article[id]')?.id || '';
}
