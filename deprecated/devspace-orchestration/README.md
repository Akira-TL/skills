# devspace-orchestration

该已发布 Skill 名称已弃用，替代名称为 `agent-orchestration`。

迁移原因：原名称把一个特定运行环境误写成多 Agent 执行协议的前提，并在实现中硬编码了特定 CLI 与模型名称。新的 Skill 只依据当前 Agent harness 实际暴露的执行原语工作，不绑定具体产品，也不是 Parallel 协议的必选依赖。

原有“接收已定义工作单元、执行并返回真实结果”的职责迁移到：

```text
engineering/agent-orchestration/SKILL.md
```

新安装和后续调用统一使用 `agent-orchestration`。本目录只保留迁移发现信息，不包含可安装的 `SKILL.md`。
