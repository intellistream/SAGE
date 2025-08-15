#!/bin/bash

# SAGE 快速启动脚本 - 简化版本
# 委托给模块化安装系统 tools/install/install.py

set -e

# 获取脚本所在目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}ℹ️ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Python是否可用
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未找到，请先安装 Python 3.8+"
        exit 1
    fi
    
    # 检查Python版本
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_info "Python版本: $python_version ✓"
    else
        print_error "Python版本 $python_version 不满足要求，需要 3.8+"
        exit 1
    fi
}

# 检查模块化安装系统
check_modular_installer() {
    INSTALLER_PATH="$PROJECT_ROOT/tools/install/install.py"
    
    if [[ ! -f "$INSTALLER_PATH" ]]; then
        print_error "模块化安装系统未找到: $INSTALLER_PATH"
        print_info "请确保在正确的SAGE项目目录中运行此脚本"
        exit 1
    fi
    
    print_info "找到模块化安装系统: $INSTALLER_PATH"
}

# 显示欢迎信息
show_welcome() {
    echo "
🚀 SAGE 快速启动脚本 
"
}

# 显示使用说明
show_usage() {
    echo "💡 使用方法:
  
  🏃 快速开始:
    $0                       # 交互式安装（推荐新用户）
    $0 --dev                    # 开发模式
    $0 --minimal                # 最小安装
  
  🎯 高级选项:
    $0 --profile standard       # 标准安装
    $0 --env-name my-sage       # 自定义环境名
    $0 --quiet                  # 静默模式
    $0 --force                  # 强制重装
  
  📋 查看选项:
    $0 --list-profiles          # 查看所有安装模式
    $0 --help                   # 详细帮助
    
  🔧 直接使用模块化系统:
    python3 tools/install/install.py --help
"
}

# 主函数
main() {
    show_welcome
    
    # 基础检查
    check_python
    check_modular_installer
    
    # 如果没有参数，显示使用说明并询问用户
    if [[ $# -eq 0 ]]; then
        show_usage
        echo "
🤔 如何继续？
  1) 交互式安装 (推荐新用户)
  2) 开发模式安装  
  3) 最小安装
  4) 显示所有安装模式
  5) 退出
"
        read -p "请选择 (1-5): " choice
        
        case $choice in
            1)
                print_info "启动交互式安装..."
                exec python3 "$PROJECT_ROOT/tools/install/install.py"
                ;;
            2)
                print_info "启动开发模式安装..."
                exec python3 "$PROJECT_ROOT/tools/install/install.py" --dev
                ;;
            3)
                print_info "启动最小安装..."
                exec python3 "$PROJECT_ROOT/tools/install/install.py" --minimal
                ;;
            4)
                exec python3 "$PROJECT_ROOT/tools/install/install.py" --list-profiles
                ;;
            5)
                print_info "退出安装"
                exit 0
                ;;
            *)
                print_warning "无效选择，启动交互式安装..."
                exec python3 "$PROJECT_ROOT/tools/install/install.py"
                ;;
        esac
    else
        # 有参数时，直接传递给模块化安装系统
        print_info "委托给模块化安装系统..."
        exec python3 "$PROJECT_ROOT/tools/install/install.py" "$@"
    fi
}

# 错误处理
trap 'print_error "安装过程中断"; exit 1' INT TERM

# 运行主函数
main "$@"
