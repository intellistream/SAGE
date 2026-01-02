# Environment Doctor - Unbound Variable 修复说明

## 问题描述

在运行 `./quickstart.sh --doctor` 时，遇到了 `unbound variable` 错误：

```bash
/home/shuhao/SAGE/tools/install/fixes/environment_doctor.sh: line 921: AUTO_CONFIRM_FIX: unbound variable
```

## 根本原因

Bash 脚本在使用 `set -u` 或通过其他方式启用严格模式时，访问未定义的变量会导致脚本崩溃。`environment_doctor.sh` 中存在多个未初始化的变量，包括：

1. `AUTO_CONFIRM_FIX` - 用于控制是否自动确认修复操作
1. `CI`, `GITHUB_ACTIONS` - CI/CD 环境检测变量
1. `VIRTUAL_ENV`, `CONDA_DEFAULT_ENV`, `CONDA_PREFIX` - 虚拟环境检测变量
1. 其他可能未设置的环境变量

## 解决方案

### 1. 全局变量初始化

在脚本开头添加了完整的变量初始化块：

```bash
# ================================
# 全局变量初始化
# ================================
# 项目路径相关
SAGE_DIR="${SAGE_DIR:-$(pwd)/.sage}"
DOCTOR_LOG="$SAGE_DIR/logs/environment_doctor.log"

# 计数器
ISSUES_FOUND=0
FIXES_APPLIED=0
CRITICAL_ISSUES=0
NEED_RESTART_SHELL=0

# 配置选项（支持通过环境变量传入）
AUTO_CONFIRM_FIX="${AUTO_CONFIRM_FIX:-false}"

# 环境变量安全默认值（避免 unbound variable 错误）
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
CONDA_PREFIX="${CONDA_PREFIX:-}"
HOME="${HOME:-$(/usr/bin/env | grep ^HOME= | cut -d= -f2)}"
```

### 2. 使用 `${VAR:-default}` 模式

- **不使用** `set -u`，因为我们需要灵活处理环境变量
- 通过 `${VAR:-default}` 语法为所有变量提供安全默认值
- 确保即使环境变量未设置，脚本也能正常运行

### 3. 测试覆盖

创建了 `test_environment_doctor.sh` 测试套件，包括：

1. ✅ 帮助信息测试
1. ✅ 仅检查模式测试
1. ✅ 完整诊断测试
1. ✅ 环境变量安全性测试
1. ✅ CI 环境模拟测试
1. ✅ Conda 环境模拟测试
1. ✅ 虚拟环境模拟测试

所有测试均已通过。

## 验证

### 运行诊断（无错误）

```bash
./quickstart.sh --doctor
```

### 运行测试套件

```bash
bash tools/install/fixes/test_environment_doctor.sh
```

### 手动测试各种场景

```bash
# 测试帮助信息
bash tools/install/fixes/environment_doctor.sh --help

# 测试仅检查模式
bash tools/install/fixes/environment_doctor.sh --check-only

# 测试 CI 环境
CI=true GITHUB_ACTIONS=true bash tools/install/fixes/environment_doctor.sh --check-only

# 测试无环境变量场景
env -i bash tools/install/fixes/environment_doctor.sh --help
```

## 影响范围

- ✅ `tools/install/fixes/environment_doctor.sh` - 主脚本
- ✅ `tools/install/fixes/test_environment_doctor.sh` - 测试脚本（新增）

## 后续建议

1. **Pre-commit Hook**: 添加 shellcheck 检查，防止类似问题再次发生
1. **CI 测试**: 在 CI/CD 流程中运行 `test_environment_doctor.sh`
1. **文档更新**: 在 DEVELOPER.md 中添加脚本开发最佳实践

## 最佳实践

对于所有 Bash 脚本，应遵循以下原则：

1. **变量初始化**: 在脚本开头初始化所有全局变量
1. **安全访问**: 使用 `${VAR:-default}` 语法访问环境变量
1. **测试覆盖**: 为关键脚本编写测试用例
1. **错误处理**: 不盲目使用 `set -u`，而是有针对性地进行变量检查
1. **文档说明**: 在脚本中添加注释说明变量的用途和默认值

## 修复时间

- 修复日期: 2026-01-01
- 修复人: GitHub Copilot
- 测试状态: ✅ 全部通过

## 后续修复 (2026-01-01 - 第二轮)

### 问题：开发工具安装误报失败

用户报告虽然工具实际已安装，但诊断脚本仍显示"安装失败"。

**根本原因**：

1. 从外部依赖文件安装时，使用了管道 `| grep`，导致 pip 命令可能被提前终止
1. grep 匹配成功后立即返回，但实际安装状态未正确捕获

**修复方案**：

```bash
# ❌ 错误方式 - pip 输出被管道截断
if $pip_cmd install -r file.txt 2>&1 | grep -E "pattern" >/dev/null; then

# ✅ 正确方式 - 先捕获完整输出，再检查
local install_output=$($pip_cmd install -r file.txt 2>&1)
local install_status=$?
if [ $install_status -eq 0 ] || echo "$install_output" | grep -qE "pattern"; then
```

**验证**：

- ✅ 已安装的包正确识别为"已安装"
- ✅ 从外部依赖文件安装成功时显示正确消息
- ✅ 逐个安装时正确统计成功/失败数量
