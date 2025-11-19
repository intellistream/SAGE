#!/bin/bash
# CI/CD 安装包装脚本（可选增强）
#
# 作用说明：
#   CI/CD 已经在使用 quickstart.sh 进行安装，这个包装器是**可选的增强**，提供：
#   1. 详细的安装日志记录（便于与本地对比排查）
#   2. CI 环境验证（提前发现配置问题）
#   3. 统一的入口点（未来可扩展更多检查）
#
# 重要：
#   - 这个脚本**不改变**安装方式，只是在 quickstart.sh 外加了验证层
#   - 主要目的是提供更好的日志和诊断信息
#   - 如果不使用这个包装器，直接用 quickstart.sh 也完全可以
#
# 用法:
#   ./tools/install/ci_install_wrapper.sh [quickstart.sh 的参数]
#
# 示例:
#   ./tools/install/ci_install_wrapper.sh --dev --yes
#   ./tools/install/ci_install_wrapper.sh --core --yes
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 打印 CI 环境信息
print_ci_info() {
    echo ""
    echo -e "${BOLD}${BLUE}🤖 CI/CD 安装包装器${NC}"
    echo -e "${BLUE}确保与本地开发环境使用相同的安装方式${NC}"
    echo ""

    # 检测 CI 环境
    local ci_platform="Unknown"
    if [ -n "$GITHUB_ACTIONS" ]; then
        ci_platform="GitHub Actions"
    elif [ -n "$GITLAB_CI" ]; then
        ci_platform="GitLab CI"
    elif [ -n "$JENKINS_URL" ]; then
        ci_platform="Jenkins"
    elif [ -n "$BUILDKITE" ]; then
        ci_platform="Buildkite"
    elif [ -n "$CI" ]; then
        ci_platform="Generic CI"
    fi

    echo -e "  ${GREEN}✓${NC} CI 平台: ${BOLD}$ci_platform${NC}"
    echo -e "  ${GREEN}✓${NC} Python 版本: $(python3 --version 2>&1 | awk '{print $2}')"
    echo -e "  ${GREEN}✓${NC} 工作目录: $PWD"
    echo -e "  ${GREEN}✓${NC} SAGE 根目录: $SAGE_ROOT"
    echo ""
}

# 验证环境
validate_environment() {
    echo -e "${BLUE}📋 验证 CI 环境...${NC}"

    # 检查必需的工具
    local missing_tools=""

    for tool in python3 pip3 git; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing_tools="$missing_tools $tool"
        fi
    done

    if [ -n "$missing_tools" ]; then
        echo -e "${RED}✗ 缺少必需工具:$missing_tools${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ 所有必需工具已安装${NC}"
    echo ""
}

# 记录安装配置到日志
log_install_config() {
    local mode="$1"
    local args="${@:2}"

    local log_file="$SAGE_ROOT/.sage/logs/ci_install.log"
    mkdir -p "$(dirname "$log_file")"

    {
        echo "========================================="
        echo "CI/CD 安装记录"
        echo "========================================="
        echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "CI 平台: ${GITHUB_ACTIONS:+GitHub Actions}${GITLAB_CI:+GitLab CI}${CI:+Generic CI}"
        echo "Python 版本: $(python3 --version 2>&1)"
        echo "工作目录: $PWD"
        echo "安装模式: $mode"
        echo "完整参数: $args"
        echo "========================================="
        echo ""
    } > "$log_file"
}

# 主函数
main() {
    print_ci_info
    validate_environment

    # 确保在 SAGE 根目录
    cd "$SAGE_ROOT"

    # 记录安装配置
    log_install_config "$@"

    # 确保 quickstart.sh 可执行
    chmod +x "$SAGE_ROOT/quickstart.sh"

    echo -e "${BOLD}${BLUE}🚀 运行 quickstart.sh...${NC}"
    echo -e "参数: $*"
    echo ""

    # 运行 quickstart.sh，传递所有参数
    # 使用 tee 同时输出到终端和日志文件
    if "$SAGE_ROOT/quickstart.sh" "$@" 2>&1 | tee -a "$SAGE_ROOT/.sage/logs/ci_install.log"; then
        echo ""
        echo -e "${GREEN}${BOLD}✅ CI/CD 安装成功！${NC}"
        echo ""
        echo -e "${BLUE}📝 详细日志: .sage/logs/ci_install.log${NC}"
        echo ""

        # 验证安装
        echo -e "${BLUE}🔍 验证安装...${NC}"
        if python3 -c "import sage; print(f'SAGE version: {sage.__version__}')" 2>/dev/null; then
            echo -e "${GREEN}✓ SAGE 导入成功${NC}"
        else
            echo -e "${YELLOW}⚠ SAGE 导入失败（可能需要激活环境）${NC}"
        fi

        return 0
    else
        echo ""
        echo -e "${RED}${BOLD}❌ CI/CD 安装失败！${NC}"
        echo ""
        echo -e "${BLUE}📝 错误日志: .sage/logs/ci_install.log${NC}"
        echo -e "${BLUE}💡 提示: 这可能表明本地安装也会失败${NC}"
        echo ""
        return 1
    fi
}

# 运行主函数
main "$@"
