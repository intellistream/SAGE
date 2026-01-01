#!/bin/bash
# 测试 environment_doctor.sh 脚本的所有功能
# 确保没有 unbound variable 错误


# ============================================================================
# 环境变量安全默认值（防止 set -u 报错）
# ============================================================================
CI="${CI:-}"
GITHUB_ACTIONS="${GITHUB_ACTIONS:-}"
GITLAB_CI="${GITLAB_CI:-}"
JENKINS_URL="${JENKINS_URL:-}"
BUILDKITE="${BUILDKITE:-}"
VIRTUAL_ENV="${VIRTUAL_ENV:-}"
CONDA_DEFAULT_ENV="${CONDA_DEFAULT_ENV:-}"
SAGE_FORCE_CHINA_MIRROR="${SAGE_FORCE_CHINA_MIRROR:-}"
SAGE_DEBUG_OFFSET="${SAGE_DEBUG_OFFSET:-}"
SAGE_CUSTOM_OFFSET="${SAGE_CUSTOM_OFFSET:-}"
LANG="${LANG:-en_US.UTF-8}"
LC_ALL="${LC_ALL:-${LANG}}"
LC_CTYPE="${LC_CTYPE:-${LANG}}"
# ============================================================================

set -e  # 遇到错误立即退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCTOR_SCRIPT="$SCRIPT_DIR/environment_doctor.sh"

echo "=========================================="
echo "测试 environment_doctor.sh"
echo "=========================================="

# 测试 1: 帮助信息
echo ""
echo "测试 1: 显示帮助信息"
echo "----------"
bash "$DOCTOR_SCRIPT" --help >/dev/null 2>&1 && echo "✓ 帮助信息测试通过" || echo "✗ 帮助信息测试失败"

# 测试 2: 仅检查模式
echo ""
echo "测试 2: 仅检查模式"
echo "----------"
AUTO_CONFIRM_FIX=false bash "$DOCTOR_SCRIPT" --check-only >/dev/null 2>&1 && echo "✓ 仅检查模式测试通过" || echo "✗ 仅检查模式测试失败"

# 测试 3: 完整诊断（无自动修复）
echo ""
echo "测试 3: 完整诊断（自动拒绝修复）"
echo "----------"
# 模拟用户输入 'n' 拒绝修复
echo "n" | AUTO_CONFIRM_FIX=false bash "$DOCTOR_SCRIPT" >/dev/null 2>&1 && echo "✓ 完整诊断测试通过" || echo "✗ 完整诊断测试失败"

# 测试 4: 环境变量安全性测试
echo ""
echo "测试 4: 环境变量安全性测试"
echo "----------"
# 取消设置所有可能的环境变量，确保脚本使用默认值
(
    unset CI GITHUB_ACTIONS VIRTUAL_ENV CONDA_DEFAULT_ENV CONDA_PREFIX AUTO_CONFIRM_FIX
    bash "$DOCTOR_SCRIPT" --help >/dev/null 2>&1
) && echo "✓ 环境变量安全性测试通过" || echo "✗ 环境变量安全性测试失败"

# 测试 5: CI 环境模拟
echo ""
echo "测试 5: CI 环境模拟"
echo "----------"
(
    export CI=true
    export GITHUB_ACTIONS=true
    bash "$DOCTOR_SCRIPT" --check-only >/dev/null 2>&1
) && echo "✓ CI 环境模拟测试通过" || echo "✗ CI 环境模拟测试失败"

# 测试 6: Conda 环境模拟
echo ""
echo "测试 6: Conda 环境模拟"
echo "----------"
(
    export CONDA_DEFAULT_ENV=test-env
    export CONDA_PREFIX=/some/path
    bash "$DOCTOR_SCRIPT" --check-only >/dev/null 2>&1
) && echo "✓ Conda 环境模拟测试通过" || echo "✗ Conda 环境模拟测试失败"

# 测试 7: 虚拟环境模拟
echo ""
echo "测试 7: 虚拟环境模拟"
echo "----------"
(
    export VIRTUAL_ENV=/some/venv
    bash "$DOCTOR_SCRIPT" --check-only >/dev/null 2>&1
) && echo "✓ 虚拟环境模拟测试通过" || echo "✗ 虚拟环境模拟测试失败"

echo ""
echo "=========================================="
echo "所有测试完成."
echo "=========================================="
