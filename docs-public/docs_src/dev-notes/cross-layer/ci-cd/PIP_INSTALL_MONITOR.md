# 🔍 PIP 安装监控工具

**Date**: 2025-11-11\
**Author**: SAGE Development Team\
**Summary**: PIP installation monitoring tool to detect and prevent dependency pollution in SAGE
installation process\
**Type**: Tool Documentation\
**Status**: Completed\
**Related**: CI/CD Pipeline, Installation Process

______________________________________________________________________

## 📖 概述

`pip_install_monitor.sh` 是一个用于检测 SAGE 安装过程中依赖污染问题的监控工具。它会分析 pip 安装日志，检测是否从 PyPI 意外下载了应该使用本地版本的 SAGE
子包。

## 🎯 目的

防止在本地开发或 CI/CD 环境中，因为 `pyproject.toml` 配置错误而导致：

- 从 PyPI 下载旧版本的 SAGE 子包覆盖本地开发版本
- 版本不一致导致的功能异常
- 依赖冲突和安装失败

## 🚀 使用方法

### 1. 分析已有的安装日志

```bash
# 分析默认安装日志
./tools/install/installation_table/pip_install_monitor.sh analyze .sage/logs/install.log

# 分析自定义日志文件
./tools/install/installation_table/pip_install_monitor.sh analyze /path/to/pip.log
```

### 2. 监控 pip 命令执行

```bash
# 监控单个 pip 命令
./tools/install/installation_table/pip_install_monitor.sh monitor pip install -e packages/sage-tools

# 监控复杂的 pip 命令
./tools/install/installation_table/pip_install_monitor.sh monitor pip install packages/sage[dev]
```

### 3. 在安装脚本中集成

监控工具已经集成到 `quickstart.sh` 中，在 CI/CD 环境中会自动运行检查：

```bash
# 正常安装，在 CI 环境中会自动检查
./quickstart.sh --mode dev --yes
```

### 4. 查看帮助信息

```bash
./tools/install/installation_table/pip_install_monitor.sh --help
```

## 🔍 检测的包

监控工具会检测以下 SAGE 本地包是否被从 PyPI 下载：

- `isage-common`
- `isage-platform`
- `isage-kernel`
- `isage-libs`
- `isage-middleware`
- `isage-apps`
- `isage-benchmark`
- `isage-cli`
- `isage-studio`
- `isage-tools`
- `isage` (元包)

## 📊 输出说明

### ✅ 检查通过

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 检查通过：没有从 PyPI 下载本地包
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### ❌ 检测到违规

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 检测到 2 个违规：从 PyPI 下载了本地包！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

违规的包：
   • isage-middleware
   • isage-kernel

💡 可能的原因：
   1. pyproject.toml 中声明了不必要的本地包依赖
   2. 安装顺序错误，后安装的包依赖先安装的包
   3. 版本约束不匹配，pip 选择从 PyPI 下载
   4. 未使用 --no-deps 标志安装本地包

🔧 建议：
   1. 检查 pyproject.toml 的 dependencies 声明
   2. 确保按依赖顺序安装（L1→L2→L3→L4→L5→L6）
   3. 所有本地包使用 'pip install -e pkg --no-deps'
   4. 最后一步才安装外部依赖
```

## 🔧 CI/CD 集成

### GitHub Actions

监控工具已集成到以下 workflows：

1. **自动检查**（`main_installer.sh`）

   - 在 CI 环境中自动运行
   - 检查安装日志
   - 发现问题时设置环境变量 `DEPENDENCY_VIOLATION_DETECTED=true`

1. **独立检查 workflow**（`dependency-check.yml`）

   - 专门的依赖完整性检查
   - 生成详细报告
   - 检测到违规时导致 CI 失败

### 手动触发 CI 检查

```bash
# 通过 GitHub Actions UI 手动触发
# Workflow: "Dependency Integrity Check"
```

## 🐛 常见问题和修复

### 问题 1: sage-tools 下载 sage-middleware

**症状**：

```
⚠️  检测到从 PyPI 下载：isage-middleware
```

**原因**： `packages/sage-tools/pyproject.toml` 中错误声明了 `isage-middleware` 依赖

**修复**：

```diff
 dependencies = [
     "isage-common>=0.1.0",
-    "isage-kernel>=0.1.0",
-    "isage-middleware>=0.1.0",
-    "isage-libs>=0.1.0",
 ]
```

**详见**：`.sage/BUG_FIX_REPORT.md`

### 问题 2: 安装顺序错误

**症状**： 多个包被从 PyPI 下载

**修复**： 确保按正确的依赖顺序安装：

1. L1-L2: sage-common, sage-platform
1. L3: sage-kernel, sage-libs
1. L4: sage-middleware
1. L5: sage-apps, sage-benchmark
1. L6: sage-cli, sage-studio, sage-tools

### 问题 3: 缺少 --no-deps 标志

**症状**： 本地包在安装时触发依赖下载

**修复**：

```bash
# ❌ 错误
pip install -e packages/sage-tools

# ✅ 正确
pip install -e packages/sage-tools --no-deps
```

## 📚 相关文档

- `.sage/BUG_FIX_REPORT.md` - sage-tools 依赖 bug 修复报告
- `tools/install/installation_table/core_installer.sh` - 核心安装脚本
- `tools/install/installation_table/main_installer.sh` - 主安装控制器
- `.github/workflows/dependency-check.yml` - 依赖检查 workflow

## 🔗 返回值

- `0` - 检查通过，没有违规
- `1` - 检测到从 PyPI 下载了本地包（违规）

## 💡 最佳实践

1. **最小依赖原则**

   - 只在 `dependencies` 中声明直接使用的包
   - 避免声明传递性依赖

1. **按顺序安装**

   - 遵循 L1→L2→L3→L4→L5→L6 的顺序
   - 基础包先安装，上层包后安装

1. **使用 --no-deps**

   - 本地包安装时使用 `--no-deps`
   - 最后一步才安装外部依赖

1. **定期检查**

   - 修改 `pyproject.toml` 后运行检查
   - CI 中自动检查确保没有遗漏

## 🎓 示例场景

### 场景 1: 本地开发验证

```bash
# 安装 SAGE
./quickstart.sh --mode dev --yes

# 手动验证
./tools/install/installation_table/pip_install_monitor.sh analyze .sage/logs/install.log
```

### 场景 2: PR 提交前检查

```bash
# 修改了 pyproject.toml
# 重新安装并检查
rm -rf ~/.local/lib/python3.*/site-packages/isage*
./quickstart.sh --mode dev --yes
./tools/install/installation_table/pip_install_monitor.sh analyze .sage/logs/install.log
```

### 场景 3: 调试安装问题

```bash
# 启用详细日志
export PIP_VERBOSE=1
./quickstart.sh --mode dev --yes 2>&1 | tee debug.log

# 分析日志
./tools/install/installation_table/pip_install_monitor.sh analyze debug.log
```

## 📝 维护说明

### 添加新的本地包

如果添加了新的 SAGE 子包，需要在 `pip_install_monitor.sh` 中更新 `LOCAL_PACKAGES` 数组：

```bash
LOCAL_PACKAGES=(
    "isage-common"
    "isage-platform"
    # ... 现有包 ...
    "isage-new-package"  # 新增的包
)
```

### 修改检测规则

检测规则在 `analyze_pip_log()` 函数中定义，可以根据需要调整正则表达式。

## 🤝 贡献

发现问题或有改进建议？

1. 在 GitHub 上创建 Issue
1. 提交 Pull Request
1. 联系维护团队

______________________________________________________________________

**维护者**: SAGE Development Team\
**最后更新**: 2025-11-11
