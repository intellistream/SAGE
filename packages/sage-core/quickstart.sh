#!/bin/bash

# SAGE Core 快速启动脚本
# 以开发模式安装 sage-core 源代码，并安装闭源依赖包

set -e

# 获取脚本所在目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "脚本目录: $PROJECT_ROOT"
# 引入工具模块
source "$PROJECT_ROOT/scripts/logging.sh"
source "$PROJECT_ROOT/scripts/common_utils.sh"
source "$PROJECT_ROOT/scripts/conda_utils.sh"

# 定义辅助函数
# 安装系统依赖的函数
install_system_dependencies() {
    print_status "安装编译依赖工具..."
    
    # 检测操作系统
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        OS=$ID
    else
        OS="unknown"
    fi
    
    case $OS in
        ubuntu|debian)
            print_status "检测到 Ubuntu/Debian 系统，安装必要的编译工具..."
            if command -v apt-get >/dev/null 2>&1; then
                # 检查是否有 sudo 权限
                if sudo -n true 2>/dev/null; then
                    # 安装 SWIG 和其他编译依赖
                    sudo apt-get update -qq
                    sudo apt-get install -y build-essential swig pkg-config libopenblas-dev
                    if [ $? -eq 0 ]; then
                        print_success "系统依赖安装成功"
                    else
                        print_warning "系统依赖安装失败，尝试使用预编译包"
                    fi
                else
                    print_warning "需要 sudo 权限安装系统依赖，请手动运行："
                    print_warning "  sudo apt-get update && sudo apt-get install -y build-essential swig pkg-config libopenblas-dev"
                fi
            else
                print_warning "未找到 apt-get，跳过系统依赖安装"
            fi
            ;;
        centos|rhel|fedora)
            print_status "检测到 CentOS/RHEL/Fedora 系统，安装必要的编译工具..."
            if command -v yum >/dev/null 2>&1; then
                if sudo -n true 2>/dev/null; then
                    sudo yum install -y gcc gcc-c++ swig pkgconfig openblas-devel
                else
                    print_warning "需要 sudo 权限，请手动运行: sudo yum install -y gcc gcc-c++ swig pkgconfig openblas-devel"
                fi
            elif command -v dnf >/dev/null 2>&1; then
                if sudo -n true 2>/dev/null; then
                    sudo dnf install -y gcc gcc-c++ swig pkgconfig openblas-devel
                else
                    print_warning "需要 sudo 权限，请手动运行: sudo dnf install -y gcc gcc-c++ swig pkgconfig openblas-devel"
                fi
            else
                print_warning "未找到包管理器，跳过系统依赖安装"
            fi
            ;;
        arch)
            print_status "检测到 Arch Linux 系统，安装必要的编译工具..."
            if command -v pacman >/dev/null 2>&1; then
                if sudo -n true 2>/dev/null; then
                    sudo pacman -S --noconfirm base-devel swig openblas
                else
                    print_warning "需要 sudo 权限，请手动运行: sudo pacman -S --noconfirm base-devel swig openblas"
                fi
            else
                print_warning "未找到 pacman，跳过系统依赖安装"
            fi
            ;;
        *)
            print_warning "未识别的操作系统: $OS，跳过系统依赖安装"
            ;;
    esac
    
    # 检查 SWIG 是否可用
    if command -v swig >/dev/null 2>&1; then
        print_success "SWIG 已安装: $(swig -version | head -n1)"
    else
        print_warning "SWIG 未找到，faiss-cpu 可能需要从源码编译"
        # 尝试使用 conda 安装 swig
        if command -v conda >/dev/null 2>&1; then
            print_status "尝试使用 conda 安装 SWIG..."
            conda install -y swig -c conda-forge
            if command -v swig >/dev/null 2>&1; then
                print_success "通过 conda 安装 SWIG 成功"
            else
                print_warning "conda 安装 SWIG 失败"
            fi
        fi
    fi
}

# 智能安装 faiss-cpu 的函数
install_faiss_with_fallback() {
    print_status "尝试安装 faiss-cpu..."
    
    # 首先尝试预编译包
    if pip install faiss-cpu --no-deps --only-binary=all 2>/dev/null; then
        print_success "faiss-cpu 预编译包安装成功"
        return 0
    fi
    
    print_warning "预编译包安装失败，尝试使用 conda-forge..."
    
    # 尝试使用 conda 安装
    if command -v conda >/dev/null 2>&1; then
        if conda install -y faiss-cpu -c conda-forge; then
            print_success "通过 conda 安装 faiss-cpu 成功"
            return 0
        fi
    fi
    
    print_warning "conda 安装失败，将跳过 faiss-cpu"
    return 1
}

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

# 询问用户是否继续
echo
echo "本脚本将："
echo "1) 以开发模式 (-e) 安装当前 sage-core 源代码"
echo "2) 通过 pyproject.toml 从 PyPI 安装运行时依赖包: sage-utils, sage-kernel, sage-middleware"
echo "3) 安装其他必要的依赖包"
echo
read -p "是否继续? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    print_status "操作取消"
    exit 0
fi

# 开始安装过程
print_header "📦 开始安装 SAGE Core 开发环境"

# 升级 pip
print_status "升级 pip..."
pip install --upgrade pip

# 清理可能的冲突包
print_status "清理可能的包冲突..."
pip list | grep -E "^sage" | awk '{print $1}' | xargs -r pip uninstall -y 2>/dev/null || true
pip list | grep -E "^intellistream-sage" | awk '{print $1}' | xargs -r pip uninstall -y 2>/dev/null || true

# 安装系统依赖和编译工具
print_status "检查和安装必要的系统依赖..."
install_system_dependencies

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



# 以开发模式安装当前 sage-core 包（这会自动从 PyPI 安装依赖包）
print_status "以开发模式安装 sage-core（包含 PyPI 闭源依赖）..."

# 首先尝试正常安装
if pip install -e . 2>/dev/null; then
    print_success "sage-core 开发安装成功"
else
    print_warning "正常安装失败，可能由于 faiss-cpu 编译问题"
    print_status "尝试智能安装策略..."
    
    # 先安装 faiss-cpu
    install_faiss_with_fallback
    
    # 再次尝试安装，如果还是失败则跳过有问题的依赖
    print_status "重新尝试安装 sage-core..."
    if ! pip install -e . --no-deps; then
        print_error "sage-core 开发安装失败"
        exit 1
    fi
    
    # 手动安装其他依赖（跳过可能有问题的）
    print_status "手动安装核心依赖..."
    pip install pyyaml python-dotenv pydantic typing-extensions rouge
    
    # 确保安装最新版本的闭源依赖包
    print_status "安装最新版本的闭源依赖包..."
    pip install --upgrade --force-reinstall intellistream-sage-utils intellistream-sage-kernel intellistream-sage-middleware intellistream-sage-cli
    
    print_success "sage-core 开发安装完成（已跳过问题依赖）"
fi

# 验证安装
print_header "🔍 验证安装结果"

print_status "检查安装的包..."
pip list | grep -E "(sage|intellistream-sage)" || print_warning "未找到相关包"

# 验证闭源包版本
print_status "验证闭源包版本..."
pip show intellistream-sage-kernel | grep "Version:" || print_warning "无法获取 intellistream-sage-kernel 版本信息"

print_status "测试 sage 模块导入..."
if python3 -c "import sage; print('✅ sage 模块导入成功')" 2>/dev/null; then
    print_success "sage 模块导入测试通过"
else
    print_warning "sage 模块导入失败，可能需要检查依赖"
fi

# 显示安装完成信息
print_header "🎉 SAGE Core 开发环境安装完成！"

echo
echo "安装摘要:"
echo "✅ sage-core 已以开发模式安装 (可直接编辑源代码)"
echo "📦 依赖包已从 PyPI 安装 (闭源版本)"
echo "🔧 sage-utils, sage-kernel, sage-middleware 为闭源包"
echo
echo "使用说明:"
echo "1) 现在可以直接编辑 src/sage/ 下的源代码"
echo "2) sage-core 代码修改会立即生效，无需重新安装"
echo "3) 可以使用 'python -c \"import sage\"' 测试模块"
echo "4) 依赖包为 PyPI 闭源版本，提供稳定功能"
echo
echo "开发模式特点:"
echo "• sage-core 源代码修改立即生效"
echo "• 可以直接调试和开发核心 API"
echo "• 依赖包使用稳定的 PyPI 闭源版本"
echo "• 适合 sage-core 核心功能开发"
echo

print_success "开发环境准备就绪！"

# 显示故障排除信息
echo
echo "🔧 故障排除提示："
echo
echo "如果遇到 faiss-cpu 编译错误："
echo "1) 确保安装了编译工具："
echo "   Ubuntu/Debian: sudo apt-get install build-essential swig pkg-config libopenblas-dev"
echo "   CentOS/RHEL: sudo yum install gcc gcc-c++ swig pkgconfig openblas-devel"
echo "   Fedora: sudo dnf install gcc gcc-c++ swig pkgconfig openblas-devel"
echo "   Arch: sudo pacman -S base-devel swig openblas"
echo
echo "2) 或者使用 conda 安装 faiss-cpu："
echo "   conda install faiss-cpu -c conda-forge"
echo
echo "3) 如果是 Python 3.13，可能需要等待兼容版本发布"
echo "   建议暂时使用 Python 3.11 或 3.12"
echo
echo "如果遇到模块导入错误："
echo "1) 检查闭源包版本是否最新："
echo "   pip install --upgrade intellistream-sage-kernel intellistream-sage-utils intellistream-sage-middleware"
echo
echo "2) 如果导入 JobManagerClient 错误，检查 sage.kernel 版本是否大于等于 0.1.5："
echo "   pip show intellistream-sage-kernel"
echo
echo "3) 清理旧版本的包："
echo "   pip uninstall -y intellistream-sage intellistream-sage-kernel intellistream-sage-utils intellistream-sage-middleware"
echo "   然后重新运行此脚本"
echo
