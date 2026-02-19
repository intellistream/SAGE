## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring
- [ ] Documentation
- [ ] Flownet → SAGE migration

---

## Flownet → SAGE Migration Compliance Checklist

> **只有当本 PR 涉及 Flownet → SAGE 迁移时，才需要填写本节。**
> **引用权威边界文档**: [intellistream/SAGE#1430](https://github.com/intellistream/SAGE/issues/1430)

### 本 PR 迁移了什么（What Moved）

<!-- 列出迁移的模块/类/函数，格式：`flownet.x.y` → `sage.z.w` -->

- [ ] _填写迁移制品列表_

### 本 PR 中什么留在 Flownet（What Stayed）

<!-- 列出明确保留在 Flownet 的制品及原因 -->

- [ ] _填写保留制品及原因_

### 边界验证（Why It's Correct）

- [ ] 已对照[迁移矩阵](https://github.com/intellistream/SAGE/issues/1430)验证，迁移制品属于**声明/API/协议抽象层**
- [ ] 迁移制品**不包含**任何运行时核心实现（执行循环、传输层、Actor 分发等）
- [ ] Flownet 源位置旧代码**已删除**，无 shim 层、重导出层或兼容 wrapper
- [ ] 所有调用方的 import 路径已更新
- [ ] 迁移声明层的单元测试在**无运行时核心依赖**的情况下通过

---

## Testing

- [ ] Unit tests pass (`sage-dev project test`)
- [ ] Quality checks pass (`sage-dev quality --check-only`)

## Notes

<!-- Any additional context or notes for reviewers -->
