# 页面观察与单次动作

仅在 `browser-access` 已选择 WSL → Windows Chrome 适配器时读取。其他浏览器使用其实际提供的等价能力。以下表达式是只读观察与 Agent 已决定动作的实现参考，不是定时器或语义判断器。

## 复用公共入口

从当前加载的 `browser-access` 找到 `scripts/browser_cdp.py`，先用 `--help` 核对命令。全局 `--profile auto-gpt` 位于子命令之前，`--target <完整页面ID>` 位于子命令之后。

```text
uv run <browser-access脚本绝对路径> --profile auto-gpt status
uv run <browser-access脚本绝对路径> --profile auto-gpt tabs
uv run <browser-access脚本绝对路径> --profile auto-gpt eval --target <页面ID> --await-promise -
uv run <browser-access脚本绝对路径> --profile auto-gpt call --target <页面ID> <方法> --params <参数> --guard <条件表达式>
```

`eval -` 从标准输入读取表达式，聊天结果只返回 Agent 当前上下文，不重定向到文件。不重复实现调试连接、页面选择或键盘传输。缺少动作前复核能力时停止在发送之前；只请求补齐本技能必需能力，不无故更新其他技能。

## 先发现当前页面结构

首次接管和界面改变后，用 `inspect` 或只读 `eval` 确认页面结构。2026-10-12 的实际中文界面可见：

- 聊天正文位于 `main`，用户轮次有 `h4.sr-only` 的“你说：”；该标题祖父元素包含当前用户消息与对应回复。
- 输入框是 `main [contenteditable="true"][role="textbox"]`，空编辑器的 `innerText` 可能为换行，不能按字符串长度一判断已有草稿。
- 模型选择控件的 `aria-label` 是“选择 ChatGPT 模型”，当前模型读取该控件的可见文字，不查正文中的“Pro”。
- 生成／等待中存在 `aria-label="停止"` 的按钮；连接中断提示可能同时存在。
- 该版本没有 `[data-message-author-role]`，旧选择器返回空数组不证明没有回复。页面顶部还可能提示正在加载更早消息，不能把已渲染轮次当成全部历史。

以上只描述已观察版本。语言、结构或唯一性不同就重新勘察；不要强行套用这些选择器，更不要访问未文档化内部状态或刷新真实任务来修复选择器。

## 完整读取

通过 `eval` 读取需要的正文与原始长度，长内容分段返回。对同一轮次分段期间，核对页面地址和回复版本；正文变化后重新取稳定的一份，再决定动作。当前运行中的片段只作观察，不为了取得稳定文本停止生成。

对已确认的轮次容器，可以在一次只读表达式里返回其完整 `innerText`、长度和 SHA-256 摘要。摘要只用于机械地核对读取期间有没有变化，不能判断“有新回复”“已完成”或“应继续”。必要前文仍由 Agent 阅读；加载不全且影响判断时保留观察。

`scripts/reply-view.js` 提供只读 `replyView(options)`，可经公共 `eval --await-promise` 执行。Agent 先核验 `reply_selector`、`user_selector`、`model_selector` 指向当前回复、用户消息与模型；回复和模型必须唯一。默认完整返回可见回复，不截断。明确识别为界面控件的后代可用 `ui_selector` 排除；工具源代码或编码数据可用 `payload_selector` 单列长度和摘要，需要判断其结果时再设 `payload_text: true` 完整读取。两类范围重叠即拒绝。

排除范围必须由 Agent 在实际 DOM 核验；不能笼统排除所有按钮、状态提示、代码块或工具结果。语义相关内容和人工提示始终完整读取；不知道某块是什么时保留默认全文。回复版本包含完整回复、轮次、用户消息和机械载荷摘要，界面文字变化不改变版本，载荷变化仍会使版本改变。整个 `main` 或正文混合容器不能凭名称当作最新回复。选择器无匹配、多匹配或布局未知时只读调查，不自动降级到整页正文后发送。

## 不覆盖草稿的发送步骤

Agent 完成语义判断后，按 `browser-access` 获取真实焦点。普通 `type` 会选中并替换内容，不能用于本技能的并发输入场景；改用显式 `Input.insertText`，不会先删除任何文本。

优先用同版本的 `.sh` 单次入口，`read` 和 `continue` 共用已核验的选择器：

```sh
bash <auto-gpt目录>/scripts/auto_gpt.sh read \
  --browser-access-script <browser-access目录>/scripts/browser_cdp.py \
  --endpoint <已核验地址> --target <完整ID> --url <准确会话网址> \
  --reply-selector <唯一当前回复> --user-selector <全部用户消息正文> \
  --model-selector <唯一模型控件>
```

`read` 完整返回当前回复、用户最新消息、模型和版本；必要前文仍须经公共入口完整读取。`user-selector` 指向用户消息正文，不是“你说：”标题或整个混合轮次。只有已核验范围才添加 `--ui-selector` 或 `--payload-selector`，载荷全文按需添加 `--payload-text`。无法可靠定位最新回复或用户正文时，沿用只读调查，不强行使用此入口。

Agent 判断需要续接后，用相同参数把 `read` 改成 `continue`，再提供 `--expected-version <已完整读过的version>` 与 `--expected-model <已核验的完整模型文字>`。入口只执行这一次，核验专用实例后复用一个公共 `BrowserSession` 完成聚焦、坐标复核、插入、回车和发送确认；没有定时器、语义判断或重试。模型、回复、草稿、焦点、生成状态、附件或对话框变化即拒绝。重复会话标签页需要 Agent 先消歧，该入口不会擅自选一个继续。

结果只返回动作阶段、是否尝试插入／回车、是否确认新用户消息与控件事实；`confirmed` 要求用户消息数增加且最新正文严格为“继续”。`unconfirmed`、错误或工具超时都保留待确认记录，先回读，不再次调用。按键释放只释放已有尝试，不提交第二次。旧 `browser-access` 缺少 Python `call(..., guard=...)` 能力时停在动作之前，不通过省略保护降级；先用本地源码验证依赖，不为测试更新安装。

动作前条件应严格核对这些已观察事实：

1. 当前 `location.href` 仍等于本次已读页面地址，协议和主机名仍合格；
2. 会话、最新轮次和完整已读回复仍是本次判断所对应的一份；
3. 已确认的模型选择控件仍是本次核对过的非 Pro 模型；
4. 当前没有生成／等待证据；
5. 输入框唯一、启用、可编辑，且是 `document.activeElement`；
6. 插入前输入框为空；回车前其内容精确为本次“继续”，没有用户新增文字。

仅为空检查的表达式不能代替以上条件。按实际页面构造只读条件，可用 `crypto.subtle.digest` 在异步表达式中比对已读回复摘要；`call --guard` 支持等待 Promise，只接受布尔值 `true`。摘要或轮次不符时先重新观察，不自动修改条件让动作通过。

插入参数：

```json
{"text":"继续"}
```

回车通过 `Input.dispatchKeyEvent` 的真实事件完成，例如：

```json
{"type":"keyDown","key":"Enter","code":"Enter","windowsVirtualKeyCode":13,"text":"\r","unmodifiedText":"\r"}
```

随后发对应 `keyUp` 释放按键，不再插入文字。回读最新用户轮次与助手回复，以此确认提交。发送结果未确认时留在观察状态；不能按“输入框空了”自动重发，也不能点击重试、重新生成、跳过或停止来制造验收状态。

只读控件观察脚本按 [观察参考](control-monitor.md) 每分钟采样，发现变化后返回；它不采集此处用于判断的完整回复。一次 `call` 只执行 Agent 显式发起的一个方法，续接和错误暂停仍由 Agent 决定。

## 连接中断

出现“连接已中断，正在等待完整答复”时只等待自然恢复。恢复为发送／语音状态后，完整读取回复再判断；本技能不因该提示刷新，不点击重试或中止任务。
