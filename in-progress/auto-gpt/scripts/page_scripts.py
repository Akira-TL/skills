"""共享只读页面表达式，保证采样和发送确认使用同一消息身份规则。"""
from pathlib import Path

DIRECTORY = Path(__file__).parent
IDENTITY = (DIRECTORY / 'message-identity.js').read_text(encoding='utf-8')
PROBE = '(() => {\n' + IDENTITY + '\nreturn ' + (DIRECTORY / 'observe-controls.js').read_text(encoding='utf-8').rstrip().removesuffix(';') + ';\n})()'
VIEW = IDENTITY + '\n' + (DIRECTORY / 'reply-view.js').read_text(encoding='utf-8')
LOCATOR = '(() => {\n' + VIEW + '\nreturn (\n' + (DIRECTORY / 'resolve-layout.js').read_text(encoding='utf-8') + '\n);\n})()'
