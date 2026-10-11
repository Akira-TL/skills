---
name: midjourney-discord
description: 通过用户已授权、已登录且可见的 Discord 浏览器会话操作 Midjourney Bot。用于 Codex/Agent 需要在指定 Discord 频道执行只读命令、提交 /imagine、等待任务、解析消息、精确处理 U/V/Remix 等组件状态、获取原图 URL 或下载结果时。必须依赖 browser-access，并锁定用户明确授权的频道。
---

# Midjourney Discord

## 目标

把 Midjourney 的 Discord 工作流封装为可审计的 CLI，供 Codex / Agent 在**用户明确授权的现有浏览器会话**中调用。该 Skill 不使用 Discord user token、不读取 Cookie、不模拟私有 API，也不创建第二套浏览器控制实现；浏览器控制统一委托给 `browser-access`。

Midjourney 未向普通订阅用户提供可与会员额度等价复用的公共 API；通过浏览器自动操作 Discord 属于非官方自动化路径。只有用户明确接受该风险并授权当前浏览器/Profile 后才使用。

## 强制边界

1. **精确频道锁定**：每次调用都传完整 Discord channel URL，例如 `https://discord.com/channels/<guild>/<channel>`。CLI 只匹配已经打开且 URL 完全一致的 page target；默认不导航、不新开标签页。
2. **复用 Browser Grant**：如果当前对话没有对该浏览器/Profile 的明确授权，先按 `browser-access` 的 Browser Grant 规则询问。换 Profile、换浏览器或扩大控制范围时重新授权。
3. **不触碰凭据**：不得导出 Discord token、Cookie、Authorization header 或 Midjourney 会话凭据。
4. **账号设置默认只读**：`/settings` 只允许读取当前状态；`/prefer`、模式切换、隐私设置、订阅操作等会改变账号行为的命令只有用户明确要求时才另行处理，不由本 CLI 泛化执行。
5. **生成动作必须来自用户意图**：`imagine`、U/V、reroll、upscale、vary、zoom、animate 都会产生外部动作或消耗额度；只有用户已经要求生成/继续处理时执行。
6. **识别 Remix modal**：Remix Mode 开启时，`V1`–`V4`、`Vary (Subtle)`、`Vary (Strong)` 可能先弹出 `Remix Prompt`。CLI 必须返回 modal 状态；只有调用方显式传 `--accept-remix` 或 `--remix-prompt` 才继续提交。
7. **不把复杂模态动作伪装成完成**：`Vary (Region)`、`Custom Zoom` 等需要区域选择或额外参数的动作不在通用 `action` 支持列表中。遇到这类按钮，回到 browser-access 做专门交互或交给用户。
8. **保护已有 modal**：执行任何新的 Midjourney 组件动作前先检查页面是否已有 `Remix Prompt`。如果已有，拒绝点击其他按钮，使用 `remix inspect/submit/cancel` 处理当前对话框，防止把用户或其他任务的 modal 误归因给当前动作。
9. **只按消息定位按钮**：禁止依赖“页面最后一个 U1”之类位置假设。优先使用 `message_id`；次选唯一的 `contains` 文本定位；等待结果时还必须绑定源 Prompt 签名，避免同频道并发任务串线。
10. **消息按钮必须真实 pointer click**：Discord 会复用虚拟列表 DOM，实测对视觉正确的按钮直接执行 `HTMLElement.click()` 可能触发旧任务状态。消息组件必须锁定 `message-accessories-<message_id>`，滚动到可视区后通过 `browser-access` 的 pointer click 执行；DOM click 仅可用于已经精确锁定的本地 modal 取消等不会跨任务提交的控制。

## CLI

入口：

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" doctor
```

也可以设置：

```bash
export MJ_DISCORD_CHANNEL_URL='https://discord.com/channels/<guild>/<channel>'
```

### 1. 连通性与频道锁

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" doctor
```

成功结果至少包含：

- exact channel URL；
- 唯一 page target id；
- Discord composer；
- 当前频道可见状态。

### 2. 只读命令

仅内置：

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" command info
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" command help
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" command settings
```

这些命令会真实调用 Midjourney Bot，但不会修改账号设置。

### 3. 生图

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" imagine \
  'cinematic product shot, soft studio light --ar 16:9'
```

默认等待任务完成。需要仅提交不等待时：

```bash
... imagine 'prompt' --no-wait
```

返回 JSON 中保存：

- `message_id`
- 实际 Discord 文本（可观察 Midjourney 自动追加参数）
- `status` / `progress`
- `job_url`
- `original_urls`
- 当前按钮

### 4. 最近任务与精确定位

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" recent --limit 10
```

需要后续 U/V 操作时，优先记录第一次生成返回的 `message_id`。

### 5. U/V 与非模态动作

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" action \
  --message-id chat-messages-... --button U1
```

支持：

- `U1`–`U4`
- `V1`–`V4`（Remix Mode 开启时会检测 `Remix Prompt`）
- `Reroll`
- `Upscale (Subtle)`
- `Upscale (Creative)`
- `Vary (Subtle)`
- `Vary (Strong)`
- `Zoom Out 2x`
- `Zoom Out 1.5x`
- `Animate (High motion)`
- `Animate (Low motion)`

默认等待由该动作产生的新 Midjourney 消息；`--no-wait` 可只点击。

如果 Remix Mode 已开启，希望保持原 Prompt：

```bash
... action --message-id chat-messages-... --button V1 --accept-remix
```

希望在 variation 时改 Prompt：

```bash
... action --message-id chat-messages-... --button V1 \
  --remix-prompt 'new prompt --ar 16:9'
```

如果没有提供这两个参数而页面出现 Remix modal，CLI 返回 `modal_required: true` 并停止，不会自动提交。

已经存在 Remix modal 时，可独立处理：

```bash
... remix inspect
... remix submit                 # 保持当前 prompt
... remix submit --prompt '...'  # 替换 prompt 后提交
... remix cancel
# 多个 Remix Prompt 同时可见时，用 prompt 片段消歧：
... remix --dialog-contains 'prompt fragment' inspect
```

CLI 不会把动作前就存在的 modal 当作当前动作产生的 modal；这种情况下会拒绝新的组件点击。

### 6. 下载原图

```bash
uv run <skill>/scripts/mj_discord.py --channel-url "$URL" download \
  --message-id chat-messages-... --output ./result.webp
```

下载只使用当前 Discord DOM 暴露的附件 URL；不提取账户凭据。

## Codex 推荐流程

1. 运行 `doctor`。
2. 如需了解当前账号状态，运行 `command info`；只有需要确认模型/风格默认值时运行 `command settings`。
3. 运行 `imagine` 并保存 `message_id`。
4. 根据返回按钮决定是否执行 `action`。
5. 对选定结果运行 `download`。
6. 需要多个素材时，以任务队列逐个调用，不依赖 Discord 页面视觉顺序。

如果生成文本出现未在输入 Prompt 中提供的参数，例如 `--niji 7`、`--s 750`，把它视为账号当前默认设置的可观察结果；不要自行修改，除非用户明确要求。
