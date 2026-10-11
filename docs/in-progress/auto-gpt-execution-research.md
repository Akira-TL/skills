# auto-gpt 专用浏览器与持续监听的执行能力调查

调查日期：2026-10-12。对应决策：[auto-gpt：专用可见浏览器与一分钟监听的执行能力](https://github.com/Akira-TL/akira-lattice/issues/2)。本文只记录执行能力与限制，不包含真实聊天、账号或认证资料。

## 调查范围

确认现有 `browser-access` 与本会话的实际工具是否足以承载：专用可见窗口、持久登录配置、每分钟一轮的 Agent 观察，以及显式启停。页面是否需要续接属于后续语义判断，不由本调查中的脚本决定。

## 可核验事实

| 能力 | 当前证据 | 限制 |
| --- | --- | --- |
| 专用持久配置 | `browser-access` 的 `profile-save`、`--profile` 与 `profiles.toml` 契约；实际配置身份为 `auto-gpt`，默认仍为 `agent-browser` | 配置名称不表示已经登录，也不代表可以控制其他配置 |
| 可见浏览器 | 当前通过该适配器启动 Windows Chrome，`ensure` 返回 `reused: false`、`connected: true`、`profileVerified: true`；已打开 ChatGPT 页面 | 启动窗口与开始监听是两个动作，当前尚未开始监听 |
| 配置隔离 | 本机端口所有者、Chrome 参数及调试实例标识核验；默认端口与默认目录仍被保留 | 核验失败时拒绝页面动作，不回退到默认浏览器 |
| 页面发现与读取 | 公共入口提供 `tabs`、`text`、`inspect`、`eval`；`tabs` 筛选页面目标 | `text` 会报告 `length` 和 `truncated`，不能把截断结果当作完整回复 |
| 显式页面动作 | 公共入口提供 `click`、`type`、`call`；通用调试方法可以发送真实键盘事件 | `type` 会替换现有文本，不适合直接用于可能被用户同时编辑的输入框 |
| 等待与中断 | 本会话提供 `clock.sleep`，允许一分钟等待并在新用户输入到达时提前结束；也有当前时刻读取工具 | 这是当前执行器的实际能力，不是所有 Agent 的共同接口 |
| 会话外定时执行 | 当前暴露的工具中没有 `automation_update` | 本技能不能承诺 Agent 会话结束后继续监听 |

脚本证据：[生命周期与配置核验](../../productivity/browser-access/scripts/browser_cdp_lifecycle.py)、[Windows 实例核验](../../productivity/browser-access/scripts/browser_cdp_windows.py)、[公共命令入口](../../productivity/browser-access/scripts/browser_cdp.py)、[运行规则](../../productivity/browser-access/SKILL.md)。

## 启动调查中暴露的兼容性限制

首次选择的 `9223` 在本机 Windows 的排除端口范围内。实际回环绑定返回访问权限错误；改选端口前另行验证绑定能力。该事实说明“没有监听进程”不能证明端口可用，不能把示例中的任一端口写成所有机器的固定选择。启动层已经增加绑定预检，两种回环地址都不可用时在打开窗口前报错。[Chromium 调试服务器源码](https://chromium.googlesource.com/chromium/src/+/HEAD/chrome/browser/devtools/remote_debugging_server.cc)

旧版自定义实例依赖 `Browser.getBrowserCommandLine` 核验，该方法要求 `--enable-automation`；新窗口因此与原默认实例的启动参数不同。用户手动登录遇到 Google 的“不安全浏览器”提示，不能据此证明某一个参数是唯一原因。Google 官方将自动化控制的浏览器列为可能拒绝登录的情况。[Chrome 调试协议](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Browser.pdl)、[Google 官方登录说明](https://support.google.com/accounts/answer/7675428?co=GENIE.Platform%3DDesktop&hl=en)

本地配置现已改为核验 Windows 上调试端口的 Chrome 进程和实际调试实例，不再为核验强制添加该参数。Windows 命令行采用系统解析函数，带空格与单引号的目录、重复身份参数、多个端口所有者和实例不匹配都有定向测试；真实默认实例也完成了只读读取验证。认证仍由用户按网站支持的方式完成，启动参数调整不保证认证成功。[Windows 端口所有者查询](https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-nettcpconnection)、[Windows 命令行解析](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-commandlinetoargvw)

Chrome 136 起，对标准用户数据目录的远程调试有额外限制。本技能使用独立专用目录，不管理或复制日常 Chrome 配置。[Chrome 官方说明](https://developer.chrome.com/blog/remote-debugging-port)

## 对后续规格的建议

- 保存配置只建立浏览器身份；打开窗口只为用户提供人工操作入口；收到明确启动指令才进入监听。
- 监听由当前 Agent 发起每轮观察、判断与动作。等待工具只负责等待，页面脚本只负责事实读取或已决定的机械操作。
- 每轮重新发现专用配置下的页面，以真实 URL 的协议和主机名筛选 ChatGPT。首次启动没有目标页面时打开 ChatGPT 首页；监听中没有目标页面时继续低频等待。
- “停止 auto-gpt”先撤销后续观察与发送，再结束监听；保留窗口、数据目录和登录态。关闭浏览器是另外的明确操作。
- 会话结束就是本次监听的执行边界。恢复需重新启动，不通过后台发送脚本补偿。
- 正常任务完成只让对应会话回到等待用户新消息；人工障碍、发送不确定与错误暂停分别记录在当前 Agent 上下文中。

## 尚未验证

真实 ChatGPT 的生成、中断、错误和人工状态需要实际页面证据；不能用本次窗口启动成功证明这些状态已经可靠识别。用户仍在手动认证阶段，调查尚未读取登录表单、凭据或聊天正文，也没有发送初始任务或“继续”。
