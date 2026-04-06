#!/bin/bash
# C++ 扩展库修复工具
# 处理 editable install 模式下 C++ 扩展库(.so)的安装问题

# 加载日志和颜色函数（logging.sh 会自动 source colors.sh）
source "$(dirname "${BASH_SOURCE[0]}")/../ui/logging.sh"

# 修复独立适配器 C++ 扩展安装问题（当前仅保留提示功能）

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

fix_middleware_cpp_extensions() {
    # 注意: C++ 扩展已迁移为独立 PyPI 包，不再由主仓修复脚本直接处理
    # - isage-vdb (was sageVDB)
    # - isage-flow (was sageFlow)
    # - isage-tsdb (was sageTSDB)
    # 主仓只保留核心 stream/runtime surface

    log_info "C++ 扩展已迁移为独立 PyPI 包，跳过修复" "CPPExtFix"
    echo -e "${DIM}ℹ️  C++ 扩展（sageVDB/sageFlow/sageTSDB）已迁移为独立 PyPI 包${NC}"
    echo -e "${DIM}   如需使用，请分别安装 isage-vdb / isage-flow / isage-tsdb${NC}"
    return 0
}

# 导出函数供其他脚本使用
export -f fix_middleware_cpp_extensions
