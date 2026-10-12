(() => {
  const visible = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  const count = selector => [...document.querySelectorAll(selector)].filter(visible).length;
  const editors = [...document.querySelectorAll('main [contenteditable="true"][role="textbox"],main textarea')].filter(visible);
  const headings = [...document.querySelectorAll('main h4.sr-only')];
  const turns = headings.filter(el => ['你说：', 'You said:'].includes(el.textContent.trim()));
  const connectionLost = [...document.querySelectorAll('main [role="status"] .text-chatgpt-recovery')]
    .filter(visible).some(el => /^连接已中断[，,]正在等待完整答复[。.…]*$/.test(el.textContent.trim().replace(/\s/g, '')));
  return {
    stop: count('button[aria-label="停止"],button[aria-label="Stop"],button[aria-label="Stop generating"],button[data-testid="stop-button"]'),
    composer: count('button[aria-label="发送"],button[aria-label="发送消息"],button[aria-label="Send prompt"],button[data-testid="send-button"],button[aria-label="开始语音"],button[aria-label="Start voice mode"],button[data-testid="composer-speech-button"]'),
    editors: editors.length,
    draft: editors.some(el => (el.value ?? el.textContent ?? '').trim().length > 0),
    alerts: count('[role="alert"]'),
    dialogs: count('[role="dialog"]'),
    turns: turns.length,
    latest_turn: turns.at(-1)?.closest('[data-turn-id],[data-message-id],article[id]')?.getAttribute('data-turn-id')
      || turns.at(-1)?.closest('[data-message-id]')?.getAttribute('data-message-id')
      || turns.at(-1)?.closest('article[id]')?.id || '',
    connection_lost: connectionLost
  };
})()
