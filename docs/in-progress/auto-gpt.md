# auto-gpt

`auto-gpt` 是专用可见 ChatGPT 浏览器的会话内监听技能。你在浏览器里发任务，只读脚本每分钟检查停止、发送／语音等控件。状态没有需要核对的变化时，Agent 等待事件；出现可能结束的变化后才读取完整回复，判断是否需要发送“继续”。它不会执行回复中的下载、文件或其他任务指令。

## 使用

- “启动 auto-gpt”：开始一次监听；专用配置中没有 ChatGPT 页面时打开首页。
- “停止 auto-gpt”：停止监听，保留浏览器和登录态，不中止网页中正在运行的任务。
- “恢复 auto-gpt 的某个错误暂停会话”：由 Agent 重新检查该会话并恢复；人工障碍解除后由 Agent 核对解除证据。

所有 ChatGPT 页面都在观察范围内，同一会话的多个标签页合并处理。任务正常完成后仍等待你发起新任务。非 ChatGPT 页面不参与；用户草稿、未确认发送、需要人工或状态不明确时，Agent 会退让。

## 执行边界

监听只在承载它的 Agent 会话持续运行时有效；会话结束后不作为后台服务继续。浏览器是可见窗口，没有另外的仪表板。默认浏览器配置保持原样，专用身份固定为 `auto-gpt`。

续接和暂停均由 Agent 判断并显式发起，不由脚本定时触发。脚本只读控件，不采集对话正文、不自动发送、不按失败次数暂停。控件状态仅在进程内存和 Agent 上下文传递，不保存本地文件。续接次数不限，连续三次真实失败也只是 Agent 的判断材料。

这种观察方式减少正文读取和模型判断次数；执行器若需要返回前台进程的运行状态，仍会产生少量工具调度 token。按钮只说明界面状态，Agent 仍需区分任务完成、时长中断和需要人工。每分钟采样不能保证捕获两次采样之间的所有短促变化。

“连接已中断，正在等待完整答复”可能与停止按钮并存。脚本识别状态提示后先连续观察 3 分钟；中间自行恢复或恢复发送状态就取消候选，仍持续才通知 Agent。脚本没有刷新逻辑。用户授权掉线恢复后，Agent 先读取完整回复、保护输入现场，再判断是否需要一次普通刷新；同一中断轮次不反复刷新，刷新后重新核对状态才考虑“继续”。

本技能不选择或使用 Pro 模型，不为了测试中止或反复刷新真实任务。机械输入会在执行前再次检查页面和草稿，并在发送后确认新消息；这不代表网站提供了人与 Agent 的互斥锁。

## 源码与验证

行为规则：[SKILL.md](../../in-progress/auto-gpt/SKILL.md)。适配器启动、事件和取消入口：[只读控件观察](../../in-progress/auto-gpt/references/control-monitor.md)；续接机械步骤：[页面观察与单次动作](../../in-progress/auto-gpt/references/browser-operations.md)。依赖通过标准 `skiloom-package.toml` 声明 `browser-access`。

当前属于 `in-progress` 技能；[适用验证记录](auto-gpt-validation.md)分别区分真实任务观察、确定性机械测试和当前 Agent 的场景审计，不把一种证据当作所有分支都已真实复现。

## 本地测试

测试直接读取当前仓库中的 `in-progress/auto-gpt/SKILL.md` 和 `productivity/browser-access/SKILL.md`，使用同一源码仓中的浏览器执行入口。不要把全局已安装的旧版本当成待测版本；本地测试不以推送 GitHub 或更新 Skiloom 安装为前提。

从本仓根目录核对已有专用窗口，不启动新窗口或发送消息：

```sh
uv run --no-project --offline productivity/browser-access/scripts/browser_cdp.py --profile auto-gpt status
```

浏览器机械测试也可以直接本地运行：

```sh
uv run --no-project --offline -m unittest discover -s productivity/browser-access/tests -p 'test_*.py'
```

控件观察的聚焦测试：

```sh
uv run --no-project --offline -m unittest discover -s in-progress/auto-gpt/tests -p 'test_*.py'
```

`--offline` 要求所需依赖已存在于本机缓存。真实页面观察与单次续接仍由读取上述两个本地技能的 Agent 执行，测试命令不会自动续接。
