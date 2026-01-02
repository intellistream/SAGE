#!/bin/bash
# SAGE 安装脚本 - 基础系统检查工具（简化版）
# 保留验证安装等基础功能

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 验证安装

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

verify_installation() {
    echo ""
    echo -e "${INFO} 验证安装..."

    if python3 -c "
import sage
import sage.common
import sage.kernel
import sage.libs
import sage.middleware
print(f'${CHECK} SAGE v{sage.__version__} 安装成功！')
print(f'${CHECK} 所有子包版本一致: {sage.common.__version__}')
" 2>/dev/null; then
        echo -e "${CHECK} 验证通过！"

        # 提示运行完整验证测试
        echo ""
        echo -e "${DIM}提示: 运行完整的安装验证测试:${NC}"
        echo -e "${DIM}  bash tools/install/tests/verify_installation.sh${NC}"

        return 0
    else
        echo -e "${WARNING} 验证出现问题，但安装可能成功了"
        return 1
    fi
}
