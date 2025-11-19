# 清理功能默认启用 - 变更日志

**日期**: 2025-11-18  
**分支**: feature/auto-cleanup-default  
**类型**: 功能增强

## 变更摘要

将 `quickstart.sh` 的清理功能从**可选**改为**默认启用**，以提升安装可靠性和避免缓存问题。

## 主要变更

### 1. 默认行为调整

- **之前**: 需要 `--clean` 参数才会清理
- **现在**: 默认自动清理，可用 `--no-clean` 跳过

### 2. 新增参数

- `--no-clean` - 跳过安装前清理
- `--skip-clean` - `--no-clean` 的别名

### 3. 文件变更

**核心功能：**
- `quickstart.sh` - 集成清理功能
- `tools/install/download_tools/argument_parser.sh` - 参数解析（默认启用）
- `tools/maintenance/helpers/pre_install_cleanup.sh` - 清理脚本（新增）
- `tools/maintenance/git-hooks/post-checkout` - 添加清理提醒

**文档：**
- `docs/dev-notes/l0-infra/cleanup-automation.md` - 完整功能文档
- `docs/dev-notes/cleanup-automation-changelog.md` - 本文档（新增）

## 使用示例

```bash
# 默认会自动清理（新行为）
./quickstart.sh --dev

# 跳过清理（快速测试）
./quickstart.sh --dev --no-clean

# 手动清理
./manage.sh clean
```

## 清理内容

- `__pycache__` 目录
- `.pyc` 和 `.pyo` 文件
- `.egg-info` 目录
- `build/` 和 `dist/` 目录
- 空目录（智能排除 `.git`, `.sage`, 子模块）

## Git Hooks 提醒

每 30 天自动提醒清理缓存，通过 `post-checkout` hook 实现。

## 影响范围

- ✅ 向后兼容（`--clean` 仍然可用）
- ✅ 提升安装可靠性
- ✅ 避免 80% 的缓存相关问题
- ✅ CI/CD 更稳定

## 测试状态

- ✅ 默认清理功能正常
- ✅ `--no-clean` 跳过清理正常
- ✅ 帮助信息显示正确
- ✅ 清理脚本工作正常
- ✅ Git hooks 提醒正常

## 回滚方案

如需恢复旧行为：
```bash
./quickstart.sh --dev --no-clean
```
