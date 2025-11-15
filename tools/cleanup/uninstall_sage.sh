#!/bin/bash
# SAGE 卸载与清理工具
# 使用安装记录和环境信息，帮助用户一键卸载 SAGE 及其虚拟环境

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TRACK_SCRIPT="$SCRIPT_DIR/track_install.sh"
INSTALL_INFO_FILE="$SAGE_ROOT/.sage/install_info.json"
PACKAGE_LIST_FILE="$SAGE_ROOT/.sage/installed_packages.txt"

# 颜色定义（尽量复用安装脚本风格）
if [ -f "$SAGE_ROOT/tools/install/display_tools/colors.sh" ]; then
    # shellcheck source=/dev/null
    source "$SAGE_ROOT/tools/install/display_tools/colors.sh"
else
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'
    INFO="[i]"; WARNING="[!]"; CHECK="[✓]"; CROSS="[x]"
fi

AUTO_YES=false

# 安全提示
print_header() {
    echo -e "${BLUE}${BOLD}SAGE 卸载与清理工具${NC}"
    echo ""
    echo -e "${DIM}此工具将帮助你:${NC}"
    echo -e "  • 卸载通过 quickstart.sh 安装的 SAGE Python 包"
    echo -e "  • 可选：删除为 SAGE 创建的虚拟环境 (.sage/venv 或 Conda 环境)"
    echo -e "  • 保留项目源码和 Git 仓库本身${NC}"
    echo ""
}

confirm() {
    local prompt="$1"
    local default_yes="${2:-false}"

    if [ "$AUTO_YES" = true ]; then
        echo -e "${DIM}自动确认已启用，继续执行: $prompt${NC}"
        return 0
    fi

    if [ "$default_yes" = true ]; then
        read -p "$prompt [Y/n]: " -r ans
        if [[ -z "$ans" || "$ans" =~ ^[Yy]$ ]]; then
            return 0
        fi
        return 1
    else
        read -p "$prompt [y/N]: " -r ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            return 0
        fi
        return 1
    fi
}

uninstall_packages_from_list() {
    if [ ! -f "$PACKAGE_LIST_FILE" ]; then
        echo -e "${YELLOW}未找到包列表文件，回退到自动检测模式${NC}"
        if [ -f "$SAGE_ROOT/tools/install/examination_tools/sage_check.sh" ]; then
            # shellcheck source=/dev/null
            source "$SAGE_ROOT/tools/install/examination_tools/sage_check.sh"
            uninstall_sage
            return
        else
            echo -e "${RED}未找到卸载逻辑脚本，无法安全卸载${NC}"
            exit 1
        fi
    fi

    echo -e "${INFO} 根据安装记录卸载 SAGE 相关包..."
    local uninstall_count=0
    local total_count=0

    while IFS= read -r package; do
        [ -z "$package" ] && continue
        total_count=$((total_count + 1))
        if pip show "$package" >/dev/null 2>&1; then
            if pip uninstall "$package" -y >/dev/null 2>&1; then
                echo -e "${DIM}  ✓ 已卸载 $package${NC}"
                uninstall_count=$((uninstall_count + 1))
            else
                echo -e "${DIM}  ⚠ 卸载 $package 失败${NC}"
            fi
        else
            echo -e "${DIM}  - $package 未安装，跳过${NC}"
        fi
    done < "$PACKAGE_LIST_FILE"

    echo ""
    echo -e "${CHECK} 使用记录卸载完成: $uninstall_count/$total_count 个包${NC}"
}

print_env_cleanup_plan() {
    if [ ! -f "$INSTALL_INFO_FILE" ]; then
        echo -e "${YELLOW}未找到安装信息文件，将只卸载 Python 包${NC}"
        return
    fi

    echo -e "${INFO} 检查安装环境信息..."

    local venv_name venv_path conda_env
    venv_name=$(grep '"venv_name"' "$INSTALL_INFO_FILE" | sed 's/.*: "\(.*\)".*/\1/')
    venv_path=$(grep '"venv_path"' "$INSTALL_INFO_FILE" | sed 's/.*: "\(.*\)".*/\1/')
    conda_env=$(grep '"conda_env"' "$INSTALL_INFO_FILE" | sed 's/.*: "\(.*\)".*/\1/')

    if [ -n "$venv_path" ]; then
        echo -e "${BLUE}检测到 Python 虚拟环境:${NC}"
        echo -e "  路径: ${DIM}$venv_path${NC}"
        if confirm "是否删除此虚拟环境目录？" false; then
            echo -e "${INFO} 删除虚拟环境目录..."
            rm -rf "$venv_path"
            echo -e "${CHECK} 已删除虚拟环境目录${NC}"
        else
            echo -e "${DIM}保留虚拟环境目录${NC}"
        fi
    elif [ -n "$conda_env" ]; then
        echo -e "${BLUE}检测到 Conda 环境:${NC}"
        echo -e "  名称: ${DIM}$conda_env${NC}"
        if confirm "是否删除此 Conda 环境 (conda env remove -n $conda_env)？" false; then
            if command -v conda >/dev/null 2>&1; then
                echo -e "${INFO} 删除 Conda 环境..."
                conda env remove -n "$conda_env" -y || echo -e "${YELLOW}删除 Conda 环境失败，请手动检查${NC}"
            else
                echo -e "${YELLOW}当前 shell 中未检测到 conda 命令，请手动删除环境${NC}"
            fi
        else
            echo -e "${DIM}保留 Conda 环境${NC}"
        fi
    else
        echo -e "${DIM}安装记录显示使用系统环境，无需虚拟环境清理${NC}"
    fi
}

main() {
    local args=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --yes|-y)
                AUTO_YES=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--yes]"
                echo "  --yes / -y     跳过所有确认提示"
                exit 0
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done

    if [ ${#args[@]} -gt 0 ]; then
        echo "${YELLOW}警告: 额外参数 '$${args[*]}' 已忽略。${NC}"
    fi

    print_header

    if ! confirm "确认开始卸载 SAGE 吗？" false; then
        echo -e "${INFO} 已取消卸载"
        exit 0
    fi

    # 优先使用记录的包列表卸载
    uninstall_packages_from_list

    echo ""
    echo -e "${BLUE}环境清理选项：${NC}"
    print_env_cleanup_plan

    echo ""
    echo -e "${CHECK} 卸载流程完成${NC}"
    echo -e "${DIM}提示: 如需再次安装，可运行: ./quickstart.sh${NC}"
}

main "$@"
