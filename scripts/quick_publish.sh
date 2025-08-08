#!/bin/bash
#
# SAGE 闭源包发布简易包装脚本
# SAGE Proprietary Package Publishing Easy Wrapper Script
#
# 这是一个简化的包装脚本，提供预定义的发布方案
# This is a simplified wrapper script that provides predefined publishing scenarios
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_SCRIPT="$SCRIPT_DIR/proprietary_publish.sh"

# 检查主脚本是否存在
if [[ ! -f "$MAIN_SCRIPT" ]]; then
    echo "错误: 未找到主发布脚本: $MAIN_SCRIPT"
    exit 1
fi

show_usage() {
    cat << 'EOF'
🚀 SAGE 闭源包发布快捷脚本 SAGE Proprietary Publishing Quick Script

用法 Usage:
  ./quick_publish.sh <scenario> [additional_options...]

预定义方案 Predefined Scenarios:

  dev-test           开发测试 - 预演模式发布所有包到Test PyPI
                     Development test - dry run all packages to Test PyPI
                     
  staging            预发布 - 发布核心包到Test PyPI
                     Staging - publish core packages to Test PyPI
                     
  production         生产发布 - 发布所有包到正式PyPI
                     Production - publish all packages to PyPI
                     
  core-only          仅核心包 - 发布核心包到正式PyPI
                     Core only - publish core packages to PyPI
                     
  enterprise         企业版 - 发布企业版包
                     Enterprise - publish enterprise packages
                     
  community          社区版 - 发布社区版包
                     Community - publish community packages
                     
  single <package>   单包发布 - 发布指定单个包
                     Single package - publish specified package
                     
  custom             自定义 - 进入交互模式选择包和选项
                     Custom - enter interactive mode

示例 Examples:
  ./quick_publish.sh dev-test
  ./quick_publish.sh production --force
  ./quick_publish.sh single sage-kernel --test-pypi
  ./quick_publish.sh custom

更多选项请查看主脚本帮助 For more options see main script help:
  ./proprietary_publish.sh --help

EOF
}

# 核心包列表
CORE_PACKAGES=(
    "sage-kernel"
    "sage-middleware"
    "sage-core"
)

# 企业版包列表
ENTERPRISE_PACKAGES=(
    "sage-kernel"
    "sage-middleware"
    "sage-core"
)

# 社区版包列表
COMMUNITY_PACKAGES=(
    "sage-cli"
    "sage-utils"
    "sage-dev-toolkit"
    "sage-frontend"
)

# 交互式选择
interactive_selection() {
    echo "🎯 进入交互模式 Entering interactive mode"
    echo
    
    # 选择包
    echo "选择要发布的包 Select packages to publish:"
    echo "1) 所有包 All packages"
    echo "2) 核心包 Core packages (${CORE_PACKAGES[*]})"
    echo "3) 企业版包 Enterprise packages (${ENTERPRISE_PACKAGES[*]})"
    echo "4) 社区版包 Community packages (${COMMUNITY_PACKAGES[*]})"
    echo "5) 自定义选择 Custom selection"
    
    read -p "请选择 Please select (1-5): " -n 1 -r package_choice
    echo
    
    local selected_packages=()
    case $package_choice in
        1)
            selected_packages=("--all")
            ;;
        2)
            selected_packages=("${CORE_PACKAGES[@]}")
            ;;
        3)
            selected_packages=("${ENTERPRISE_PACKAGES[@]}")
            ;;
        4)
            selected_packages=("${COMMUNITY_PACKAGES[@]}")
            ;;
        5)
            echo "可用的包 Available packages:"
            local available_packages
            mapfile -t available_packages < <(find "$SCRIPT_DIR/../packages" -maxdepth 1 -type d -name "sage-*" | sort | sed 's|.*/||')
            
            for i in "${!available_packages[@]}"; do
                echo "  $((i+1))) ${available_packages[i]}"
            done
            
            echo "请输入包编号（用空格分隔）Please enter package numbers (space separated):"
            read -r -a pkg_numbers
            
            for num in "${pkg_numbers[@]}"; do
                if [[ $num =~ ^[0-9]+$ ]] && [[ $num -ge 1 ]] && [[ $num -le ${#available_packages[@]} ]]; then
                    selected_packages+=("${available_packages[$((num-1))]}")
                fi
            done
            ;;
        *)
            echo "无效选择 Invalid selection"
            exit 1
            ;;
    esac
    
    # 选择目标仓库
    echo
    echo "选择目标仓库 Select target repository:"
    echo "1) PyPI (生产环境 Production)"
    echo "2) Test PyPI (测试环境 Test)"
    
    read -p "请选择 Please select (1-2): " -n 1 -r repo_choice
    echo
    
    local repo_option=""
    case $repo_choice in
        1)
            repo_option=""
            ;;
        2)
            repo_option="--test-pypi"
            ;;
        *)
            echo "无效选择 Invalid selection"
            exit 1
            ;;
    esac
    
    # 选择模式
    echo
    echo "选择发布模式 Select publishing mode:"
    echo "1) 预演模式 Dry run (不实际发布 Don't actually publish)"
    echo "2) 实际发布 Actual publish"
    
    read -p "请选择 Please select (1-2): " -n 1 -r mode_choice
    echo
    
    local mode_option=""
    case $mode_choice in
        1)
            mode_option="--dry-run"
            ;;
        2)
            mode_option="--no-dry-run --force"
            ;;
        *)
            echo "无效选择 Invalid selection"
            exit 1
            ;;
    esac
    
    # 执行命令
    local cmd_args=("$MAIN_SCRIPT")
    cmd_args+=($mode_option)
    if [[ -n "$repo_option" ]]; then
        cmd_args+=($repo_option)
    fi
    cmd_args+=("${selected_packages[@]}")
    
    echo
    echo "即将执行 About to execute:"
    echo "${cmd_args[*]}"
    echo
    
    read -p "确认执行? Confirm execution? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "${cmd_args[@]}"
    else
        echo "取消执行 Execution cancelled"
    fi
}

# 主逻辑
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    local scenario="$1"
    shift  # 移除第一个参数
    
    case "$scenario" in
        -h|--help|help)
            show_usage
            exit 0
            ;;
            
        dev-test)
            echo "🧪 开发测试模式 Development test mode"
            "$MAIN_SCRIPT" --dry-run --test-pypi --all --verbose "$@"
            ;;
            
        staging)
            echo "🎭 预发布模式 Staging mode"
            "$MAIN_SCRIPT" --dry-run --test-pypi "${CORE_PACKAGES[@]}" --verbose "$@"
            ;;
            
        production)
            echo "🚀 生产发布模式 Production mode"
            "$MAIN_SCRIPT" --no-dry-run --all --clean "$@"
            ;;
            
        core-only)
            echo "🎯 仅核心包模式 Core packages only mode"
            "$MAIN_SCRIPT" --no-dry-run "${CORE_PACKAGES[@]}" --clean "$@"
            ;;
            
        enterprise)
            echo "🏢 企业版模式 Enterprise mode"
            "$MAIN_SCRIPT" --no-dry-run "${ENTERPRISE_PACKAGES[@]}" --clean "$@"
            ;;
            
        community)
            echo "🌍 社区版模式 Community mode"
            "$MAIN_SCRIPT" --no-dry-run "${COMMUNITY_PACKAGES[@]}" --clean "$@"
            ;;
            
        single)
            if [[ $# -eq 0 ]]; then
                echo "错误: 单包模式需要指定包名"
                echo "用法: $0 single <package_name>"
                exit 1
            fi
            local package_name="$1"
            shift
            echo "📦 单包发布模式 Single package mode: $package_name"
            "$MAIN_SCRIPT" --no-dry-run "$package_name" "$@"
            ;;
            
        custom)
            interactive_selection
            ;;
            
        *)
            echo "错误: 未知方案 Unknown scenario: $scenario"
            echo
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
