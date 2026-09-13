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

自行启动的浏览器必须使用固定持久 Profile，而不是每次创建临时目录。统一的逻辑 Profile identity 为 `agent-browser`；各浏览器 adapter 将它映射到自己的持久 data directory。浏览器关闭或系统重启后继续用同一个 Profile 恢复登录态。用户日常 Profile 与专用 Agent Profile 默认隔离，只有用户明确授权时才连接现有个人 Profile。

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

原 `visible-browser-form-automation` 中已经验证的表单规则仍然保留：

- 先读取页面正文和控件元数据，再建立当前页面映射；
- 条件题按真实交互顺序展开，每次状态变化后重新读取 DOM；
- 文本赋值后按页面需要派发 `input` / `change`；
- 上传前检查数量、大小、类型和浏览器实际运行的操作系统路径；
- 姓名、金额、日期、编号等关键字段在交还用户前必须回读确认；
- “提交”“发送”“付款”“发布”“删除”“授权”等不可逆动作仍以用户明确授权为硬边界。

## WSL + Windows Chrome adapter

在当前 Akira 的 WSL + Windows 环境中，已验证的 fallback 是一个长期复用的 Windows Chrome 专用 Profile，并通过本机 CDP 端口控制。

默认参考值：

```text
CDP: http://localhost:9222
Profile identity: agent-browser
Profile directory: %USERPROFILE%\.agent-browser\profile
```

使用前先检查现有 CDP 实例；存在就复用，不存在才以同一 Profile 启动 Chrome。该 adapter 现在提供确定性命令行界面（Command-Line Interface, CLI）：

```text
productivity/browser-access/scripts/browser_cdp.py
```

它统一处理 Chrome 生命周期、page target 选择、导航、页面文本/控件勘察、点击、填写、等待、上传、任意单次 CDP 调用和网络请求观察。Agent 通过 `uv run <script-path> --help` 读取当前命令面；页面特定逻辑使用 CLI 的 `eval`，而不是重复编写 WebSocket/CDP 包装脚本。复杂网站的 `inspect` 默认只回传可见控件和文件控件，减少无关 DOM 对上下文的占用。

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

项目级安装统一从远端 GitHub source 拉取，并在当前项目建立软链接：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill browser-access \
  --project .
```
