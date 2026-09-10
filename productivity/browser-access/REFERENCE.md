# Browser Access 实现参考

本文件保存 `browser-access` 的低层实现细节。通用路由、Browser Grant 和 Profile 规则位于 `SKILL.md`；只有当前选择了 WSL → Windows Chrome CDP adapter、需要直接调用 CDP、检查动态 DOM、解析网络资源或处理跨系统上传时才读取本文。

这里的 Windows Chrome 路径是一个 adapter，不是浏览器选择的默认起点。调用方必须先按 `SKILL.md` 完成 capability discovery；harness 原生浏览器已经满足需求时不读取或套用本 adapter。

## 0. 确定性命令行界面（Command-Line Interface, CLI）：默认控制入口

选中本 adapter 后，任务级浏览器操作统一优先使用本 Skill 目录下的 `scripts/browser_cdp.py`。脚本使用 PEP 723 声明运行依赖，应通过 `uv run <absolute-script-path> ...` 调用；完整命令和参数以 `--help` 为准。

它把高频能力固定为同一个控制面：`status` / `ensure` 处理生命周期，`tabs` 发现 page target，`open` / `navigate` / `focus` 管理页面，`text` / `inspect` 完成勘察，`click` / `fill` / `wait` / `upload` 完成交互，`eval` 承载页面特定 JavaScript，`call` 承载任意单次 CDP 方法，`network` 捕获请求与响应元数据。

除 `status` 外，命令在 CDP 不可达时会尝试以固定 `agent-browser` Profile 启动 Windows Chrome。存在多个真实 `type=page` target 且没有唯一选择时，脚本会直接拒绝继续，并要求通过 `--target` 使用 target ID、标题或 URL 的唯一片段选择页面。

`inspect` 默认只回传可见控件和文件控件，同时报告页面控件总数；需要隐藏控件时再使用其显式选项。`click` 默认拒绝关联表单的 HTML 提交控件，只有已经满足 `SKILL.md` 的提交授权边界时才使用对应显式放行参数。

`eval`、`call` 与 `network` 是低层逃生口。任务中应组合这些入口，而不是重新编写 Python/WebSocket/CDP 包装代码；下面的原始协议片段只用于理解或维护这个 CLI。

## 1. Adapter：Windows Chrome 持久实例模式

默认控制面固定为：

```text
CDP: http://localhost:9222
Profile identity: agent-browser
Profile directory: %USERPROFILE%\.agent-browser\profile
```

任务级检查与启动由 CLI 的 `status` / `ensure` 负责。下面的原始探针只用于 adapter 自身排障：

```bash
curl -fsS http://localhost:9222/json/version
```

探针成功时复用现有实例，不再启动 Chrome。只有 CDP 不可达时，才探测 Chrome 的实际路径。常见位置包括：

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
```

从 WSL 调用时，对应路径通常位于 `/mnt/c/Program Files/...`。

使用固定的持久专用 Profile：

```powershell
$agentProfile = Join-Path $env:USERPROFILE ".agent-browser\profile"

Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList @(
  "--remote-debugging-address=127.0.0.1",
  "--remote-debugging-port=9222",
  "--user-data-dir=$agentProfile",
  "https://example.com"
)
```

这个目录不是临时目录。首次登录飞书、问卷平台或其他站点后，Cookie 和站点登录态留在该 Profile 中，后续 CDP 会话继续复用。浏览器被关闭后也应使用同一路径重新启动，不能换新目录。

不要对用户默认 Chrome Profile 直接开放 CDP。现代 Chrome 也会限制对默认数据目录使用远程调试参数，因此专用 `--user-data-dir` 同时是安全和兼容性要求。

## 2. 从 WSL 发现并复用 CDP

任务中先用 CLI 的 `tabs`；它会过滤 extension、service worker 等非 page target，并在需要时复用或恢复同一个 Agent Chrome。排查 CLI 本身时才直接查看：

```bash
curl -fsS http://localhost:9222/json/version
curl -fsS http://localhost:9222/json/list
```

第一条命令也是生命周期探针：成功则复用现有 Agent Chrome；失败才启动同一专用 Profile。不要把“建立新 WebSocket 连接”和“启动新浏览器”混为一件事，前者可以按页面目标重新建立，后者只在浏览器实例不存在时发生。

`/json/version` 应包含：

```text
Browser
Protocol-Version
webSocketDebuggerUrl
```

`/json/list` 中寻找：

```text
type: page
url: 目标网址
webSocketDebuggerUrl: ws://127.0.0.1:9222/devtools/page/...
```

如果存在浏览器扩展 background page、service worker、omnibox popup，不要误把它们当成目标标签页。优先匹配已有目标 URL 或标题；没有目标页时，在当前 Agent Chrome 实例中导航或打开新标签页，不再创建另一套 Profile/Chrome 实例。

## 3. CDP 低层逃生口

页面特定 JavaScript 通过 CLI 的 `eval` 执行；没有专用子命令的单次 CDP 方法通过 `call` 执行。因此普通任务不直接建立 `websocket-client` 连接。

维护 CLI 或诊断协议问题时，CDP 消息的基本结构仍是：

```json
{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}
```

常见方法包括：

```text
Runtime.enable
Runtime.evaluate
Page.enable
Page.navigate
DOM.enable
DOM.getDocument
DOM.querySelector
DOM.setFileInputFiles
```

CLI 已负责 message id、事件与 response 的区分、JavaScript exception、target WebSocket 选择和连接生命周期。不要在普通浏览任务里再次实现这些机制。

## 4. 网络资源与 Artifact Request 解析

浏览器需要为上层任务解析 PDF、数据文件或其他资源时，先从页面静态状态寻找真实资源地址，再使用网络观察；不要一开始就模拟下载。

优先通过 `inspect` / `eval` 检查 `a[href]`、`iframe[src]`、`embed[src]`、`object[data]`、页面 meta/JSON state 等是否已经暴露目标 URL。若 URL 只有点击、脚本执行或重定向后才出现，优先用 CLI 的 `network` 在触发动作之前启用 CDP `Network` 域并捕获请求/响应；只有维护 CLI 时才直接处理 `Network.requestWillBeSent`、`Network.responseReceived` 等原始事件。

对候选请求至少核对 URL、method、响应 `Content-Type`、`Content-Disposition`、redirect chain 和当前页面 referer。需要认证时，只提取重放目标 artifact 所需的最小临时请求上下文；Cookie、Authorization、signed token 等不得写入项目文件或长期缓存。

上层需要直接传输时，返回类似以下临时 `Artifact Request`：

```text
url
method
headers
referer
session_context
content_type
suggested_filename
expires_at
```

能在普通 HTTP 客户端重放时，由调用方直接传输。如果资源与浏览器会话强绑定，优先在已授权页面上下文执行 `fetch` 并返回响应体，或在响应仍可读取时使用 `Network.getResponseBody`。浏览器默认 Downloads 目录不是资源解析的完成条件。

## 5. 页面勘察表达式

普通勘察先使用 CLI 的 `inspect`；只需要正文时使用 `text`。下面表达式用于 `eval` 的站点特定补充，不应再包装成独立脚本。

读取可见正文：

```javascript
document.body.innerText
```

枚举表单控件：

```javascript
[...document.querySelectorAll('input, textarea, select, button')].map((el, i) => ({
  i,
  tag: el.tagName,
  type: el.type || '',
  id: el.id || '',
  name: el.name || '',
  value: el.value || '',
  placeholder: el.placeholder || '',
  readonly: !!el.readOnly,
  checked: !!el.checked,
  multiple: !!el.multiple,
  accept: el.accept || ''
}))
```

检查题目容器是否显示：

```javascript
[...document.querySelectorAll('[id^="div"]')].map(el => ({
  id: el.id,
  display: getComputedStyle(el).display,
  visibility: getComputedStyle(el).visibility,
  text: el.innerText.slice(0, 200)
}))
```

不要依赖某个站点一定使用 `div1`、`q1` 这类命名；先观察再建立当前页面映射。

## 6. 填写普通输入框

普通文本框、`textarea`、`select` 和 `contenteditable` 优先使用 CLI 的 `fill`，它会走原生 setter 并触发 `input` / `change`。只有站点组件需要额外逻辑时才通过 `eval` 补充。

需要让页面监听到变更时，不只设置 `value`，还要触发事件：

```javascript
const el = document.querySelector('#q1');
el.focus();
el.value = '示例';
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
el.blur();
```

如果框架重写了原生 setter，可以调用 `HTMLInputElement.prototype` 上的 setter，再派发事件。

## 7. 单选和条件题

普通点击优先使用 CLI 的 `click`，交互后再使用 `inspect` 或 `wait` 重新确认条件题状态。需要点击包装元素或执行站点特定逻辑时使用 `eval`。

优先让页面自己的点击逻辑生效：

```javascript
document.querySelector('#q2_1')?.click();
```

如果真实 `input` 被隐藏而点击绑定在包装元素上，应点击站点实际监听的 label、anchor 或 wrapper。点击后重新读取后续题目的 `display` 状态。

不要一次性给所有隐藏题写值再假定页面会接受；条件题应按真实交互顺序展开。

## 8. 日期控件

对只读日期输入框，首选点击页面日期选择器。如果必须直接设置，应在设置后验证站点是否接受：

```javascript
const el = document.querySelector('#date');
el.removeAttribute('readonly');
el.value = '2026-08-07';
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

不要把这一方式当作默认做法。不同站点可能把真实值保存在隐藏字段或框架状态中。

## 9. 文件上传与跨系统路径

优先使用 CLI 的 `upload`。在 WSL 下传入存在的 Linux 路径时，脚本会在需要时转换为 Windows Chrome 可访问路径；也可以直接传入明确的 Windows 路径。

先通过 `inspect` 或必要的 `eval` 确认 `input[type=file]` 是否存在，以及：

```javascript
[...document.querySelectorAll('input[type=file]')].map(el => ({
  id: el.id,
  multiple: el.multiple,
  accept: el.accept
}))
```

如果使用 `DOM.setFileInputFiles`，文件路径由浏览器进程解析。因此 Windows Chrome 需要 Windows 可访问路径，例如：

```text
C:\Users\Akira\Downloads\evidence.zip
```

不是：

```text
/home/Akira/Downloads/evidence.zip
```

如果页面只允许上传一个文件，而凭证有多个，优先按主办方要求打包，不要尝试多次覆盖同一个单文件上传框。

## 10. 文件按时间定位

当用户只记得“几个文件挨得比较近”时，可以先按修改时间列出下载目录，再由文件名、时间和大小交叉确认。

PowerShell 示例：

```powershell
Get-ChildItem "$env:USERPROFILE\Downloads" |
  Sort-Object LastWriteTime -Descending |
  Select-Object LastWriteTime, Length, Name
```

不要只凭“最近的 PDF”自动上传，尤其在报销、合同、身份材料等场景。至少核对文件名和时间，必要时让用户确认。

## 11. 表单完成后的机器校验

先通过 `inspect` 回读当前页面；需要把多个站点特定字段组合成一次结构化校验时，通过 `eval` 返回对象，不再创建一次性 WebSocket 脚本。

最终检查可以返回一组结构化状态，例如：

```javascript
({
  name: document.querySelector('#q1')?.value,
  outboundAmount: document.querySelector('#q5')?.value,
  returnAmount: document.querySelector('#q9')?.value,
  cityTransport: document.querySelector('input[name="q11"]:checked')?.value,
  uploadMessage: document.querySelector('.uploadmsg')?.innerText || '',
  href: location.href
})
```

实际字段名必须来自当前页面勘察结果。

## 12. 事故预防

自动填写阶段不要执行以下行为：

```text
点击“提交”按钮
调用 form.submit()
调用站点自定义提交函数
在提交按钮获得焦点时发送 Enter
为了测试流程而真的提交一次再回退
```

如果用户要求“先不要提交”，最可靠的验收证据是：关键字段值已经填好、页面 URL 仍是填写页、提交按钮未触发、用户能在可视化 Chrome 中直接检查。CLI 的 `click` 还会对 HTML submit-like 控件增加机械拒绝；只有已经获得提交授权时才显式放行。

## 13. 登录态与任务结束

首次进入需要认证的网站时，由用户在专用 Agent Chrome 内完成登录。登录后保留该浏览器和 Profile，单次任务完成只断开自动化操作，不清除 Cookie、不删除 Profile，也不因为“任务结束”主动关闭专用浏览器。

如果网站自己让会话过期、撤销设备登录或要求二次认证，才再次让用户处理登录；这属于站点认证生命周期，不应通过创建新 Profile 解决。

## 14. 本次问卷星实践得到的经验

在问卷星类动态问卷中，页面初始只显示顶层问题；选择“有”后，后续日期、交通工具、金额和发票号才会显示。实际操作应先点击上游单选，再读取新出现的 DOM。

上传控件的视觉文案可能显示“选择文件”，但真正约束需要结合 `input[type=file]` 属性和页面错误提示判断。本次页面在尝试多文件时明确提示“上传文件数量不能超过1个”，因此自动化应停止覆盖上传区，改由用户整理单一凭证包或手动上传。

对于“1,064 元是两个人一起买、本人只报销 532 元”这类情况，表单中的报销金额必须使用本人应报销金额，而不是支付记录中的整单金额。原始支付记录、个人车票金额和说明文件应三者一致。
