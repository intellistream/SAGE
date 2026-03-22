#!/bin/bash
# 检查并修复 SAGE 依赖冲突
# 这个脚本可以被其他脚本调用，也可以独立运行
#
# 用法:
#   source tools/install/check_and_fix_dependencies.sh
#   check_and_fix_dependencies [--non-interactive]
#
# 或者直接运行:
#   ./tools/install/check_and_fix_dependencies.sh [--non-interactive]

# 检查并修复依赖

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
BASH_SOURCE="${BASH_SOURCE:-}"
# ============================================================================

check_and_fix_dependencies() {
    local non_interactive=false

    # 解析参数
    for arg in "$@"; do
        case $arg in
            --non-interactive|-y)
                non_interactive=true
                ;;
        esac
    done

    # 获取脚本目录
    local script_dir
    if [ -n "${BASH_SOURCE[0]}" ]; then
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    else
        script_dir="$(pwd)/tools/install/diagnostics"
    fi
    local project_root="$(cd "$script_dir/../../.." && pwd)"

    # 检查 Python 是否可用
    if ! command -v python &> /dev/null; then
        echo "❌ 错误: Python 未安装或不在 PATH 中"
        return 1
    fi

    # 运行依赖验证脚本
    local verify_script="$project_root/tools/install/diagnostics/verify_dependencies.py"
    if [ ! -f "$verify_script" ]; then
        echo "⚠️  警告: 依赖验证脚本不存在: $verify_script"
        return 0
    fi

    # 静默检查（只获取退出码）
    if python "$verify_script" > /dev/null 2>&1; then
        echo "✅ 所有依赖版本正确"
        return 0
    fi

    # 依赖有问题，显示详细信息
    echo "⚠️  检测到依赖版本问题"
    python "$verify_script" 2>&1 | grep -E "❌|⚠️|版本不兼容|不可用" || true
    echo

    # 询问是否修复（非交互模式下自动修复）
    local should_fix=false
    if [ "$non_interactive" = true ]; then
        echo "🔧 非交互模式：自动修复依赖冲突"
        should_fix=true
    else
        read -p "是否自动修复依赖冲突？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            should_fix=true
        fi
    fi

    if [ "$should_fix" = true ]; then
        local fix_script="$project_root/tools/install/maintenance/fix_torch.sh"
        if [ ! -f "$fix_script" ]; then
            echo "❌ 错误: 修复脚本不存在: $fix_script"
            return 1
        fi

        # 运行修复脚本
        if [ "$non_interactive" = true ]; then
            bash "$fix_script" --non-interactive
        else
            bash "$fix_script"
        fi

        return $?
    else
        echo "ℹ️  跳过自动修复。你可以稍后手动运行:"
        echo "   ./tools/install/maintenance/fix_torch.sh"
        return 0
    fi
}

# 如果脚本被直接执行（而不是被 source）
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    check_and_fix_dependencies "$@"
fi
