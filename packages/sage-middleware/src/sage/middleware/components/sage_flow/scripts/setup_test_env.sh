#!/bin/bash

# SAGE Flow 测试环境设置脚本
# 该脚本设置完整的测试环境，包括依赖安装和配置

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 配置变量
CONDA_ENV_NAME="${CONDA_ENV_NAME:-sage}"
PYTHON_VERSION="${PYTHON_VERSION:-3.9}"
FORCE_REINSTALL="${FORCE_REINSTALL:-false}"

log_info "开始设置 SAGE Flow 测试环境..."
log_info "项目根目录: $PROJECT_ROOT"
log_info "Conda 环境名: $CONDA_ENV_NAME"
log_info "Python 版本: $PYTHON_VERSION"

# 检查并安装 conda
check_and_install_conda() {
    log_info "检查 conda 安装..."
    
    if ! command -v conda &> /dev/null; then
        log_error "conda 未安装，请先安装 Miniconda 或 Anaconda"
        log_info "下载地址: https://docs.conda.io/en/latest/miniconda.html"
        return 1
    fi
    
    log_success "conda 已安装: $(conda --version)"
    return 0
}

# 创建或更新 conda 环境
setup_conda_environment() {
    log_info "设置 conda 环境: $CONDA_ENV_NAME"
    
    # 检查环境是否存在
    if conda env list | grep -q "^$CONDA_ENV_NAME "; then
        if [[ "$FORCE_REINSTALL" == "true" ]]; then
            log_warning "强制重新安装环境，删除现有环境..."
            conda env remove -n "$CONDA_ENV_NAME" -y
        else
            log_info "环境 $CONDA_ENV_NAME 已存在，跳过创建"
            return 0
        fi
    fi
    
    log_info "创建 conda 环境: $CONDA_ENV_NAME (Python $PYTHON_VERSION)"
    conda create -n "$CONDA_ENV_NAME" python="$PYTHON_VERSION" -y
    
    log_success "conda 环境创建成功"
    return 0
}

# 激活环境并安装基础依赖
install_base_dependencies() {
    log_info "安装基础依赖..."
    
    # 激活环境
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV_NAME"
    
    # 更新 pip
    log_info "更新 pip..."
    python -m pip install --upgrade pip
    
    # 安装基础构建依赖
    log_info "安装基础构建依赖..."
    conda install -y cmake make ninja
    
    # 安装 Python 依赖
    log_info "安装 Python 依赖..."
    local python_deps=(
        "numpy>=1.21.0"
        "pybind11>=2.10.0"
        "typing-extensions>=4.0.0"
    )
    
    pip install "${python_deps[@]}"
    
    log_success "基础依赖安装完成"
    return 0
}

# 安装开发和测试依赖
install_dev_dependencies() {
    log_info "安装开发和测试依赖..."
    
    # 确保在正确的环境中
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV_NAME"
    
    # 开发依赖
    local dev_deps=(
        "pytest>=7.0"
        "pytest-cov>=4.0"
        "pytest-xdist>=3.0"
        "pytest-benchmark>=4.0"
        "hypothesis>=6.0"
        "black>=22.0"
        "isort>=5.10"
        "mypy>=1.0"
        "flake8>=5.0"
        "pre-commit>=2.20"
        "build>=0.8"
        "twine>=4.0"
    )
    
    # 性能测试依赖
    local perf_deps=(
        "memory-profiler>=0.60"
        "psutil>=5.9"
        "py-spy>=0.3"
    )
    
    # 文档依赖
    local docs_deps=(
        "sphinx>=5.0"
        "sphinx-rtd-theme>=1.0"
        "myst-parser>=0.18"
        "sphinx-autoapi>=2.0"
    )
    
    log_info "安装开发依赖..."
    pip install "${dev_deps[@]}"
    
    log_info "安装性能测试依赖..."
    pip install "${perf_deps[@]}"
    
    log_info "安装文档依赖..."
    pip install "${docs_deps[@]}"
    
    log_success "开发和测试依赖安装完成"
    return 0
}

# 安装系统依赖 (Ubuntu/Debian)
install_system_dependencies_ubuntu() {
    log_info "检查并安装系统依赖 (Ubuntu/Debian)..."
    
    # 检查是否有 sudo 权限
    if ! sudo -n true 2>/dev/null; then
        log_warning "需要 sudo 权限安装系统依赖"
        return 0
    fi
    
    # 更新包列表
    sudo apt-get update
    
    # 安装必要的系统依赖
    local sys_deps=(
        "build-essential"
        "cmake"
        "ninja-build"
        "pkg-config"
        "libeigen3-dev"
        "libboost-all-dev"
        "libjq-dev"
        "clang-tidy"
        "valgrind"
        "gdb"
    )
    
    sudo apt-get install -y "${sys_deps[@]}"
    
    log_success "系统依赖安装完成"
    return 0
}

# 安装系统依赖 (CentOS/RHEL)
install_system_dependencies_centos() {
    log_info "检查并安装系统依赖 (CentOS/RHEL)..."
    
    # 检查是否有 sudo 权限
    if ! sudo -n true 2>/dev/null; then
        log_warning "需要 sudo 权限安装系统依赖"
        return 0
    fi
    
    # 安装开发工具
    sudo yum groupinstall -y "Development Tools"
    
    # 安装必要的系统依赖
    local sys_deps=(
        "cmake3"
        "ninja-build"
        "pkgconfig"
        "eigen3-devel"
        "boost-devel"
        "jq-devel"
        "clang-tools-extra"
        "valgrind"
        "gdb"
    )
    
    sudo yum install -y "${sys_deps[@]}"
    
    # 创建 cmake 符号链接
    if [[ -f /usr/bin/cmake3 ]] && [[ ! -f /usr/bin/cmake ]]; then
        sudo ln -sf /usr/bin/cmake3 /usr/bin/cmake
    fi
    
    log_success "系统依赖安装完成"
    return 0
}

# 检测并安装系统依赖
install_system_dependencies() {
    log_info "检测操作系统并安装系统依赖..."
    
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        case "$ID" in
            ubuntu|debian)
                install_system_dependencies_ubuntu
                ;;
            centos|rhel|fedora)
                install_system_dependencies_centos
                ;;
            *)
                log_warning "未识别的操作系统: $ID，跳过系统依赖安装"
                ;;
        esac
    else
        log_warning "无法检测操作系统，跳过系统依赖安装"
    fi
    
    return 0
}

# 设置 Git 钩子
setup_git_hooks() {
    log_info "设置 Git 钩子..."
    
    cd "$PROJECT_ROOT"
    
    # 确保在正确的环境中
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV_NAME"
    
    # 安装 pre-commit 钩子
    if [[ -f .pre-commit-config.yaml ]]; then
        pre-commit install
        log_success "pre-commit 钩子安装成功"
    else
        log_warning ".pre-commit-config.yaml 不存在，跳过 pre-commit 设置"
    fi
    
    return 0
}

# 验证安装
verify_installation() {
    log_info "验证安装..."
    
    # 确保在正确的环境中
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV_NAME"
    
    echo "环境验证报告:"
    echo "============="
    echo "Python 版本: $(python --version)"
    echo "pip 版本: $(pip --version)"
    echo "conda 环境: $(conda info --envs | grep '*' | awk '{print $1}')"
    
    echo ""
    echo "关键依赖版本:"
    echo "============"
    
    local key_packages=(
        "numpy"
        "pybind11"
        "pytest"
        "cmake"
    )
    
    for pkg in "${key_packages[@]}"; do
        if python -c "import $pkg; print(f'$pkg: {$pkg.__version__}')" 2>/dev/null; then
            echo "✓ $pkg 已安装"
        elif command -v "$pkg" &> /dev/null; then
            echo "✓ $pkg 已安装: $(${pkg} --version | head -n1)"
        else
            echo "✗ $pkg 未安装"
        fi
    done
    
    echo ""
    echo "系统工具:"
    echo "========"
    local sys_tools=(
        "cmake"
        "make"
        "g++"
        "clang-tidy"
        "valgrind"
    )
    
    for tool in "${sys_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            echo "✓ $tool 已安装"
        else
            echo "✗ $tool 未安装"
        fi
    done
    
    log_success "环境验证完成"
    return 0
}

# 生成环境配置脚本
generate_env_script() {
    log_info "生成环境配置脚本..."
    
    local env_script="$PROJECT_ROOT/activate_test_env.sh"
    
    cat > "$env_script" << EOF
#!/bin/bash

# SAGE Flow 测试环境激活脚本
# 使用方法: source activate_test_env.sh

# 激活 conda 环境
source "\$(conda info --base)/etc/profile.d/conda.sh"
conda activate $CONDA_ENV_NAME

# 设置环境变量
export SAGE_FLOW_ROOT="$PROJECT_ROOT"
export SAGE_FLOW_BUILD_DIR="\$SAGE_FLOW_ROOT/build"
export PYTHONPATH="\$SAGE_FLOW_BUILD_DIR:\$PYTHONPATH"

# 显示环境信息
echo "SAGE Flow 测试环境已激活"
echo "Python: \$(python --version)"
echo "环境: \$(conda info --envs | grep '*' | awk '{print \$1}')"
echo "项目根目录: \$SAGE_FLOW_ROOT"

# 设置别名
alias sage-build="cd \$SAGE_FLOW_ROOT && ./scripts/build_test.sh"
alias sage-test="cd \$SAGE_FLOW_ROOT && python -m pytest tests/"
alias sage-clean="rm -rf \$SAGE_FLOW_BUILD_DIR"

echo "可用别名:"
echo "  sage-build  - 构建项目"
echo "  sage-test   - 运行测试"
echo "  sage-clean  - 清理构建"
EOF

    chmod +x "$env_script"
    
    log_success "环境配置脚本已生成: $env_script"
    log_info "使用方法: source activate_test_env.sh"
    
    return 0
}

# 主函数
main() {
    local start_time=$(date +%s)
    
    # 检查和安装依赖
    check_and_install_conda || exit 1
    install_system_dependencies || true  # 系统依赖不是必须的
    
    # 设置 conda 环境
    setup_conda_environment || exit 1
    install_base_dependencies || exit 1
    install_dev_dependencies || exit 1
    
    # 设置开发环境
    setup_git_hooks || true  # Git 钩子不是必须的
    
    # 验证和生成配置
    verify_installation || exit 1
    generate_env_script || exit 1
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    log_success "测试环境设置完成！总耗时: ${total_duration}秒"
    log_info "下一步:"
    echo "  1. 激活环境: source activate_test_env.sh"
    echo "  2. 构建项目: sage-build"
    echo "  3. 运行测试: sage-test"
}

# 检查是否作为脚本直接运行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi