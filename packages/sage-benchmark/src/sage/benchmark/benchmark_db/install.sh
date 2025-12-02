#!/bin/bash
# SAGE-DB-Bench 自动安装脚本
# 用于快速在Linux/macOS上部署完整环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            VER=$VERSION_ID
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    log_info "Detected OS: $OS"
}

# 检查依赖
check_dependencies() {
    log_info "Checking dependencies..."

    local missing_deps=()

    # 必需的命令
    for cmd in git python3 pip3 cmake; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        else
            log_success "$cmd found: $(command -v $cmd)"
        fi
    done

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install them first"
        return 1
    fi

    log_success "All required dependencies found"
}

# 安装系统依赖
install_system_deps() {
    log_info "Installing system dependencies..."

    case $OS in
        ubuntu|debian)
            log_info "Installing packages via apt-get..."
            sudo apt-get update
            sudo apt-get install -y \
                build-essential \
                cmake \
                git \
                python3-dev \
                libopenblas-dev \
                libomp-dev \
                swig \
                pkg-config
            ;;
        macos)
            log_info "Installing packages via Homebrew..."
            if ! command -v brew &> /dev/null; then
                log_error "Homebrew not found. Please install from https://brew.sh"
                return 1
            fi
            brew install cmake libomp openblas swig
            ;;
        *)
            log_warning "Unknown OS, skipping system dependencies"
            log_warning "Please install: cmake, openblas, openmp, swig manually"
            ;;
    esac

    log_success "System dependencies installed"
}

# 创建虚拟环境
setup_venv() {
    log_info "Setting up Python virtual environment..."

    if [ -d "venv" ]; then
        log_warning "Virtual environment already exists"
        read -p "Recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
        else
            log_info "Using existing virtual environment"
            return 0
        fi
    fi

    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel

    log_success "Virtual environment created"
}

# 安装Python依赖
install_python_deps() {
    log_info "Installing Python dependencies..."

    if [ ! -f "venv/bin/activate" ]; then
        log_error "Virtual environment not found. Run setup_venv first."
        return 1
    fi

    source venv/bin/activate
    pip install -r requirements.txt

    log_success "Python dependencies installed"
}

# 初始化子模块
init_submodules() {
    log_info "Initializing git submodules..."

    git submodule update --init --recursive

    log_success "Submodules initialized"
}

# 编译算法库
build_algorithms() {
    log_info "Building algorithm libraries..."
    log_warning "This may take 30-60 minutes..."

    read -p "Build all algorithms? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cd algorithms_impl

        if [ ! -f "build.sh" ]; then
            log_error "build.sh not found in algorithms_impl/"
            cd ..
            return 1
        fi

        chmod +x build.sh
        ./build.sh 2>&1 | tee ../logs/build.log

        cd ..
        log_success "Algorithms built successfully"
    else
        log_info "Skipping algorithm build"
    fi
}

# 验证安装
verify_installation() {
    log_info "Verifying installation..."

    source venv/bin/activate

    # 测试Python包
    python3 << EOF
import sys
try:
    import numpy
    import pandas
    import yaml
    import h5py
    print("✓ Core packages OK")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

try:
    from bench import BenchmarkRunner
    print("✓ Framework OK")
except ImportError as e:
    print(f"✗ Framework import error: {e}")
    sys.exit(1)

try:
    from datasets import DATASETS
    print(f"✓ {len(DATASETS)} datasets available")
except ImportError as e:
    print(f"✗ Dataset import error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        log_success "Installation verified"
    else
        log_error "Verification failed"
        return 1
    fi
}

# 显示使用说明
show_usage() {
    cat << EOF

${GREEN}═══════════════════════════════════════════════════════════${NC}
${GREEN}  SAGE-DB-Bench Installation Complete!${NC}
${GREEN}═══════════════════════════════════════════════════════════${NC}

Next steps:

  1. Activate virtual environment:
     ${BLUE}source venv/bin/activate${NC}

  2. Run tests:
     ${BLUE}python tests/test_streaming.py${NC}

  3. Run a benchmark:
     ${BLUE}python __main__.py --config runbooks/simple.yaml${NC}

  4. Prepare datasets:
     ${BLUE}python prepare_dataset.py --dataset sift-small${NC}

Documentation:
  - README.md - Project overview
  - INSTALL.md - Detailed installation guide
  - algorithms_impl/README.md - Algorithm compilation

Need help?
  - Issues: https://github.com/intellistream/SAGE-DB-Bench/issues
  - Docs: https://github.com/intellistream/SAGE-DB-Bench

${GREEN}═══════════════════════════════════════════════════════════${NC}

EOF
}

# 主函数
main() {
    echo ""
    log_info "SAGE-DB-Bench Installation Script"
    echo ""

    # 创建日志目录
    mkdir -p logs

    detect_os

    # 交互式选择安装内容
    echo ""
    echo "Select installation type:"
    echo "  1) Quick install (Python only, no C++ algorithms)"
    echo "  2) Full install (with C++ algorithms compilation)"
    echo "  3) Custom install"
    echo ""
    read -p "Your choice [1/2/3]: " -n 1 -r choice
    echo ""

    case $choice in
        1)
            log_info "Starting quick installation..."
            check_dependencies || exit 1
            setup_venv
            install_python_deps
            init_submodules
            verify_installation
            ;;
        2)
            log_info "Starting full installation..."
            check_dependencies || exit 1
            install_system_deps
            setup_venv
            install_python_deps
            init_submodules
            build_algorithms
            verify_installation
            ;;
        3)
            log_info "Custom installation..."
            check_dependencies || exit 1

            read -p "Install system dependencies? (Y/n): " -n 1 -r; echo
            [[ ! $REPLY =~ ^[Nn]$ ]] && install_system_deps

            read -p "Setup virtual environment? (Y/n): " -n 1 -r; echo
            [[ ! $REPLY =~ ^[Nn]$ ]] && setup_venv

            read -p "Install Python dependencies? (Y/n): " -n 1 -r; echo
            [[ ! $REPLY =~ ^[Nn]$ ]] && install_python_deps

            read -p "Initialize submodules? (Y/n): " -n 1 -r; echo
            [[ ! $REPLY =~ ^[Nn]$ ]] && init_submodules

            read -p "Build algorithms? (Y/n): " -n 1 -r; echo
            [[ ! $REPLY =~ ^[Nn]$ ]] && build_algorithms

            verify_installation
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac

    show_usage
}

# 运行主函数
main "$@"
