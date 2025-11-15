#!/bin/bash
# SAGE 安装包追踪工具
# 记录安装的包列表，方便后续完全卸载

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 导入颜色定义
source "$SAGE_ROOT/tools/install/display_tools/colors.sh"

# 包列表文件
PACKAGE_LIST_FILE="$SAGE_ROOT/.sage/installed_packages.txt"
INSTALL_INFO_FILE="$SAGE_ROOT/.sage/install_info.json"

# 创建 .sage 目录
mkdir -p "$SAGE_ROOT/.sage"

# 记录安装信息
record_install_info() {
    local install_mode="${1:-dev}"
    local install_environment="${2:-pip}"
    local install_vllm="${3:-false}"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    cat > "$INSTALL_INFO_FILE" <<EOF
{
  "timestamp": "$timestamp",
  "install_mode": "$install_mode",
  "install_environment": "$install_environment",
  "install_vllm": $install_vllm,
  "python_version": "$(python3 --version 2>&1 | cut -d' ' -f2)",
  "pip_version": "$(pip --version 2>&1 | awk '{print $2}')",
  "venv_name": "${SAGE_ENV_NAME:-}",
  "venv_path": "${VIRTUAL_ENV:-}",
  "conda_env": "${CONDA_DEFAULT_ENV:-}"
}
EOF

    echo -e "${DIM}✓ 安装信息已记录到: $INSTALL_INFO_FILE${NC}"
}

# 获取当前安装的 SAGE 包列表
get_sage_packages() {
    pip list 2>/dev/null | grep -E '^(sage|isage|intsage)(-|$)' | awk '{print $1}' || echo ""
}

# 记录安装前的包列表
record_pre_install_packages() {
    echo -e "${INFO} 记录安装前的包列表..."
    get_sage_packages > "$SAGE_ROOT/.sage/packages_before.txt"
}

# 记录安装后的包列表
record_post_install_packages() {
    echo -e "${INFO} 记录安装后的包列表..."
    get_sage_packages > "$PACKAGE_LIST_FILE"

    if [ -f "$SAGE_ROOT/.sage/packages_before.txt" ]; then
        # 计算新安装的包
        local before_count=$(cat "$SAGE_ROOT/.sage/packages_before.txt" | wc -l)
        local after_count=$(cat "$PACKAGE_LIST_FILE" | wc -l)
        local new_count=$((after_count - before_count))

        echo -e "${DIM}✓ 新安装了 $new_count 个 SAGE 包${NC}"
        echo -e "${DIM}✓ 包列表已保存到: $PACKAGE_LIST_FILE${NC}"

        # 清理临时文件
        rm -f "$SAGE_ROOT/.sage/packages_before.txt"
    else
        local total_count=$(cat "$PACKAGE_LIST_FILE" | wc -l)
        echo -e "${DIM}✓ 记录了 $total_count 个 SAGE 包${NC}"
        echo -e "${DIM}✓ 包列表已保存到: $PACKAGE_LIST_FILE${NC}"
    fi
}

# 显示已安装的包
show_installed_packages() {
    if [ ! -f "$PACKAGE_LIST_FILE" ]; then
        echo -e "${WARNING} 未找到包列表文件"
        echo -e "${DIM}位置: $PACKAGE_LIST_FILE${NC}"
        return 1
    fi

    echo -e "${BLUE}已安装的 SAGE 包：${NC}"
    echo ""

    local count=0
    while IFS= read -r package; do
        if [ -n "$package" ]; then
            count=$((count + 1))
            local version=$(pip show "$package" 2>/dev/null | grep "^Version:" | cut -d' ' -f2)
            echo -e "  ${DIM}$count.${NC} ${GREEN}$package${NC} ${DIM}v$version${NC}"
        fi
    done < "$PACKAGE_LIST_FILE"

    echo ""
    echo -e "${DIM}共 $count 个包${NC}"
}

# 显示安装信息
show_install_info() {
    if [ ! -f "$INSTALL_INFO_FILE" ]; then
        echo -e "${WARNING} 未找到安装信息文件"
        return 1
    fi

    echo -e "${BLUE}SAGE 安装信息：${NC}"
    echo ""

    # 使用 Python 解析 JSON（如果可用），否则使用简单的文本处理
    if command -v python3 &> /dev/null; then
        python3 -c "
import json
import sys
try:
    with open('$INSTALL_INFO_FILE', 'r') as f:
        info = json.load(f)
    print(f\"  安装时间: {info.get('timestamp', 'N/A')}\")
    print(f\"  安装模式: {info.get('install_mode', 'N/A')}\")
    print(f\"  安装环境: {info.get('install_environment', 'N/A')}\")
    print(f\"  Python 版本: {info.get('python_version', 'N/A')}\")

    venv_name = info.get('venv_name', '')
    conda_env = info.get('conda_env', '')
    if venv_name:
        print(f\"  虚拟环境: {venv_name}\")
    elif conda_env:
        print(f\"  Conda 环境: {conda_env}\")
    else:
        print(\"  虚拟环境: 系统环境\")
except Exception as e:
    print(f\"Error: {e}\", file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || {
            # Fallback to simple grep
            echo -e "  ${DIM}$(cat "$INSTALL_INFO_FILE")${NC}"
        }
    else
        cat "$INSTALL_INFO_FILE"
    fi

    echo ""
}

# 主函数
main() {
    local command="${1:-help}"

    case "$command" in
        pre-install)
            record_pre_install_packages
            ;;
        post-install)
            shift
            record_post_install_packages
            record_install_info "$@"
            ;;
        show)
            show_installed_packages
            show_install_info
            ;;
        list)
            show_installed_packages
            ;;
        info)
            show_install_info
            ;;
        help|*)
            echo "SAGE 包追踪工具"
            echo ""
            echo "用法: $0 <command> [options]"
            echo ""
            echo "命令:"
            echo "  pre-install                 记录安装前的包列表"
            echo "  post-install <mode> <env>   记录安装后的包列表和安装信息"
            echo "  show                        显示所有信息"
            echo "  list                        仅显示包列表"
            echo "  info                        仅显示安装信息"
            echo "  help                        显示此帮助"
            echo ""
            ;;
    esac
}

# 运行主函数
main "$@"
