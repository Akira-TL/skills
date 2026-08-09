# visible-browser-form-automation

## 作用

该 Skill 用于“Agent 自动操作网页，但用户仍要实时看到浏览器，并在最终提交前人工复核”的任务。

当前默认拓扑是：WSL 中运行 Agent 和自动化逻辑，Windows Chrome 使用固定的持久专用 Profile `%USERPROFILE%\.agent-browser\chrome-profile`，并开放本机 Chrome DevTools Protocol（CDP）端口 `9222`。每次任务先检查 `localhost:9222`，已有实例就直接复用；只有实例不存在时才用同一个 Profile 重启。用户看到的是实际被 Agent 操作的 Windows Chrome，而登录 Cookie 和站点状态会跨任务保留。

这种方式特别适合问卷、报销、报名、申请等表单。Agent 可以完成字段勘察、条件题展开、金额和编号填写、页面滚动和状态检查；用户可以保留验证码、敏感附件、截图上传和最终提交等步骤。

## 本次实践得到的经验

本次在 Windows + WSL2 环境中使用 Chrome CDP 操作问卷星交通报销问卷，验证了以下流程。

第一，用户要求“无头自动化但必须可视化”时，不应机械坚持真正的 `--headless`。真正 headless 浏览器本身没有可直接观察的窗口。更合适的实现是让 Windows Chrome 保持有头运行，把自动化控制面放在 WSL。

第二，Windows Chrome 应使用**固定持久**的独立 `--user-data-dir` 启动远程调试实例，而不是每次创建临时 Profile。这样既不会污染用户日常 Profile，也能保存飞书等网站的登录态。WSL 中先通过 `http://localhost:9222/json/version` 判断专用浏览器是否已经运行：成功就复用，不再启动第二个 Chrome；随后用 `/json/list` 从多个 background page、service worker、omnibox popup 中筛选真正的目标 `type=page` 标签页。

第三，动态问卷不能按输入框索引盲填。实际页面中，选择“有城际交通需要报销”后，日期、交通工具、金额、发票号等后续题目才出现。正确流程是先读取正文和控件元数据，再点击上游单选，之后重新读取可见 DOM。

第四，填写字段时应让站点自己的事件链生效。单选优先调用 `.click()`；文本赋值后根据页面情况派发 `input` 和 `change`。只读日期框等自定义组件如果采用直接赋值，必须在之后重新读取字段和页面状态确认站点接受了值。

第五，文件上传是跨系统浏览器自动化中最容易出错的部分。浏览器运行在 Windows 时，文件输入控件需要 Windows 能访问的路径，而不是只有 WSL 能访问的 `/home/...` 路径。本次问卷的上传区域还实际限制“上传文件数量不能超过1个”。发现这一限制后，自动化没有继续覆盖上传区，而是停止并把页面滚动到上传位置，让用户手动处理截图和最终凭证包。

第六，报销表中的“付款金额”和“本人应报销金额”不能混用。本次 1,064 元付款记录对应两人合并购票，个人铁路电子客票金额为 532 元，因此表单填写 532 元，而不是把整单 1,064 元作为个人报销金额。自动化应以原始凭证、个人票据和说明文件的逻辑一致性为准。

第七，“先不要提交”必须视为硬边界。自动化可以填表、检查和滚动，但不能点击提交按钮、调用 `form.submit()`、调用站点提交函数或通过 Enter 意外触发提交。任务交还用户前应再次读取关键值，并确认页面仍处于填写页。

第八，专用 Agent Chrome 默认跨任务常驻。单次任务结束不关闭浏览器、不删除 Profile、不清 Cookie。后续任务重新读取 `/json/list` 获取当前页面 WebSocket 即可；页面级 WebSocket 可以重新建立，但浏览器实例和 Profile 不需要重新创建。若用户手动关闭浏览器或系统重启，则仍以同一个专用 Profile 启动，因此正常情况下不需要再次登录。

## 推荐工作流

1. 先访问 `http://localhost:9222/json/version` 检查专用 Agent Chrome 是否已经运行。
2. 已运行则直接复用；未运行才探测 Chrome 路径，并以 `%USERPROFILE%\.agent-browser\chrome-profile` 启动 `9222` CDP 实例。
3. 读取 `/json/list`，优先复用目标 URL/标题对应的现有标签页；没有时在同一个浏览器实例中打开目标页。
4. 找到目标页面的 WebSocket 调试地址并建立页面级 CDP 连接。
5. 读取页面正文、动态列表、输入控件、问题容器和文件上传属性。
6. 按真实页面交互顺序抓取、展开条件题或填写。
7. 对姓名、日期、金额、编号等关键字段进行回读校验。
8. 在登录、文件上传限制、验证码、隐私确认等环节按需交还用户。
9. 把页面停在用户容易复核的位置；单次任务结束后保留专用 Chrome 和 Profile。
10. 只有在用户随后明确授权后，才执行提交、发送、付款、发布等最终动作。

## 技术实现

主运行规则位于：

```text
productivity/visible-browser-form-automation/SKILL.md
```

CDP 命令、DOM 勘察表达式、文件上传和跨系统路径处理示例位于：

```text
productivity/visible-browser-form-automation/REFERENCE.md
```

## 使用 npx skills 安装

从当前仓库安装到 Codex：

```bash
npx skills add . --skill visible-browser-form-automation --agent codex -g -y
```

同时安装到 Codex、Claude Code、OpenCode 和 Hermes Agent：

```bash
npx skills add . \
  --skill visible-browser-form-automation \
  -g \
  -a codex \
  -a claude-code \
  -a opencode \
  -a hermes-agent \
  -y
```

安装到所有被 CLI 检测到的 Agent：

```bash
npx skills add . --skill visible-browser-form-automation --agent '*' -g -y
```

先只检查仓库中能识别到哪些 Skill：

```bash
npx skills add . --list
```

也可以直接从 GitHub 的自研 Skill 仓库安装：

```bash
npx skills add Akira-TL/skills --skill visible-browser-form-automation --agent '*' -g -y
```
