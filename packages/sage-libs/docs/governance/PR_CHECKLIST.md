# PR 审查清单（SAGE - 包级）

- 版本：2026-01-14
- 适用范围：当前包（本文件位于 `packages/<package>/docs/governance/PR_CHECKLIST.md`）

> Maintainer/Reviewer 需要用本清单进行可量化审查。未满足项必须在 PR 中解释或补齐。

______________________________________________________________________

## 1. 架构合规

- [ ] 不产生向上依赖/循环依赖（符合 L1-L5 分层）
- [ ] 遵守 libs vs middleware 规则（需要向上能力则放 middleware）
- [ ] LLM 相关操作不绕过 Control Plane

## 2. Protocol-First（如适用）

- [ ] 公共接口/类型先定义（Protocol/ABC/Schema），实现不“绑死”具体后端
- [ ] 接口变更包含迁移说明（Breaking change 必须公告）

## 3. Mock-First

- [ ] 无 GPU 环境可跑（至少核心测试/最小路径）
- [ ] 新增外部依赖/服务调用有可测试替身（mock/fake）

## 4. Fail-Fast

- [ ] 无隐式回退（不写 try/except 吞异常、不用静默默认值掩盖缺失配置）
- [ ] 错误信息可定位（异常 message 清晰，必要时包含修复指引）

## 5. 可观测性（按适用范围）

- [ ] 关键路径有日志/指标/追踪点（至少日志）
- [ ] 不输出敏感信息（key/token/密码等）

## 6. 配置验证

- [ ] 新增配置项有校验与文档说明
- [ ] 端口不硬编码（如适用，使用统一端口配置）

## 7. 测试覆盖

- [ ] 新增/修改逻辑有对应测试
- [ ] 关键 bug fix 有回归测试

## 8. 代码质量

- [ ] `sage-dev quality check --all-files` 通过
- [ ] `sage-dev project test --coverage` 通过（或至少本包相关测试通过）
