---
name: ask-akira
description: 在需要快速交付、紧急修复或比赛冲刺时，用 Akira 的执行策略裁剪 Matt 的标准工程流程；默认开发仍使用 Matt。
argument-hint: "rapid | emergency | competition [scope=task|session]"
disable-model-invocation: true
---

# Ask Akira

Matt skills 是标准工程能力层。`ask-akira` 只处理 Matt 标准流程在特殊时间约束下过重的情况：它改变路由、交互频率、并行方式和完成标准，不重写 Matt 已经做好的专业能力。

## 1. 建立执行模式

只有用户显式调用本 Skill 或明确要求切换到 `rapid`、`emergency`、`competition` 时才进入 Akira 模式。普通的“快一点”“赶紧”“今天要完成”“这个很急”只描述任务优先级，不自动切换执行模式。

支持三个模式：

- `rapid`：以最少 ceremony 尽快交付仍可维护的软件。
- `emergency`：尽快恢复正确行为，同时限制 blast radius。
- `competition`：在明确截止时间前最大化完整、稳定、可演示的成果。

若用户调用 `/ask-akira` 但没有给出模式，询问一次要进入哪一个模式；不要根据紧迫措辞猜测。

`scope` 默认为 `task`：当前任务完成后模式失效，后续开发重新回到 Matt。只有用户显式指定 `scope=session` 时，模式才跨多个任务持续到当前会话结束或用户明确退出。

## 2. 锁定模式，隔离上下文

模式一旦建立，在其作用域结束前保持不变。新的紧迫性、风险、难度或截止时间信息可以改变当前模式内的优先级和验证强度，但不能隐式切换模式。

用户明确切换模式时：

- 保留已经确认的需求、事实、设计决定、代码状态和产物；这些是 **Work State**。
- 用新模式完全替换旧模式的规划、交互、验证和速度权衡；这些是 **Execution Policy**。
- 从切换点开始只读取新模式目录，不再把旧模式文件作为当前规则。

## 3. 按需加载

模式确定后只读取 `<mode>/ROUTER.md`。Router 只决定下一跳；只读取当前分支明确要求的文件。

- 不预读整个模式目录。
- 不读取其他模式目录来比较差异。
- 不因为目录结构存在某个文件就自动加载它。
- 到达真实工作边界后再回到当前模式的 Router 重新分类下一步。

模式目录中的文件是 Akira 对标准流程的 **delta**。没有 Akira 路由或覆盖的能力继续使用 Matt；不要为了让目录“完整”而复制 Matt 的正文。

## 4. 与 Matt 协作

Matt 继续负责能力本身的方法论。Akira Router 可以直接交给当前 harness 中可由模型使用的 Matt Skill，例如：

- `grilling` / `domain-modeling`：确实存在阻塞性产品或领域决策时。
- `prototype`：必须通过可运行的逻辑或可见 UI 才能做决定时。
- `diagnosing-bugs`：需要系统化建立反馈环、定位根因时。
- `tdd`：当前模式明确选择完整 TDD 时。
- `codebase-design`：测试 seam 或模块接口本身是设计问题时。
- `code-review`：当前模式明确要求 Matt 的完整双轴审查时。
- `research`、`resolving-merge-conflicts`、`wizard`：任务形态与其原始触发条件一致时。

Matt 的 user-invoked Skill 不是 Akira 可以隐式调用的依赖。Akira 若要省略或替代其 ceremony，应在自己的分支文件中定义该特殊模式所需的更短流程。

## 5. 正式 Parallel 协作

Rapid / Emergency / Competition 的模式策略可以继续使用多 Agent，但模式与 Parallel 是两个正交层：模式决定**做什么、优先级和验证强度**，Parallel 只决定**如何让多个 Worker 通过 Tracker 安全协作**。

当协作需要 Execution Map、Gate、可领取 Parallel Task、跨会话 Ownership、动态 frontier 或 Coordinator 双层验收时，路由到 user-invoked 的 `/parallel-coordinator`：

- 把当前 mode 与已经确认的 Work State 作为上游来源交给 Coordinator，不因为进入 Parallel 补造 Matt Spec/Ticket。
- 当前 Akira mode 不切换；Coordinator 与 Worker 都继续遵守该 mode 的 Execution Policy。
- Worker 任务由 model-invoked 的 `parallel-execution` 负责 claim、生命周期和阶段汇报。
- Parallel 不规定 Worker 必须由哪一种 Agent harness、CLI、进程模型或 worktree 管理器启动；实际执行只使用当前环境已经提供且可验证的能力。

若只是当前父 Agent 临时并行两个只读查找或完全隔离的短任务，不需要持久 Tracker 状态，则按当前模式的 coordination Router 使用当前 harness 已有的并行能力；没有并行能力时保持串行，不为此建立 Execution Map。

## 6. 风险只提高验证强度

Akira 模式控制的是执行策略，不是安全豁免。当前工作暴露出数据迁移、权限、安全、不可逆写入、广泛 blast radius 或其他高风险因素时，在当前模式内提高验证强度；不要仅因为追求速度而把已经识别出的风险降级。

## 7. 进入模式

- `rapid` → 读取 [`rapid/ROUTER.md`](rapid/ROUTER.md)。
- `emergency` → 读取 [`emergency/ROUTER.md`](emergency/ROUTER.md)。
- `competition` → 读取 [`competition/ROUTER.md`](competition/ROUTER.md)。

模式作用域结束后停止使用本 Skill 的执行策略；标准开发重新由 Matt 路由。
