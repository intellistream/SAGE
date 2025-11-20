#!/bin/bash
# 🔍 PIP 安装监控器 - 检测不应该从 PyPI 下载的本地包
# 用于 CI/CD 检测安装过程中的依赖污染问题

set -euo pipefail

# 导入颜色定义（如果可用）
if [ -f "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh" ]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"
else
    # 简单定义
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# 本地 SAGE 包列表（不应该从 PyPI 下载）
LOCAL_PACKAGES=(
    "isage-common"
    "isage-platform"
    "isage-kernel"
    "isage-libs"
    "isage-middleware"
    "isage-apps"
    "isage-benchmark"
    "isage-cli"
    "isage-studio"
    "isage-tools"
    "sage-gateway"
    "isage"
)

# 分析 pip 日志文件
analyze_pip_log() {
    local log_file="$1"
    local violations=()
    local found_downloads=false

    echo -e "${BLUE}🔍 检查 pip 安装日志：${log_file}${NC}"
    echo ""

    if [ ! -f "$log_file" ]; then
        echo -e "${RED}❌ 日志文件不存在：${log_file}${NC}"
        return 1
    fi

    # 检测是否从 PyPI 下载了本地包
    for package in "${LOCAL_PACKAGES[@]}"; do
        # 检查各种下载模式
        # 1. "Downloading isage-xxx-0.1.0.tar.gz"
        # 2. "Collecting isage-xxx" (从 PyPI)
        # 3. "Downloading https://files.pythonhosted.org/.../isage-xxx"

        if grep -E "(Downloading|Collecting).*${package}[-_]" "$log_file" | grep -vE "(editable|file://|/packages/)" | grep -q .; then
            found_downloads=true

            echo -e "${RED}⚠️  检测到从 PyPI 下载：${package}${NC}"
            echo -e "${YELLOW}   匹配的日志行：${NC}"

            # 显示相关日志行
            grep -E "(Downloading|Collecting).*${package}[-_]" "$log_file" | \
                grep -vE "(editable|file://|/packages/)" | \
                sed 's/^/     /' || true

            echo ""
            violations+=("${package}")
        fi
    done

    # 额外检查：从 PyPI 下载任何 sage/isage 相关包
    echo -e "${BLUE}📊 所有下载记录（包括合法的外部依赖）：${NC}"
    if grep -E "Downloading.*\.(whl|tar\.gz)" "$log_file" | head -n 20; then
        echo ""
    else
        echo -e "${GREEN}   （没有下载记录或文件为空）${NC}"
        echo ""
    fi

    # 检查 editable 安装（应该有）
    echo -e "${BLUE}📦 Editable 安装记录（应该存在）：${NC}"
    if grep -E "(Installing|Preparing|Building).*editable" "$log_file" | head -n 10; then
        echo ""
    else
        echo -e "${YELLOW}   ⚠️  没有找到 editable 安装记录${NC}"
        echo ""
    fi

    # 返回结果
    if [ ${#violations[@]} -gt 0 ]; then
        echo ""
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ 检测到 ${#violations[@]} 个违规：从 PyPI 下载了本地包！${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${YELLOW}违规的包：${NC}"
        printf '   • %s\n' "${violations[@]}"
        echo ""
        echo -e "${YELLOW}💡 可能的原因：${NC}"
        echo "   1. pyproject.toml 中声明了不必要的本地包依赖"
        echo "   2. 安装顺序错误，后安装的包依赖先安装的包"
        echo "   3. 版本约束不匹配，pip 选择从 PyPI 下载"
        echo "   4. 未使用 --no-deps 标志安装本地包"
        echo ""
        echo -e "${YELLOW}🔧 建议：${NC}"
        echo "   1. 检查 pyproject.toml 的 dependencies 声明"
        echo "   2. 确保按依赖顺序安装（L1→L2→L3→L4→L5→L6）"
        echo "   3. 所有本地包使用 'pip install -e pkg --no-deps'"
        echo "   4. 最后一步才安装外部依赖"
        echo ""
        return 1
    else
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✅ 检查通过：没有从 PyPI 下载本地包${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        return 0
    fi
}

# 实时监控 pip 命令
monitor_pip_command() {
    local pip_cmd="$@"
    local temp_log=$(mktemp)

    echo -e "${BLUE}🔍 监控 pip 命令：${NC}"
    echo "   $pip_cmd"
    echo ""

    # 执行 pip 命令并捕获输出
    if $pip_cmd 2>&1 | tee "$temp_log"; then
        cmd_status=$?
    else
        cmd_status=$?
    fi

    # 分析输出
    analyze_pip_log "$temp_log"
    analysis_status=$?

    # 清理
    rm -f "$temp_log"

    # 如果任一失败则返回失败
    if [ $cmd_status -ne 0 ] || [ $analysis_status -ne 0 ]; then
        return 1
    fi

    return 0
}

# 主函数
main() {
    local mode="${1:-analyze}"

    case "$mode" in
        analyze)
            # 分析现有日志文件
            if [ $# -lt 2 ]; then
                echo "用法: $0 analyze <log_file>"
                echo ""
                echo "示例："
                echo "  $0 analyze .sage/logs/install.log"
                exit 1
            fi
            analyze_pip_log "$2"
            ;;

        monitor)
            # 监控 pip 命令
            if [ $# -lt 2 ]; then
                echo "用法: $0 monitor <pip_command...>"
                echo ""
                echo "示例："
                echo "  $0 monitor pip install -e packages/sage-tools"
                exit 1
            fi
            shift  # 移除 'monitor' 参数
            monitor_pip_command "$@"
            ;;

        help|--help|-h)
            cat <<EOF
${BLUE}PIP 安装监控器${NC} - 检测不应该从 PyPI 下载的本地包

${YELLOW}用法：${NC}
  $0 analyze <log_file>        分析已有的 pip 日志文件
  $0 monitor <pip_command>     监控 pip 命令执行并分析输出

${YELLOW}示例：${NC}
  # 分析安装日志
  $0 analyze .sage/logs/install.log

  # 监控 pip 安装命令
  $0 monitor pip install -e packages/sage-tools

  # 在 CI/CD 中使用
  ./tools/install/installation_table/pip_install_monitor.sh analyze .sage/logs/install.log

${YELLOW}检测的包：${NC}
$(printf '  • %s\n' "${LOCAL_PACKAGES[@]}")

${YELLOW}返回值：${NC}
  0 - 检查通过，没有违规
  1 - 检测到从 PyPI 下载了本地包（违规）

EOF
            ;;

        *)
            echo -e "${RED}未知模式：$mode${NC}"
            echo "使用 '$0 --help' 查看帮助"
            exit 1
            ;;
    esac
}

# 执行主函数
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi
