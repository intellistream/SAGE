#!/bin/bash

# SAGE 快速启动脚本
# 为新手开发者提供最简单的项目初始化方式

set -e

# 获取脚本所在目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "脚本目录: $PROJECT_ROOT"
# 引入工具模块
source "$PROJECT_ROOT/scripts/logging.sh"
source "$PROJECT_ROOT/scripts/common_utils.sh"
source "$PROJECT_ROOT/scripts/conda_utils.sh"

# 脚本开始
print_header "🌟 SAGE 项目快速启动脚本"

print_status "检查依赖环境..."

# 检查必要的命令
check_command "git"
# 检查下载工具
if ! check_command_optional wget && ! check_command_optional curl; then
    print_error "需要 wget 或 curl 来下载 Miniconda，请先安装其中之一"
    exit 1
fi
# 注意：python3 和 pip 检查移到环境设置后进行

print_success "基础环境检查通过"

# 切换到项目根目录
cd "$PROJECT_ROOT"
print_status "当前目录: $PROJECT_ROOT"

# 验证项目结构
if ! validate_project_structure "$PROJECT_ROOT"; then
    print_error "请在SAGE项目根目录运行此脚本"
    exit 1
fi

print_success "确认在SAGE项目目录"

# 设置项目环境变量
setup_project_env "$PROJECT_ROOT"

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

# 环境设置阶段
print_header "🔧 环境设置"

# 1. 安装 Miniconda
if ! install_miniconda; then
    print_error "Miniconda 安装失败"
    exit 1
fi

# 2. 设置 SAGE 环境
if ! setup_sage_environment; then
    print_error "SAGE 环境设置失败"
    echo
    print_warning "如果是服务条款 (Terms of Service) 问题，请运行修复脚本:"
    print_status "  ./scripts/fix_conda_tos.sh"
    echo
    print_warning "其他常见解决方案:"
    print_warning "1. 手动接受服务条款:"
    print_warning "   conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main"
    print_warning "   conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r"
    print_warning "2. 或者使用 conda-forge 频道:"
    print_warning "   conda config --add channels conda-forge"
    print_warning "   conda config --set channel_priority strict"
    print_warning "3. 然后重新运行此脚本: ./quickstart.sh"
    echo
    exit 1
fi

# 3. 检查 Python 和 pip（现在应该在 conda 环境中）
print_status "验证 Python 环境..."
if ! check_command_optional python3; then
    if ! check_command_optional python; then
        print_error "Python 未找到，环境设置可能失败"
        exit 1
    else
        # 创建 python3 别名
        alias python3=python
        print_warning "使用 python 命令代替 python3"
    fi
fi

if ! check_command_optional pip; then
    print_error "pip 未找到，环境设置可能失败"
    exit 1
fi

print_success "Python 环境验证通过"

# 使用Python脚本执行安装
print_header "🚀 开始执行安装"

# 确保 conda 环境在当前 shell 中激活
if ! init_conda; then
    print_error "Conda 初始化失败"
    exit 1
fi

if ! activate_conda_env "$SAGE_ENV_NAME"; then
    print_error "无法激活 SAGE 环境"
    exit 1
fi

if [ "$INSTALL_TYPE" = "quick" ]; then
    python3 scripts/deployment_setup.py init
    python3 scripts/deployment_setup.py install
elif [ "$INSTALL_TYPE" = "dev" ]; then
    python3 scripts/deployment_setup.py full --dev
elif [ "$INSTALL_TYPE" = "full" ]; then
    python3 scripts/deployment_setup.py full --dev
    if [ -d "docs-public" ]; then
        print_status "构建文档..."
        safe_cd "docs-public"
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

# 显示环境信息
show_conda_env_info "$SAGE_ENV_NAME"

echo
echo "📋 下一步可以做什么:"
echo "  • 激活环境: conda activate sage"
echo "  • 查看项目状态: python3 scripts/deployment_setup.py status"
echo "  • 运行测试: python3 scripts/deployment_setup.py test"
echo "  • 启动Jupyter: jupyter notebook"

if [ -d "docs-public" ]; then
    echo "  • 查看文档: cd docs-public && mkdocs serve"
    echo "  • 在线文档: https://intellistream.github.io/SAGE-Pub/"
fi

echo
echo "🛠️ 常用开发命令:"
echo "  • 激活环境: conda activate sage"
echo "  • 同步文档: ./tools/sync_docs.sh"
echo "  • 安装包: pip install -e packages/sage-kernel"
echo "  • 运行示例: python examples/hello_world.py"

echo
echo -e "${CYAN}📖 更多信息请参考: docs/DOCUMENTATION_GUIDE.md${NC}"
echo -e "${CYAN}🆘 遇到问题可以查看: packages/sage-kernel/docs/faq.md${NC}"
echo -e "${YELLOW}⚠️  重要: 每次使用SAGE时，请先运行 'conda activate sage' 激活环境${NC}"

print_success "欢迎加入SAGE开发团队！ 🎯"
