# visible-browser-form-automation

该已发布 Skill 名称已弃用，替代名称为 `browser-access`。

迁移原因：原名称只表达“可见浏览器表单自动化”，但实际能力已经扩展为通用浏览器访问层，包括 harness 浏览器能力发现、用户可见浏览器授权与 Profile 复用、登录后页面访问、动态 DOM、网络资源解析、文件上传和表单操作。

原有表单自动化行为没有被删除；其运行规则已迁移到：

```text
productivity/browser-access/SKILL.md
```

低层 Windows Chrome/CDP、DOM、网络资源解析与跨系统文件路径参考已迁移到：

```text
productivity/browser-access/REFERENCE.md
```

新安装和后续调用统一使用 `browser-access`。本目录只保留迁移发现信息，不再新增功能。
