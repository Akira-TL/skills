# Browser Access 实现参考

本文件保存 `browser-access` 的低层实现细节。通用路由、Browser Grant 和 Profile 规则位于 `SKILL.md`；只有当前选择了 WSL → Windows Chrome CDP adapter、需要直接调用 CDP、检查动态 DOM、解析网络资源或处理跨系统上传时才读取本文。

这里的 Windows Chrome 路径是一个 adapter，不是浏览器选择的默认起点。调用方必须先按 `SKILL.md` 完成 capability discovery；harness 原生浏览器已经满足需求时不读取或套用本 adapter。

## 0. 确定性命令行界面（Command-Line Interface, CLI）：默认控制入口

选中本 adapter 后，任务级浏览器操作统一优先使用本 Skill 目录下的 `scripts/browser_cdp.py`。脚本使用 PEP 723 声明运行依赖，应通过 `uv run <absolute-script-path> ...` 调用；完整命令和参数以 `--help` 为准。

它把高频能力固定为同一个控制面：`status` / `ensure` 处理生命周期，`tabs` 发现 page target，`open` / `navigate` / `focus` 管理页面，`text` / `inspect` 完成勘察，`click` / `type` / `fill` / `wait` / `upload` 完成交互，`eval` 承载页面特定 JavaScript，`call` 承载任意单次 CDP 方法，`network` 捕获请求与响应元数据。

除 `status` 外，命令在 CDP 不可达时会尝试恢复选定的专用配置。未提供配置参数时仍使用原有 `agent-browser`；仅指定其他 `--endpoint` 而未提供专用目录时，只连接已运行实例，不在新端口启动默认目录。存在多个真实 `type=page` target 且没有唯一选择时，脚本会直接拒绝继续，并要求通过 `--target` 使用 target ID、标题或 URL 的唯一片段选择页面。

`inspect` 默认只回传可见控件和文件控件，同时报告页面控件总数；需要隐藏控件时再使用其显式选项。`click` 会先滚动并验证 `elementFromPoint` 命中目标，再通过 `Input.dispatchMouseEvent` 发出真实指针事件；它默认拒绝关联表单的 HTML 提交控件，只有已经满足 `SKILL.md` 的提交授权边界时才使用对应显式放行参数。`type` 复用同一真实点击取得焦点，再以 `Input.dispatchKeyEvent` 选择/清除现有文本并用 `Input.insertText` 输入。

`eval`、`call` 与 `network` 是低层逃生口。任务中应组合这些入口，而不是重新编写 Python/WebSocket/CDP 包装代码；下面的原始协议片段只用于理解或维护这个 CLI。

## 1. Adapter：Windows Chrome 持久实例模式

### 页面长连接与目标锁定

连续操作可运行 `uv run <script-path> session --target <完整ID> --expected-url <准确网址>`，每行输入 `{"id":1,"op":"inspect"}`，每行输出 `{"id":1,"ok":true,"result":...}`。命令错误保留原 ID 并返回统一错误对象；损坏请求的 ID 无法读取时为 `null`。结束标准输入即断开连接，保留浏览器。基础操作包括 `inspect`、`text`、`title`、`eval`、`call`；参数使用对应命令的下划线名称，不读取标准输入表达式。

也可导入同目录 `browser_session.BrowserSession`，在上下文管理器内调用 `execute(op, **options)`、`evaluate` 或 `call`；`focus` 使用锁定页面的 `Page.bringToFront` 激活。Python 调用方必须先履行 Skill 的浏览器选择、授权和专用配置核验；模块只连接，不启动浏览器。CLI 会先履行已有配置核验。截图、快照和资源解析也接受 `within`、`expect_text`、`expect_role`、`expect_count` 等元素约束。

会话固定目标 ID、准确网址、主框架与文档加载身份，每次操作检查目标仍存在，协议动作前后再次检查页面身份。换址、关闭或同网址重新加载后锁定失败保持有效；不选其他页面、不自动导航回来。可选 `--expected-origin` 与 `--expected-title-regex` 增加约束。显式 `navigate` 以及未带准确网址约束的旧 `network --navigate`、`wait --url-contains` 保留导航语义；锁定会话不执行自动重新绑定。

未指定参数时的默认配置保持为：

```text
CDP: http://localhost:9222
Profile identity: agent-browser
Profile directory: %USERPROFILE%\.agent-browser\profile
```

其他专用配置必须显式指定独立端口与持久数据目录。所有全局参数放在子命令前，例如：

```bash
uv run <absolute-script-path> --endpoint http://localhost:9223 --user-data-dir 'C:\Users\Akira\.agent-browser\chrome-profile' status
uv run <absolute-script-path> --endpoint http://localhost:9223 --user-data-dir 'C:\Users\Akira\.agent-browser\chrome-profile' ensure
```

`--profile-directory` 是该专用数据目录内的 Chrome 配置子目录，默认 `Default`；它不表示用户日常 Chrome 的配置选择器。自定义目录禁止复用默认 Agent 目录、其子目录和本地 `9222` 端口，也拒绝 Windows 根目录与无效路径。自动启动只支持带明确端口的本地 HTTP 地址，并为含空格的 Windows 路径保留参数引号。

`status` 只探测与核验，不启动 Chrome。自定义目录的页面命令在复用实例前通过 `Browser.getBrowserCommandLine` 核对数据目录和配置子目录；新启动的实例会带 `--enable-automation`。不匹配或无法核验时拒绝控制，不关闭、替换或重启已有实例。旧默认实例保持可连接，返回的 `profileVerified: false` 表示身份未经核验；仅设置连接地址时也不把其他端口的身份报告成 `agent-browser`。[Chrome 调试协议中的核验方法](https://raw.githubusercontent.com/ChromeDevTools/devtools-protocol/master/pdl/domains/Browser.pdl)

### 1.1 保存与选择专用命名配置

命名配置文件默认放在运行 CLI 的系统用户目录 `~/.agent-browser/profiles.toml`，通过 `--config <路径>` 可指定其他文件。WSL 中该文件位于 WSL 用户目录；文件中的 `user_data_dir` 仍必须是 Windows 的绝对路径。它只保存配置，不保存账号、Cookie、密码或令牌。

例如把已确认用于 Agent 的第二套专用目录保存为 `chatgpt`，使用独立端口 `9223`：

```bash
uv run <absolute-script-path> --endpoint http://localhost:9223 --user-data-dir 'C:\Users\Akira\.agent-browser\chrome-profile' profile-save chatgpt
uv run <absolute-script-path> profiles
uv run <absolute-script-path> --profile chatgpt status
uv run <absolute-script-path> --profile chatgpt ensure
uv run <absolute-script-path> --profile chatgpt tabs
```

示例目录应替换为目标机器上已确认的专用目录。`chatgpt` 是本地配置名称，不是日常 Chrome 的“ChatGPT”配置，也不表示已登录 ChatGPT。`profile-save` 和 `profiles` 都不连接或启动浏览器；保存时必须显式提供目录与端口，同名、同连接地址或相同／互相嵌套的数据目录会被拒绝，不覆盖已有配置。保存采用锁文件与原子替换；写入失败时保留原文件。

未传 `--profile` 时继续使用内置 `agent-browser`；`--profile agent-browser` 也选择同一默认配置，不读取命名配置文件。该内置配置不能被保存、覆盖或改成另一套配置。未知名称或格式错误只影响显式选择命名配置的操作，不静默回退到默认实例。`--profile` 与目录、连接地址参数不能混用，以免部分覆盖导致串用配置。

配置文件使用 TOML，例如：

```toml
schema = 1

[profiles.chatgpt]
endpoint = "http://localhost:9223"
user_data_dir = 'C:\Users\Akira\.agent-browser\chrome-profile'
profile_directory = "Default"
```

配置调整通过编辑该文件完成；不要导入日常 Chrome 的 `Local State`、配置目录或登录资料。若要变更已批准配置的目录或配置子目录，先重新确认控制目标的授权。命名配置记录本身不构成浏览器控制授权。

### 1.2 默认实例的底层启动参考

任务级检查与启动由 CLI 的 `status` / `ensure` 负责。下面的原始探针只用于 adapter 自身排障：

```bash
curl -fsS http://localhost:9222/json/version
```

探针成功时按当前配置核验并复用现有实例，不再启动 Chrome。只有 CDP 不可达时，才探测 Chrome 的实际路径。常见位置包括：

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
  "--profile-directory=Default",
  "--enable-automation",
  "https://example.com"
)
```

这个目录不是临时目录。首次登录飞书、问卷平台或其他站点后，Cookie 和站点登录态留在该 Profile 中，后续 CDP 会话继续复用。浏览器被关闭后也应使用同一路径重新启动，不能换新目录。

本配置管理不读取或管理日常 Chrome 配置。Chrome 136 起对标准数据目录忽略远程调试参数，自动启动会拒绝日常 Chrome 数据目录；仅加 `--profile-directory=Profile 7` 不能改变这一限制。[Chrome 官方说明](https://developer.chrome.com/blog/remote-debugging-port)

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

### 网络条件与资源原语

旧 `network --duration 3 --click '#download'` 继续可用；显式 `network capture` 等价。`network wait-response --url-regex '/upload' --status 2xx --click '#send'` 先启用观察再触发点击，等待匹配响应；状态也可为 `200,201`。`network wait-request` 等待请求开始，`network wait-idle --url-regex '/upload' --idle-ms 500` 要求匹配范围内没有未完成请求且在指定时间内无活动。会话建立时即启用网络域，支持先执行输入／点击再等待；单次 CLI 只能观察连接期间和显式触发之后的请求，不能追溯连接前发生的请求。缓存响应、重定向与失败结束按 CDP 事件处理。[Network 官方协议](https://chromedevtools.github.io/devtools-protocol/tot/Network/)

输出只含安全元数据：网址、方法、状态、媒体类型、内容长度与时间；不返回 Cookie、Authorization、其他原始请求头或请求正文。事件与结果有数量边界。超时同样为 `WAIT_TIMEOUT`，带最后观测和未完成请求数量。

`resolve-artifact '#result a' --within '#message-123'` 从 `data-safe-src`、`currentSrc`、`href`、`src` 或 `data` 提取真实资源，回传网址、来源页、类型提示和建议文件名。调用方优先使用普通 HTTP 传输；网址必须依赖当前浏览器会话时，`browser-fetch '<网址>' --max-bytes 20971520` 在页面中获取并保存到系统临时文件，回传绝对路径、大小与媒体类型。该命令执行读取，不提取或保存浏览器凭据。

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

## 6. 文本输入

普通文本 `input`、`textarea` 与 `contenteditable` 默认使用 CLI 的 `type`：脚本先把目标滚动到可见区域，验证中心点击点没有被其他元素遮挡，通过 `Input.dispatchMouseEvent` 取得真实焦点，再以编辑键事件清除旧内容并调用 `Input.insertText` 输入新文本。

```bash
uv run <script-path> type '#q1' '示例'
```

`contenteditable` 可能只是富文本编辑器的 DOM 表面，真实状态由编辑器内部 model 管理，因此 `fill` 明确拒绝直接修改 `contenteditable.textContent`。`type` 完成后仍要检查站点自身的错误、必填、ARIA、条件展示或其他组件状态，不能只看 DOM 文本。

`fill` 保留为兼容兜底，仅用于原生 `input`、`textarea`、`select`。它直接设置 DOM 值并派发 `input` / `change`，只有确认站点确实以普通 DOM 值为状态来源、或者真实输入路径不可用且操作后能严格验证组件状态时才使用。

## 7. 点击、单选和条件题

高动态页面用唯一业务容器限定目标，例如 `click 'button.variant' --within '#message-123' --expect-text 'U1' --expect-role button`。相同文本的其他容器不参与定位。默认匹配数量为 1；只有显式设置 `--expect-count N --allow-multiple` 才按第一个匹配动作，调用方仍应优先唯一定位。`--predicate` 使用变量 `el` 表达补充约束。会话操作 `click`、`type`、`fill` 使用同名下划线参数。

点击在滚动及一帧等待后重新查询，不使用旧坐标。指针移动与按下后再验证同一元素身份、文本、祖先和位置，命中点被遮挡或元素变化时拒绝。输入回读可编辑区域的可见文本、焦点与 `aria-invalid`，通过 `--verify exact|contains|none` 指定值核验方式；即使关闭值核验，仍核验焦点、元素身份和无效状态。模态框勘察可用 `inspect --within '#modal'`。

普通点击优先使用 CLI 的 `click`。该命令不是 `element.click()` 包装：它读取目标实际屏幕坐标、通过 `elementFromPoint` 验证落点，再发送 CDP mouse move / press / release。自定义单选、React/Vue 控件和条件题都先走这条真实 pointer 路径。

如果真实 `input` 被隐藏而交互绑定在可见 label、anchor 或 wrapper 上，应把 selector 指向站点实际可点击的可见目标。若中心落点被 overlay 或其他元素遮挡，CLI 会拒绝继续；先重新定位真正的交互目标，而不是退回 `element.click()` 绕过命中测试。

点击后使用 `inspect`、`wait` 或站点特定 `eval` 重新读取组件状态、错误状态和后续题目的显示状态。不要一次性给所有隐藏题写值再假定页面会接受；条件题应按真实交互顺序展开。

## 8. 日期控件

### 可解释异步等待

`wait` 保留选择器、文本、网址片段和表达式条件，并新增 `--dom-stable <选择器> --stable-ms 500`。稳定条件比较数量、可见文本和指定属性，要求至少一个元素存在；`--attribute` 可重复指定观测属性。

`elements --selector '.message' --within '#messages'` 返回有界元素观测及身份。动作前保留 `identity` 数组，再用 `wait-new --selector '.message' --baseline '[1,2]'` 等待真正新增元素。省略数组时以等待启动时的元素为基准；已经出现的结果需要使用动作前的数组。站点虚拟列表复用 DOM 节点时，在两次调用中使用相同的 `--identity-attribute id` 或现有消息身份属性；数组中会包含属性身份，节点复用但属性变化也能识别。属性为空时退回元素对象身份，不临时修改 DOM 打标记。

`wait-transition --selector '#status' --initial-text '正在发送' --until-expression 'value === "完成"'` 记录初始、途中和完成文本，表达式可读 `value` 和 `observed`。若要求经过特定途中状态，可重复使用 `--intermediate-text`；轮次之间短暂出现的文本可能无法捕获，不应把极短状态作为完成前提。`wait-mutation --within '#preview' --until-expression '<表达式>'` 要求范围内先发生变化，再满足完成条件。

等待在页面安装 `MutationObserver`，变化时立即唤醒，定时器兼容无 DOM 变化的条件，并在完成或失败后清理。需要把触发与等待结合时，传 `--click` 和可选 `--click-within`，先安装观察与基线，再使用真实点击。超时返回 `WAIT_TIMEOUT`，`context` 包含条件、`elapsed`、`last_observed`、`mutation_count` 和文本变化记录。会话中使用相同操作名与下划线参数，`timeout` 按请求指定秒数。

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

`upload 'input[type=file]' '/tmp/中文 图片(1).png' --within '#attachment-area' --check-only` 返回完整预检；去掉 `--check-only` 才设置文件。`--predicate 'el.accept.includes("image")'` 可消歧隐藏输入，默认不按 DOM 顺序挑选。单文件输入收到多个路径返回 `FILE_CONSTRAINT_VIOLATION`，缺文件返回 `FILE_NOT_FOUND`，设置后回读不一致返回 `UPLOAD_VERIFICATION_FAILED`。页面额外大小限制用 `--max-file-bytes`、`--max-total-bytes` 表达，不能从 `accept` 推断大小。

路径转换依据浏览器的 `navigator.platform`，在 WSL 控制 Linux 浏览器时保留 Linux 路径；控制 Windows 浏览器时转换，并先核验本地文件。无法核验远程 Windows 路径时拒绝。结果 `state.files` 包含浏览器读到的 `name`、`size`、`type`；`input_rebuilt` 和 `current_input` 说明设置后是否重建。上层仍需等待预览、传输完成和消息落地，不把 CDP 设置成功当作服务器已收到。

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

### 截图、快照与失败证据

`screenshot --output /tmp/page.png` 截取可视区域，增加 `--selector '#modal' --within '#root'` 可裁剪元素。`snapshot --selector '#modal' --max-chars 10000` 返回有界 HTML、位置、计算可见性、祖先与子控件，移除脚本、隐藏凭据输入和敏感属性。输出图片来自 [`Page.captureScreenshot`](https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot)。

`click '#missing' --evidence-on-error` 等高风险命令在失败时生成系统临时证据目录；会话也可全局开启，或每行传 `evidence_on_error: true`。原错误的 `context.evidence_dir` 指向目录，包含 `meta.json`、`screenshot.png`、`visible-text.txt`、`controls.json`、`target.json`、`console-errors.json`。网址查询与片段、敏感键和认证文本被过滤；不采集 Cookie、浏览器存储、请求头或完整 DOM。失败截图临时模糊表单输入，然后恢复原样。截图仍包含页面其他可见内容，证据是本地临时诊断资料，不自动发送或长期存档。

关闭、换页或失去锁定时不会为了凑齐证据控制另一个目标，`meta.capture_errors` 说明缺少哪些采集步骤。临时目录不可写等诊断失败通过 `evidence_capture_error` 回传，保留原动作错误码。

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

最终检查不只回读字段内容，还应同时返回会证明站点内部状态已接受输入的信号，例如必填/错误提示、`aria-invalid`、校验类名、单选状态、条件题显示状态与当前 URL。示例：

```javascript
({
  name: document.querySelector('#q1')?.value,
  nameInvalid: document.querySelector('#q1')?.getAttribute('aria-invalid'),
  outboundAmount: document.querySelector('#q5')?.value,
  cityTransport: document.querySelector('input[name="q11"]:checked')?.value,
  visibleErrors: [...document.querySelectorAll('[role="alert"], .error, .invalid')]
    .filter(el => getComputedStyle(el).display !== 'none')
    .map(el => el.innerText.trim())
    .filter(Boolean),
  uploadMessage: document.querySelector('.uploadmsg')?.innerText || '',
  href: location.href
})
```

实际字段名、错误选择器和状态信号必须来自当前页面勘察结果；DOM 中存在文本不能单独作为受控组件填写成功的证据。

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
