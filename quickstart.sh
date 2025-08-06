#!/bin/bash

# SAGE 快速启动脚本
# 为新手开发者提供最简单的项目初始化方式

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}\n"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 脚本开始
print_header "🌟 SAGE 项目快速启动脚本"

print_status "检查依赖环境..."

# 检查必要的命令
check_command "git"
check_command "python3"
check_command "pip"

print_success "环境检查通过"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_status "当前目录: $SCRIPT_DIR"

# 检查是否在正确的SAGE项目目录
if [ ! -f "pyproject.toml" ] || [ ! -d "packages" ]; then
    print_error "请在SAGE项目根目录运行此脚本"
    exit 1
fi

print_success "确认在SAGE项目目录"

# 询问用户安装类型
echo
echo "请选择安装类型:"
echo "1) 🏃 快速安装 (仅核心功能)"
echo "2) 👨‍💻 开发者安装 (包含开发工具)"
echo "3) 📚 完整安装 (包含文档和所有功能)"
echo

read -p "请输入选择 (1-3): " choice

case $choice in
    1)
        INSTALL_TYPE="quick"
        print_status "选择了快速安装模式"
        ;;
    2)
        INSTALL_TYPE="dev"
        print_status "选择了开发者安装模式"
        ;;
    3)
        INSTALL_TYPE="full"
        print_status "选择了完整安装模式"
        ;;
    *)
        print_warning "无效选择，使用默认快速安装模式"
        INSTALL_TYPE="quick"
        ;;
esac

# 使用Python脚本执行安装
print_header "🚀 开始执行安装"

if [ "$INSTALL_TYPE" = "quick" ]; then
    python3 scripts/deployment_setup.py init
    python3 scripts/deployment_setup.py install
elif [ "$INSTALL_TYPE" = "dev" ]; then
    python3 scripts/deployment_setup.py full --dev
elif [ "$INSTALL_TYPE" = "full" ]; then
    python3 scripts/deployment_setup.py full --dev
    if [ -d "docs-public" ]; then
        print_status "构建文档..."
        cd docs-public
        if command -v mkdocs &> /dev/null; then
            mkdocs build
            print_success "文档构建完成"
        else
            print_warning "mkdocs未安装，跳过文档构建"
        fi
        cd ..
    fi
fi

# 显示下一步操作
print_header "✅ 安装完成！"

echo -e "${GREEN}🎉 SAGE项目已成功设置！${NC}\n"

echo "📋 下一步可以做什么:"
echo "  • 查看项目状态: python3 scripts/deployment_setup.py status"
echo "  • 运行测试: python3 scripts/deployment_setup.py test"
echo "  • 启动Jupyter: jupyter notebook"

if [ -d "docs-public" ]; then
    echo "  • 查看文档: cd docs-public && mkdocs serve"
    echo "  • 在线文档: https://intellistream.github.io/SAGE-Pub/"
fi

echo
echo "🛠️ 常用开发命令:"
echo "  • 同步文档: ./tools/sync_docs.sh"
echo "  • 安装包: pip install -e packages/sage-kernel"
echo "  • 运行示例: python examples/hello_world.py"

echo
echo -e "${CYAN}📖 更多信息请参考: docs/DOCUMENTATION_GUIDE.md${NC}"
echo -e "${CYAN}🆘 遇到问题可以查看: packages/sage-kernel/docs/faq.md${NC}"

print_success "欢迎加入SAGE开发团队！ 🎯"
