// 只读：仅识别已在专用浏览器核验的布局；未知结构拒绝自动扩大读取范围。
(() => {
  const fail = () => { throw new Error('BROWSER_ERROR:' + JSON.stringify({
    error_code: 'AUTO_GPT_LAYOUT_UNKNOWN', message: 'Known latest-turn layout is unavailable; inspect explicit selectors'
  })); };
  const userSelector = 'main [class~="group/user-message"]:not(:has([class~="group/user-message"]))';
  const users = [...document.querySelectorAll(userSelector)].filter(viewVisible);
  const user = users.at(-1);
  const root = user?.closest('[data-turn-key]');
  const block = user?.closest('.block-BQZwFn');
  if (!root || !messageIdentity(user) || !block || !root.contains(block)) return fail();
  const key = root.getAttribute('data-turn-key');
  if (!key) return fail();
  const candidates = [...block.parentElement.children].filter(el =>
    el !== block && el.querySelector('[data-chatgpt-agent-turn-start]') && !el.contains(user));
  if (candidates.length !== 1 || !viewVisible(candidates[0])) return fail();
  const path = [];
  let node = candidates[0];
  while (node !== root) {
    if (!node.parentElement || !root.contains(node)) return fail();
    path.unshift(':nth-child(' + ([...node.parentElement.children].indexOf(node) + 1) + ')');
    node = node.parentElement;
  }
  const replySelector = 'main [data-turn-key="' + CSS.escape(key) + '"] > ' + path.join(' > ');
  const modelSelector = 'button[aria-label="选择 ChatGPT 模型"]';
  const replies = [...document.querySelectorAll(replySelector)].filter(viewVisible);
  const models = [...document.querySelectorAll(modelSelector)].filter(viewVisible);
  if (replies.length !== 1 || replies[0] !== candidates[0] || models.length !== 1) return fail();
  return {reply_selector: replySelector, user_selector: userSelector, model_selector: modelSelector};
})()
