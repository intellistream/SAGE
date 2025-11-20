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
    "isage-gateway"
    "isage"
)

# 分析 pip 日志文件
analyze_pip_log() {
    local log_file="$1"
    local violations=()
    local found_downloads=false
    local debug_output=""  # 收集DEBUG信息，只在出错时打印

    echo -e "${BLUE}🔍 检查 pip 安装日志：${log_file}${NC}"
    echo ""

    # 收集DEBUG信息（不立即打印）
    debug_output+="${BLUE}🐛 DEBUG - 环境信息：${NC}"$'\n'
    debug_output+="   日志文件: ${log_file}"$'\n'
    debug_output+="   文件大小: $(wc -c < "$log_file" 2>/dev/null || echo "N/A") bytes"$'\n'
    debug_output+="   文件行数: $(wc -l < "$log_file" 2>/dev/null || echo "N/A") lines"$'\n'
    debug_output+="   CI 环境: ${CI:-false} (GITHUB_ACTIONS=${GITHUB_ACTIONS:-false})"$'\n'
    debug_output+=$'\n'

    if [ ! -f "$log_file" ]; then
        echo -e "${RED}❌ 日志文件不存在：${log_file}${NC}"
        return 1
    fi

    # 收集待检测包列表
    debug_output+="${BLUE}🐛 DEBUG - 待检测的本地包：${NC}"$'\n'
    for pkg in "${LOCAL_PACKAGES[@]}"; do
        debug_output+="   • ${pkg}"$'\n'
    done
    debug_output+=$'\n'

    # 检测是否从 PyPI 下载了本地包
    for package in "${LOCAL_PACKAGES[@]}"; do
        # 检查各种下载模式
        # 1. "Downloading isage-xxx-0.1.0.tar.gz"
        # 2. "Collecting isage-xxx" (从 PyPI)
        # 3. "Downloading https://files.pythonhosted.org/.../isage-xxx"

        echo -e "${BLUE}🐛 DEBUG - 检查包: ${package}${NC}"

        # 显示所有匹配行（包括被排除的）
        local all_matches=$(grep -E "(Downloading|Collecting).*${package}[-_]" "$log_file" || true)
        local excluded_matches=$(grep -E "(Downloading|Collecting).*${package}[-_]" "$log_file" | grep -E "(editable|file://|/packages/)" || true)
        local violation_matches=$(grep -E "(Downloading|Collecting).*${package}[-_]" "$log_file" | grep -vE "(editable|file://|/packages/)" || true)

        if [ -n "$all_matches" ]; then
            echo -e "${YELLOW}   所有匹配（$(echo "$all_matches" | wc -l) 行）：${NC}"
            echo "$all_matches" | head -n 3 | sed 's/^/     /'
            if [ $(echo "$all_matches" | wc -l) -gt 3 ]; then
                echo "     ... (省略 $(($(echo "$all_matches" | wc -l) - 3)) 行)"
            fi
        fi

        if [ -n "$excluded_matches" ]; then
            echo -e "${GREEN}   排除的匹配（$(echo "$excluded_matches" | wc -l) 行 - editable/file:// 等）：${NC}"
            echo "$excluded_matches" | head -n 2 | sed 's/^/     /'
        fi

        if [ -n "$violation_matches" ]; then
            found_downloads=true
            echo -e "${RED}   ⚠️  违规匹配（$(echo "$violation_matches" | wc -l) 行 - 从 PyPI 下载）：${NC}"
            echo "$violation_matches" | sed 's/^/     /'
            echo ""
            violations+=("${package}")
        else
            echo -e "${GREEN}   ✓ 通过检查${NC}"
        fi
        echo ""
    done

    # 额外检查：从 PyPI 下载任何 sage/isage 相关包
    echo -e "${BLUE}📊 所有下载记录（包括合法的外部依赖）：${NC}"
    local download_count=$(grep -cE "Downloading.*\.(whl|tar\.gz)" "$log_file" || echo "0")
    echo "   总下载数: $download_count"
    if [ "$download_count" -gt 0 ]; then
        echo "   前 20 条下载："
        grep -E "Downloading.*\.(whl|tar\.gz)" "$log_file" | head -n 20 | sed 's/^/     /'
        echo ""
    else
        echo -e "${GREEN}   （没有下载记录或文件为空）${NC}"
        echo ""
    fi

    # 检查 editable 安装（应该有）
    echo -e "${BLUE}📦 Editable 安装记录（应该存在）：${NC}"
    local editable_count=$(grep -cE "(Installing|Preparing|Building).*editable" "$log_file" || echo "0")
    echo "   Editable 安装数: $editable_count"
    if [ "$editable_count" -gt 0 ]; then
        echo "   前 10 条记录："
        grep -E "(Installing|Preparing|Building).*editable" "$log_file" | head -n 10 | sed 's/^/     /'
        echo ""
    else
        echo -e "${YELLOW}   ⚠️  没有找到 editable 安装记录${NC}"
        echo ""
    fi

    # DEBUG: 显示日志文件的关键统计
    echo -e "${BLUE}🐛 DEBUG - 日志文件统计：${NC}"
    echo "   'Downloading' 出现次数: $(grep -c "Downloading" "$log_file" || echo "0")"
    echo "   'Collecting' 出现次数: $(grep -c "Collecting" "$log_file" || echo "0")"
    echo "   'Installing' 出现次数: $(grep -c "Installing" "$log_file" || echo "0")"
    echo "   'editable' 出现次数: $(grep -c "editable" "$log_file" || echo "0")"
    echo "   包含 'sage' 的行数: $(grep -ci "sage" "$log_file" || echo "0")"
    echo ""

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

        echo -e "${YELLOW}🐛 DEBUG - 详细诊断信息：${NC}"
        echo "   日志文件: ${log_file}"
        echo "   检测模式: grep -E \"(Downloading|Collecting).*PACKAGE[-_]\" | grep -vE \"(editable|file://|/packages/)\""
        echo ""

        echo -e "${YELLOW}🔍 原始匹配详情（每个违规包）：${NC}"
        for pkg in "${violations[@]}"; do
            echo "   === ${pkg} ==="
            grep -E "(Downloading|Collecting).*${pkg}[-_]" "$log_file" | \
                grep -vE "(editable|file://|/packages/)" | \
                sed 's/^/     /' || echo "     （无法重现匹配，可能是并发问题）"
            echo ""
        done

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
