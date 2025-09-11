# GitHub Actions Workflows - 2025-09-03

## 优化后的 Workflow 结构

### 1. `ci.yml` - 主分支 CI/CD
**触发条件**: push/PR 到 `main` 分支
**功能**:
- **quick-check**: 快速代码质量检查和基础测试（20分钟）
- **full-test**: 完整测试套件（仅PR时运行，60分钟）
- **info**: 手动测试提醒信息

### 2. `dev-ci.yml` - 开发分支 CI
**触发条件**: push/PR 到 `main-dev` 分支，push 到 `refactor/*` 分支
**功能**: 轻量级测试，适合开发阶段的快速验证（30分钟）

### 3. `only-main-dev.yml` - 分支保护
**触发条件**: PR 到 `main` 分支
**功能**: 确保只有来自 `main-dev` 的 PR 才能合并到 `main`

### 4. `todo-to-issue-pr.yml` - TODO 管理
**触发条件**: 所有 PR
**功能**: 自动将代码中的 TODO 转换为 GitHub Issues

## 优化改进

✅ **删除重复**: 移除了重复的 `test.yml`
✅ **环境变量统一**: 公共环境变量提升到 workflow 级别
✅ **分层测试**: 快速检查 + 完整测试的分层策略
✅ **超时优化**: 根据实际需要调整超时时间
✅ **并发控制**: 避免同一PR的多次CI运行冲突

## 分支策略

```
main-dev (开发分支)
    ↓ (PR触发 dev-ci.yml)
    ↓ (日常开发和测试)
    ↓
main (生产分支)
    ↓ (PR触发 ci.yml + only-main-dev.yml)
    ↓ (严格的CI检查)
    ↓ (发布)
```

## 备份文件

- `ci-backup.yml`: 原始的 ci.yml 备份（如需恢复可重命名）
