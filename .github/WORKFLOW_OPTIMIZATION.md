# GitHub Actions 工作流优化说明

## 🎯 优化目标
减少重复运行，提高CI效率，明确工作流职责分工。

## 📋 工作流分工

### 1. `ci.yml` - 主分支CI
- **触发条件**: 
  - Push到 `main` 分支
  - PR到 `main` 分支
- **用途**: 生产环境发布前的最终验证
- **运行频率**: 仅在准备发布时

### 2. `dev-ci.yml` - 开发CI  
- **触发条件**:
  - Push到 `main-dev` 分支
  - PR到 `main-dev` 分支（包括从 `refactor/*` 分支创建的PR）
- **用途**: 日常开发的CI/CD管道
- **运行频率**: 开发过程中频繁运行
- **优化**: 移除了对 `refactor/*` 分支push的监听，避免与PR事件重复触发

### 3. `todo-to-issue-pr.yml` - TODO转Issue
- **触发条件**:
  - PR首次打开 (`opened`)
  - PR重新打开 (`reopened`)
  - 手动触发 (`workflow_dispatch`)
- **用途**: 扫描代码中的TODO注释并转换为GitHub Issues
- **运行频率**: 仅在PR生命周期的关键节点

### 4. `only-main-dev.yml` - 分支保护
- **触发条件**: PR到 `main` 分支
- **用途**: 确保只有从 `main-dev` 分支创建的PR才能合并到 `main`
- **运行频率**: 每次有PR到main时

## 🔧 优化措施

### 1. 消除重复触发
**问题**: 推送到 `refactor/*` 分支时，如果该分支有PR到 `main-dev`，会同时触发：
- Push事件 → `dev-ci.yml` 
- PR synchronize事件 → `dev-ci.yml`

**解决方案**: 移除对 `refactor/*` 分支push事件的监听，只通过PR事件触发CI。

### 2. 并发控制
所有工作流都添加了 `concurrency` 控制：
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
- 同一分支/PR只运行最新的工作流
- 自动取消过期的运行

### 3. 精确的触发条件
- 明确指定目标分支
- 限制触发的PR事件类型
- 避免不必要的重复运行

### 4. 分支策略优化
- `ci.yml`: 只关注 `main` 分支（生产）
- `dev-ci.yml`: 专注主开发分支 `main-dev` 和相关PR
- **关键优化**: `refactor/*` 分支只通过PR触发CI，不会因push事件重复运行
- 明确分离开发和生产CI

## 🚀 预期效果

1. **减少重复运行**: 每个PR事件最多触发2-3个工作流（而非之前的4个）
2. **快速反馈**: 并发控制确保开发者看到最新代码的CI结果
3. **资源节约**: 减少不必要的CI消耗
4. **清晰职责**: 每个工作流有明确的用途和时机

## 📊 运行矩阵

| 事件 | ci.yml | dev-ci.yml | todo-to-issue-pr.yml | only-main-dev.yml |
|------|--------|------------|---------------------|-------------------|
| Push to `main` | ✅ | ❌ | ❌ | ❌ |
| Push to `main-dev` | ❌ | ✅ | ❌ | ❌ |
| Push to `refactor/*` | ❌ | ❌ | ❌ | ❌ |
| PR to `main` | ✅ | ❌ | ✅ (仅opened/reopened) | ✅ |
| PR to `main-dev` | ❌ | ✅ | ✅ (仅opened/reopened) | ❌ |
| PR `refactor/*` → `main-dev` | ❌ | ✅ | ✅ (仅opened/reopened) | ❌ |

## 💡 使用建议

### 典型开发流程示例
1. **创建功能分支**: `git checkout -b refactor/new-feature`
2. **开发过程**: 多次推送到 `refactor/new-feature` 
   - ✅ **不会触发CI** (避免不必要的资源消耗)
3. **创建PR**: `refactor/new-feature` → `main-dev`
   - ✅ **触发 `dev-ci.yml`** (PR opened)
   - ✅ **触发 `todo-to-issue-pr.yml`** (扫描TODO)
4. **后续推送**: 继续推送到 `refactor/new-feature`
   - ✅ **触发 `dev-ci.yml`** (PR synchronize，测试最新代码)
   - ❌ **不会重复触发** (因为没有push事件监听)

### 分支使用建议

1. **日常开发**: 主要关注 `dev-ci.yml` 的结果
2. **PR创建**: 检查所有相关工作流是否通过
3. **发布准备**: 重点关注 `ci.yml` 的结果
4. **问题排查**: 根据工作流职责定位问题源头