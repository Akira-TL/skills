# Midjourney Discord

`midjourney-discord` 是一个实验中的 Akira 通用 Skill，用于把用户已经登录的 Discord + Midjourney Bot 会话暴露为 Codex/Agent 可调用的确定性 CLI。

## 为什么采用 Discord 浏览器路径

Midjourney 普通会员并不等价于公开 API 配额。为了复用用户已经购买的会员，本 Skill 只连接用户明确授权的可见 Discord 浏览器页面，并由 `browser-access` 完成真实页面交互。它不要求 Discord user token、不导出 Cookie、不调用私有 Discord/Midjourney API。

这条路径仍属于非官方自动化，应由用户自行接受平台账户风险。Skill 因此默认放在 `in-progress`，不在 Router 中自动触发安装。

## 安全设计

- 每次必须提供完整频道 URL，且只允许连接已经打开、完全匹配的 tab。
- CLI 默认不导航，不访问其他服务器/频道。
- 账号设置只提供 `/settings` 只读观察，不提供通用的设置修改命令。
- 生成和按钮动作使用独立显式子命令。
- U/V 等按钮按照具体 Discord message id 精确定位；等待结果时再用源 Prompt 签名关联，避免同频道并发任务串线。
- 动作前若已经存在 `Remix Prompt`，CLI 会拒绝新的组件点击；已有对话框必须先用 `remix inspect/submit/cancel` 明确处理，防止误提交用户或其他任务的 modal。
- Discord 虚拟消息列表存在 React/DOM 复用风险。实测 `HTMLElement.click()` 可能在视觉按钮正确时触发旧任务状态，因此 Midjourney 消息组件必须先锁定 `message-accessories-<message_id>`，再滚动到可视区并通过 `browser-access` 做真实 pointer click；不使用 DOM click 作为消息按钮兜底。
- Vary Region、Custom Zoom 等复杂模态流程不放进通用 action，避免“点了按钮就算完成”的假成功。
- 下载只使用 Discord 页面已经暴露的附件 URL。

## 推荐命令

```bash
export MJ_DISCORD_CHANNEL_URL='https://discord.com/channels/<guild>/<channel>'

uv run scripts/mj_discord.py doctor
uv run scripts/mj_discord.py command info
uv run scripts/mj_discord.py command settings
uv run scripts/mj_discord.py imagine 'your prompt --ar 16:9'
uv run scripts/mj_discord.py recent --limit 10
uv run scripts/mj_discord.py action --message-id '<message-id>' --button U1
uv run scripts/mj_discord.py action --message-id '<message-id>' --button V1 --accept-remix
uv run scripts/mj_discord.py remix inspect
uv run scripts/mj_discord.py remix submit                # 保留当前 prompt
uv run scripts/mj_discord.py remix submit --prompt '...' # 替换 prompt
uv run scripts/mj_discord.py remix cancel
# 如果 Discord 同时暴露多个 Remix Prompt，先用 prompt 片段消歧：
uv run scripts/mj_discord.py remix --dialog-contains 'brass torus' inspect
uv run scripts/mj_discord.py download --message-id '<message-id>' --output ./result.webp
```

正式 Codex 工作流应保存每次 `imagine` 返回的 `message_id`，后续动作都围绕这个 ID 执行，而不是按视觉顺序寻找最后一组按钮。`--contains` 只允许唯一匹配；匹配多个 Discord 消息时 CLI 会拒绝动作并要求改用 `message_id`。若 `doctor` 或 `remix inspect` 报告已有 Remix modal，应先判断该 modal 是否属于当前任务；归属不明时不得提交或取消。

## 当前支持范围

- 浏览器/频道连通性检查
- `/info`
- `/help`
- `/settings`（只读）
- `/imagine`
- 任务等待与进度解析
- 最近 Midjourney 消息解析
- U1-U4 / V1-V4
- Remix Mode 下的 `Remix Prompt` 检测、保持原 Prompt 提交、替换 Prompt 后提交
- reroll
- 非模态 upscale / vary / zoom / animate
- Midjourney job URL / Discord 原图 URL 提取
- 原图下载

`Vary (Region)`、`Custom Zoom`、`/blend` 文件上传以及账号设置修改需要额外交互契约，不属于当前稳定 CLI 表面。`V1`–`V4` 与普通 Vary 按钮在 Remix Mode 开启时并非直接生成，CLI 会显式进入 Remix modal 状态，只有传 `--accept-remix` 或 `--remix-prompt` 才提交。
