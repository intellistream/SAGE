# SAGE 子模块管理策略

## 📋 概述

为了解决频繁的子模块PR冲突问题，我们建立了stable分支策略。

## 🌿 分支策略

### 子模块仓库分支:
- **`main`**: 独立开发者的主分支，日常开发在此进行
- **`stable`**: 主仓库追踪的稳定分支，定期从main合并
- **`release/*`**: 版本发布分支（可选）

### 主仓库追踪:
- 主仓库的子模块配置追踪各子模块的`stable`分支
- 减少因频繁main分支更新导致的PR冲突

## 👥 工作流程

### 对于独立开发者（在子模块仓库工作）:

1. **正常开发**:
   ```bash
   # 在子模块仓库（如sageDB）中
   git checkout main
   git pull origin main
   # 正常开发、提交、推送
   ```

2. **标记稳定版本**:
   ```bash
   # 功能完成后，合并到stable分支
   git checkout stable
   git merge main
   git push origin stable
   ```

3. **通知同步**: 通知主仓库维护者进行同步

### 对于主仓库维护者:

1. **检查子模块状态**:
   ```bash
   ./tools/maintenance/submodule_sync.sh status
   ```

2. **安全更新子模块**:
   ```bash
   ./tools/maintenance/submodule_sync.sh update
   ```

3. **锁定版本**（发布前）:
   ```bash
   ./tools/maintenance/submodule_sync.sh lock
   ```

## 🛠️ 工具使用

### submodule_sync.sh 脚本

```bash
# 检查所有子模块状态
./tools/maintenance/submodule_sync.sh status

# 交互式更新子模块
./tools/maintenance/submodule_sync.sh update

# 锁定当前版本
./tools/maintenance/submodule_sync.sh lock

# 显示帮助
./tools/maintenance/submodule_sync.sh help
```

## 📦 版本管理

### 版本锁定
在重要版本发布前，使用版本锁定功能:
```bash
./tools/maintenance/submodule_sync.sh lock
```

这会生成`submodule-lock.json`文件，记录确切的子模块版本。

### 回滚支持
如果需要回滚到特定版本:
```bash
# 基于lock文件恢复特定版本（需要手动实现）
git submodule update --init --recursive
```

## 🔄 同步时机

### 建议的同步频率:
- **日常开发**: 不频繁更新子模块
- **每周同步**: 定期同步stable分支的更新
- **版本发布前**: 锁定所有子模块版本
- **紧急修复**: 按需同步关键修复

## 🚨 注意事项

1. **避免直接在main分支更新子模块**: 这会导致其他PR冲突
2. **使用脚本管理**: 通过`submodule_sync.sh`而非手动操作
3. **清晰的提交信息**: 子模块更新要有清晰的说明
4. **协调沟通**: 大的子模块更新前要与团队协调

## 🎯 预期效果

- ✅ **减少PR冲突**: 不再频繁更新子模块
- ✅ **独立开发**: 开发者可以在各自仓库正常工作
- ✅ **规范管理**: 标准化的同步流程
- ✅ **版本控制**: 支持锁定和回滚
- ✅ **提升效率**: 减少合并冲突的处理时间

## 📚 相关文件

- `.gitmodules` - 子模块配置
- `tools/maintenance/submodule_sync.sh` - 同步管理脚本
- `submodule-versions.json` - 版本记录配置
- `submodule-lock.json` - 版本锁定文件（生成）

## 🆘 故障排除

### 常见问题:

1. **子模块状态不一致**:
   ```bash
   git submodule update --remote --merge
   ```

2. **分支切换失败**:
   ```bash
   cd submodule_path
   git fetch origin
   git checkout stable
   ```

3. **恢复到main分支追踪**:
   ```bash
   # 编辑 .gitmodules，将branch改回main
   git submodule sync
   git submodule update --remote
   ```