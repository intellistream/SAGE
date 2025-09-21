#!/bin/bash
# SAGE 安装脚本 - SAGE 包检查和管理工具
# 处理现有 SAGE 安装的检查、卸载等操作

# 导入颜色定义
source "$(dirname "${BASH_SOURCE[0]}")/../display_tools/colors.sh"

# 检查是否已安装SAGE
check_existing_sage() {
    echo -e "${INFO} 检查是否已安装 SAGE..."
    
    # 检查pip包列表中的所有SAGE相关包变体
    local installed_packages=$(pip list 2>/dev/null | grep -E '^(sage|isage|intsage)(-|$)' || echo "")
    if [ -n "$installed_packages" ]; then
        # 获取第一个包的版本作为代表版本
        local version=$(echo "$installed_packages" | head -n1 | awk '{print $2}')
        echo -e "${WARNING} 检测到已安装的 SAGE v${version}"
        echo
        echo -e "${DIM}已安装的包：${NC}"
        echo "$installed_packages" | while read line; do
            echo -e "${DIM}  - $line${NC}"
        done
        echo
        return 0
    fi
    
    # 检查是否能导入sage（作为备用检查）
    if python3 -c "import sage" 2>/dev/null; then
        local sage_version=$(python3 -c "import sage; print(sage.__version__)" 2>/dev/null || echo "unknown")
        echo -e "${WARNING} 检测到已安装的 SAGE v${sage_version}"
        return 0
    fi
    
    echo -e "${SUCCESS} 未检测到已安装的 SAGE"
    return 1
}

# 卸载现有SAGE
uninstall_sage() {
    echo -e "${INFO} 卸载现有 SAGE 安装..."
    
    # 获取所有已安装的SAGE相关包（包括所有前缀变体）
    local all_sage_packages=$(pip list 2>/dev/null | grep -E '^(sage|isage|intsage)(-|$)' | awk '{print $1}' || echo "")
    
    if [ -n "$all_sage_packages" ]; then
        echo -e "${DIM}  → 发现已安装的包：${NC}"
        echo "$all_sage_packages" | while read package; do
            if [ -n "$package" ]; then
                echo -e "${DIM}    - $package${NC}"
            fi
        done
        
        # 批量卸载所有SAGE相关包
        echo -e "${DIM}  → 卸载所有 SAGE 相关包${NC}"
        
        # 逐个卸载包，提供更详细的反馈
        local uninstall_count=0
        local total_packages=0
        while IFS= read -r package; do
            if [ -n "$package" ]; then
                total_packages=$((total_packages + 1))
                # 先检查包是否真的存在
                if pip show "$package" >/dev/null 2>&1; then
                    # 检查是否是editable安装
                    local package_info=$(pip show "$package" 2>/dev/null)
                    if echo "$package_info" | grep -q "Editable project location:"; then
                        echo -e "${DIM}    ○ $package 开发模式安装，重新安装时会自动更新${NC}"
                        uninstall_count=$((uninstall_count + 1))  # 算作处理成功
                    else
                        if $PIP_CMD uninstall "$package" -y --quiet 2>/dev/null; then
                            echo -e "${DIM}    ✓ 已卸载 $package${NC}"
                            uninstall_count=$((uninstall_count + 1))
                        else
                            echo -e "${DIM}    ⚠ $package 卸载失败${NC}"
                        fi
                    fi
                else
                    echo -e "${DIM}    - $package 未安装，跳过${NC}"
                fi
            fi
        done <<< "$all_sage_packages"
        
        echo -e "${SUCCESS} 已清理 $uninstall_count/$total_packages 个SAGE包${NC}"
    fi
    
    # 清理可能的开发模式安装链接
    echo -e "${DIM}  → 清理开发模式链接${NC}"
    local dev_packages=(
        "sage"
        "sage-libs" 
        "sage-middleware"
        "sage-kernel"
        "sage-common"
        "sage-tools"
        "isage"
        "isage-libs" 
        "isage-middleware"
        "isage-kernel"
        "isage-common"
        "intsage"
        "intsage-apps"
        "intsage-dev-toolkit"
        "intsage-frontend"
        "intsage-kernel"
        "intsage-middleware"
    )
    
    for package in "${dev_packages[@]}"; do
        if $PIP_CMD uninstall "$package" -y --quiet 2>/dev/null; then
            echo -e "${DIM}    清理 $package 开发链接${NC}"
        fi
    done
    
    echo -e "${CHECK} SAGE 卸载完成"
}

# 询问是否卸载现有SAGE
ask_uninstall_sage() {
    echo ""
    echo -e "${BOLD}${YELLOW}⚠️  发现已安装的 SAGE${NC}"
    echo ""
    echo -e "${BLUE}为了确保安装的完整性，建议先卸载现有版本。${NC}"
    echo ""
    echo -e "${BLUE}选项：${NC}"
    echo -e "  [1] 卸载现有版本，然后安装新版本 (推荐)"
    echo -e "  [2] 跳过卸载，直接覆盖安装"
    echo -e "  [3] 取消安装"
    echo ""
    
    while true; do
        echo -ne "${BLUE}请选择 [1-3]: ${NC}"
        read -r choice
        case $choice in
            1)
                echo -e "${INFO} 将先卸载现有 SAGE，然后安装新版本"
                uninstall_sage
                return 0
                ;;
            2)
                echo -e "${WARNING} 跳过卸载，直接进行覆盖安装"
                echo -e "${DIM}注意：这可能导致版本冲突或安装问题${NC}"
                return 0
                ;;
            3)
                echo -e "${INFO} 用户取消安装"
                exit 0
                ;;
            *)
                echo -e "${WARNING} 无效选择，请输入 1-3"
                ;;
        esac
    done
}
