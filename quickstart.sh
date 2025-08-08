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

# 安装SAGE包的函数
install_sage_packages() {
    local install_type="$1"
    
    print_header "📦 安装 SAGE 包"
    
    # 确保在正确的环境中
    if [ "$CONDA_DEFAULT_ENV" != "$SAGE_ENV_NAME" ]; then
        print_warning "重新激活 conda 环境..."
        if ! activate_conda_env "$SAGE_ENV_NAME"; then
            print_error "无法激活 SAGE 环境"
            return 1
        fi
    fi
    
    print_status "检查现有安装并清理冲突..."
    
    # 卸载可能存在冲突的包
    local packages_to_uninstall=("intsage" "intsage-kernel" "intsage-middleware" "intsage-apps" "intsage-dev-toolkit" "intsage-frontend")
    for pkg in "${packages_to_uninstall[@]}"; do
        if pip show "$pkg" >/dev/null 2>&1; then
            print_status "卸载现有包: $pkg"
            pip uninstall -y "$pkg" >/dev/null 2>&1 || true
        fi
    done
    
    # 清理可能的site-packages冲突
    local conda_env_path="$HOME/miniconda3/envs/$SAGE_ENV_NAME"
    if [ -d "$SAGE_CONDA_PATH/envs/$SAGE_ENV_NAME" ]; then
        conda_env_path="$SAGE_CONDA_PATH/envs/$SAGE_ENV_NAME"
    fi
    local sage_site_pkg="$conda_env_path/lib/python*/site-packages/sage"
    if ls $sage_site_pkg 2>/dev/null >/dev/null; then
        print_status "清理旧的 sage 命名空间包..."
        rm -rf $sage_site_pkg 2>/dev/null || true
    fi
    
    print_status "按正确顺序安装 SAGE 包..."
    
    # 1. 首先安装命名空间包 - sage-middleware 和 sage-apps
    print_status "1/6 安装 sage-middleware..."
    if ! pip install -e packages/sage-middleware; then
        print_error "sage-middleware 安装失败"
        return 1
    fi
    
    print_status "2/6 安装 sage-apps..."
    if ! pip install -e packages/sage-apps; then
        print_error "sage-apps 安装失败"
        return 1
    fi
    
    # 2. 然后安装核心包
    print_status "3/6 安装 sage-kernel..."
    if ! pip install -e packages/sage-kernel; then
        print_error "sage-kernel 安装失败"
        return 1
    fi
    
    print_status "4/6 安装主 sage 包..."
    if ! pip install -e packages/sage; then
        print_error "sage 安装失败"
        return 1
    fi
    
    # 3. 最后安装开发工具（如果需要）
    if [ "$install_type" != "quick" ]; then
        print_status "5/6 安装 sage-dev-toolkit..."
        if ! pip install -e packages/sage-tools/sage-dev-toolkit; then
            print_warning "sage-dev-toolkit 安装失败，继续..."
        fi
        
        print_status "6/6 安装 sage-frontend..."
        if ! pip install -e packages/sage-tools/sage-frontend; then
            print_warning "sage-frontend 安装失败，继续..."
        fi
    else
        print_status "快速安装模式，跳过开发工具"
    fi
    
    print_success "SAGE 包安装完成"
    return 0
}

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

# 安装基础依赖
print_status "安装基础 Python 依赖..."
if [ "$INSTALL_TYPE" = "quick" ]; then
    pip install -r scripts/requirements/requirements.txt >/dev/null 2>&1 || print_warning "部分依赖安装失败"
else
    pip install -r scripts/requirements/requirements.txt >/dev/null 2>&1 || print_warning "部分依赖安装失败"
    pip install -r scripts/requirements/requirements-dev.txt >/dev/null 2>&1 || print_warning "部分开发依赖安装失败"
fi

# 使用新的包安装函数
if ! install_sage_packages "$INSTALL_TYPE"; then
    print_error "SAGE 包安装失败"
    exit 1
fi

# 构建文档（仅限完整安装）
if [ "$INSTALL_TYPE" = "full" ]; then
    if [ -d "docs-public" ]; then
        print_status "构建文档..."
        safe_cd "docs-public"
        if command -v mkdocs &> /dev/null; then
            mkdocs build >/dev/null 2>&1 && print_success "文档构建完成" || print_warning "文档构建失败"
        else
            print_warning "mkdocs未安装，跳过文档构建"
        fi
        cd ..
    fi
fi

# 验证安装的函数
verify_installation() {
    print_header "🔍 验证安装"
    
    local all_good=true
    
    # 测试核心包导入
    local test_imports=(
        "intsage:主包"
        "intsage.kernel:内核包"
        "sage.middleware:中间件包"
        "sage.apps:应用包"
    )
    
    for import_test in "${test_imports[@]}"; do
        local import_name="${import_test%:*}"
        local display_name="${import_test#*:}"
        
        if python3 -c "import $import_name" 2>/dev/null; then
            print_status "✅ $display_name 导入成功"
        else
            print_warning "❌ $display_name 导入失败"
            all_good=false
        fi
    done
    
    # 测试开发工具（如果安装了）
    if [ "$INSTALL_TYPE" != "quick" ]; then
        if python3 -c "import sage_dev_toolkit" 2>/dev/null; then
            print_status "✅ 开发工具包导入成功"
        else
            print_warning "❌ 开发工具包导入失败"
        fi
    fi
    
    if [ "$all_good" = true ]; then
        print_success "所有核心包验证通过"
        return 0
    else
        print_warning "部分包验证失败，但可以继续使用"
        return 1
    fi
}

# 显示下一步操作
print_header "✅ 安装完成！"

# 验证安装
verify_installation

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
