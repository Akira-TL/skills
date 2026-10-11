# browser-access

## 作用

`browser-access` 是 Akira 的通用浏览器访问 Skill。它不再假定“浏览器 = WSL 控制 Windows Chrome”，而是先发现当前 Agent harness 已经提供的浏览器能力，再选择最小且足够的控制路径。

它适用于需要 JavaScript 动态页面、登录态、用户人工认证、网络资源解析、动态 DOM、文件上传或表单操作的网页任务。静态页面、公开资源或普通 API 能由 WebFetch / HTTP 直接完成时，不需要为了使用浏览器而调用本 Skill。

## 浏览器选择顺序

每次需要浏览器时按以下顺序处理：

1. **harness 原生或内联浏览器**：当前 Agent 产品已经提供网页控制能力且足够完成任务时直接使用，不自行启动第二套浏览器。
2. **用户可见、可复用浏览器**：原生能力不足时，发现是否存在能够让用户看到并保持登录态的浏览器实例或 Profile。
3. **自行建立 headed browser**：只有前两层都不可用时才启动新的浏览器环境，并固定使用持久 Profile；WSL + Windows Chrome CDP、WSLg Chromium、Xvfb/noVNC 等都属于这一层的具体 adapter。

Windows Chrome/CDP 是当前 Akira 环境中验证过的一个实现，但不是所有 Agent 环境的默认入口。

## Browser Grant 与 Profile

如果 Agent 准备直接控制用户自己的现有浏览器或 Profile，而当前对话中还没有得到该目标的明确授权，应先询问一次。

用户同意后，在当前对话中将同一个浏览器 + Profile 视为已批准的 `Browser Grant`。后续继续使用该控制目标时不重复询问；只有换浏览器、换 Profile 或明显扩大控制权限时才重新获得授权。

自行启动的浏览器必须使用固定持久配置，而不是每次创建临时目录。未指定配置时仍使用 `agent-browser`；显式指定的其他专用配置绑定各自的数据目录、配置子目录和连接地址，重启后按同一组配置恢复登录态。用户指定并授权具体配置时优先遵循该选择。

配置管理只负责专用 Agent 浏览器，不发现、导入、复制或管理日常 Chrome 配置。配置名称与 Google 账号、Chrome 配置显示名称相互独立。

## 登录与人机协作

Agent 可以打开登录入口、选择机构登录、定位验证码区域并完成机械步骤。凡是已经识别为需要人工操作的步骤，统一进入强制人工接管：该步骤不再作为自动化目标，但 Agent 会继续完成所有不依赖它的可自动化工作，并在本轮任务推进结束时把待人工动作统一交给用户。

验证码、短信码、二次认证、机构登录、需要用户本人选择或检查的附件，以及隐私、授权、支付、法律确认等都属于典型人工步骤。Agent 不会为了继续自动化而尝试绕过、模拟、规避或替代这些步骤；依赖它们的流程只推进到人工边界之前，并把页面停在用户可直接接手的位置。

用户完成后，Agent 应先验证浏览器已经进入预期认证或页面状态，再继续抓取、解析资源或填写页面。登录态由浏览器/Profile 自己保存，不把 Cookie、密码或 token 写进项目文件。

## 网络资源解析

浏览器可以作为资源授权和解析层，但默认不作为文件下载器。

需要取得 PDF、数据文件或其他 artifact 时，先检查页面 DOM、iframe、embed、object、meta 或页面状态中是否已经存在真实资源 URL。只有 URL 必须通过点击、脚本或重定向才能生成时，才在触发动作前开启网络观察并捕获最终请求。

解析出的结果应尽量作为临时 `Artifact Request` 返回给调用方，其中可包含 URL、method、必要 headers、referer、临时 session context、content type、文件名和失效时间。能够通过普通 HTTP 重放时，由调用方直接传输；资源与浏览器会话强绑定时，再在浏览器上下文获取响应体。浏览器默认 Downloads 目录不是资源获取的完成条件。

这使 `literature-access` 等上层 Skill 可以使用浏览器完成登录和 PDF 请求解析，同时继续由自己的获取层完成真正的文件传输和验收。

## 动态页面与表单能力

原 `visible-browser-form-automation` 中已经验证的表单规则继续保留，但交互策略已经收紧：

- 先读取页面正文和控件元数据，再建立当前页面映射；
- 文本 `input`、`textarea` 与 `contenteditable` 默认通过真实点击取得焦点后执行键盘输入，不以 DOM setter 作为首选；
- 单选、多选、按钮与自定义控件默认走真实 pointer / mouse 事件，而不是 `element.click()`；
- 条件题按真实交互顺序展开，每次状态变化后重新读取页面状态；
- `fill` 只作为原生 `input` / `textarea` / `select` 的兼容兜底；富文本 `contenteditable` 不通过 `fill` 写入；
- 上传前检查数量、大小、类型和浏览器实际运行的操作系统路径；
- 姓名、金额、日期、编号等关键字段在交还用户前必须回读，同时确认组件自身的 required/error/invalid 状态已经按预期变化；
- “提交”“发送”“付款”“发布”“删除”“授权”等不可逆动作仍以用户明确授权为硬边界。

## WSL + Windows Chrome adapter

在当前 Akira 的 WSL + Windows 环境中，已验证的 fallback 是一个长期复用的 Windows Chrome 专用 Profile，并通过本机 CDP 端口控制。

默认参考值：

```text
CDP: http://localhost:9222
Profile identity: agent-browser
Profile directory: %USERPROFILE%\.agent-browser\profile
```

不传配置参数时，上述默认值保持不变。其他专用配置通过 `--endpoint` 与 `--user-data-dir` 显式指定独立端口和绝对 Windows 路径，配置子目录通过 `--profile-directory` 指定，默认 `Default`。仅传其他连接地址时可连接现有实例，但不会在新端口启动默认目录。

`status` 只检查，不启动 Chrome；本地自定义目录通过 Windows 端口所有者核对 Chrome 进程的实际目录、配置子目录和端口，再比对实际调试实例标识，不匹配或不能核验时停止。新启动的实例不再强制添加 `--enable-automation`；旧默认实例保持兼容，`profileVerified` 明确表示是否完成身份核验。远程实例保留 Chrome 调试协议的命令行核验方式。脚本不会关闭或替换已有浏览器，也不修改默认配置。

登录兼容性不由配置名称保证。Google 可能拒绝自动化浏览器认证；出现此类提示时保留人工登录边界，按网站支持的方式处理，不伪造浏览器身份或修改页面的自动化标识。移除非必要启动参数也不代表保证登录成功。[Google 官方说明](https://support.google.com/accounts/answer/7675428?co=GENIE.Platform%3DDesktop&hl=en)

自动启动前在 Windows 上检查所选端口是否能绑定回环地址；端口被占用或被系统保留时提前报错，不打开一个无法连接的窗口，不静默换端口。示例端口须按目标机器的实际可用情况选择；检查通过后仍会验证实际调试连接。

Chrome 136 起，远程调试需要非标准数据目录；选择日常目录中的 `Profile 7` 不能消除该限制，适配器自动启动会拒绝日常 Chrome 数据目录。[Chrome 官方说明](https://developer.chrome.com/blog/remote-debugging-port)

该 adapter 提供确定性命令行界面（Command-Line Interface, CLI）：

```text
productivity/browser-access/scripts/browser_cdp.py
```

支持把专用目录和独立端口保存成命名配置，例如：

```bash
uv run <absolute-script-path> --endpoint http://localhost:9223 --user-data-dir 'C:\Users\Akira\.agent-browser\chrome-profile' profile-save chatgpt
uv run <absolute-script-path> profiles
uv run <absolute-script-path> --profile chatgpt status
uv run <absolute-script-path> --profile chatgpt tabs
```

示例路径应替换为目标机器上确认的专用目录。配置默认保存到运行脚本的系统用户目录 `~/.agent-browser/profiles.toml`，可用 `--config` 指定其他文件。WSL 中配置文件放在 WSL 用户目录，但记录的数据目录使用 Windows 绝对路径。

保存和列出配置都不启动浏览器。同名、重复端口、相同或互相嵌套的数据目录会被拒绝；默认 Agent 目录及其子目录也不能注册为其他配置。`agent-browser` 保留为不能覆盖的内置默认配置。`--profile` 与显式目录、端口参数不能混用，未知名称不会回退到默认浏览器。不传 `--profile` 时不读取命名配置文件，保持原有默认行为。

`chatgpt` 是本地专用配置名，与日常 Chrome 中的显示名称和 Google 账号无关。保存配置不代表授权控制，已保存配置的调整通过编辑 TOML 文件完成；目录或配置子目录变更后重新确认控制目标。

它统一处理 Chrome 生命周期、page target 选择、导航、页面文本/控件勘察、真实指针点击、真实文本输入、DOM 兼容填写、等待、上传、任意单次 CDP 调用和网络请求观察。`click` 使用 `Input.dispatchMouseEvent`，`type` 使用真实点击取得焦点后调用键盘编辑命令与 `Input.insertText`；`fill` 明确降为兼容兜底。Agent 通过 `uv run <script-path> --help` 读取当前命令面；页面特定逻辑使用 CLI 的 `eval`，而不是重复编写 WebSocket/CDP 包装脚本。复杂网站的 `inspect` 默认只回传可见控件和文件控件，减少无关 DOM 对上下文的占用。

需要让 Agent 的已决定动作在执行前重新核对页面时，可用页面级 `call --guard`：在同一连接中读取条件，只有结果严格为布尔值 `true` 才发送该动作。条件不满足或读取失败时不执行，不承担语义判断或自动重试。多人交互时仍应避开用户正在编辑的输入框；此检查不宣称消除所有并发输入竞争。

完整的 CDP 原理、DOM 表达式、网络资源解析、跨系统上传路径和问卷实践经验位于：

```text
productivity/browser-access/REFERENCE.md
```

## 运行时文件

主运行规则：

```text
productivity/browser-access/SKILL.md
```

确定性 Chrome/CDP CLI：

```text
productivity/browser-access/scripts/browser_cdp.py
```

低层实现参考：

```text
productivity/browser-access/REFERENCE.md
```

## 从旧名称迁移

`visible-browser-form-automation` 已更名为 `browser-access`。原有动态表单、文件上传、可见浏览器和不可逆提交边界仍然保留，新名称同时覆盖登录后页面读取、网络资源解析以及 harness/browser capability discovery。

入口 Package：`akira-tl/skills/browser-access`。安装、更新与修复统一由 `akira` Router 交给 Skiloom；当前 first-party source mode 使用 Git `main`，不再调用 Akira 私有安装脚本。
