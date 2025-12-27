#!/bin/bash
# ==============================================================================
# SAGE Studio 本地部署测试脚本
# ==============================================================================
# 功能: 模拟 deploy-studio.yml workflow 的完整执行流程
# 用法: ./tools/scripts/test-deploy-studio.sh [--port PORT] [--skip-install] [--skip-build]
#
# 选项:
#   --port PORT       指定 Studio 端口 (默认: 5173)
#   --skip-install    跳过 SAGE 安装步骤
#   --skip-build      跳过前端构建步骤
#   --skip-start      只构建不启动
#   --help            显示帮助信息
# ==============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认参数
PORT=5173
SKIP_INSTALL=false
SKIP_BUILD=false
SKIP_START=false
CONDA_ENV_NAME="sage"

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 日志函数
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${GREEN}🔷 $1${NC}"; echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# 帮助信息
show_help() {
    echo "SAGE Studio 本地部署测试脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --port PORT       指定 Studio 端口 (默认: 5173)"
    echo "  --skip-install    跳过 SAGE 安装步骤"
    echo "  --skip-build      跳过前端构建步骤"
    echo "  --skip-start      只构建不启动服务"
    echo "  --help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                          # 完整测试"
    echo "  $0 --port 8080              # 使用端口 8080"
    echo "  $0 --skip-install           # 跳过安装，直接构建和启动"
    echo "  $0 --skip-install --skip-build  # 直接启动（假设已构建）"
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --skip-install)
            SKIP_INSTALL=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-start)
            SKIP_START=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# ==============================================================================
# Step 1: Setup Conda Environment
# ==============================================================================
setup_conda() {
    log_step "Step 1: Setup Conda Environment"

    # 定义 conda 初始化函数
    init_conda() {
        for conda_path in "$HOME/miniconda3" "$HOME/anaconda3" "/opt/conda" "/usr/local/miniconda3"; do
            if [ -f "$conda_path/etc/profile.d/conda.sh" ]; then
                source "$conda_path/etc/profile.d/conda.sh"
                CONDA_PATH="$conda_path"
                return 0
            fi
        done
        return 1
    }

    # 尝试初始化 conda
    if ! init_conda; then
        log_error "未找到 conda，请先安装 Miniconda 或 Anaconda"
        exit 1
    fi

    conda --version
    log_success "Conda 已初始化"

    # 确定使用的环境名
    if conda env list | grep -q "^sage "; then
        ACTUAL_CONDA_ENV="sage"
        log_success "复用已有的 'sage' 环境"
    elif conda env list | grep -q "^${CONDA_ENV_NAME} "; then
        ACTUAL_CONDA_ENV="${CONDA_ENV_NAME}"
        log_success "使用 '${CONDA_ENV_NAME}' 环境"
    else
        ACTUAL_CONDA_ENV="${CONDA_ENV_NAME}"
        log_info "创建新的 Conda 环境 '${ACTUAL_CONDA_ENV}'..."
        conda create -n ${ACTUAL_CONDA_ENV} python=3.11 -y
    fi

    # 激活环境
    conda activate ${ACTUAL_CONDA_ENV}
    log_success "Conda 环境已激活: ${ACTUAL_CONDA_ENV}"
    echo "Python: $(which python)"
    echo "CONDA_PREFIX: $CONDA_PREFIX"

    # 检查核心依赖是否已安装
    NVIDIA_COUNT=$(pip list 2>/dev/null | grep -c -i "nvidia" || echo "0")
    TORCH_COUNT=$(pip list 2>/dev/null | grep -c "^torch " || echo "0")

    if [ "$NVIDIA_COUNT" -gt 5 ] && [ "$TORCH_COUNT" -gt 0 ]; then
        DEPS_INSTALLED=true
        log_success "核心依赖已安装（NVIDIA: $NVIDIA_COUNT, PyTorch: $TORCH_COUNT）"
    else
        DEPS_INSTALLED=false
        log_info "需要安装核心依赖"
    fi
}

# ==============================================================================
# Step 2: Stop Existing Services
# ==============================================================================
stop_existing_services() {
    log_step "Step 2: Stop Existing Services"

    log_info "停止现有 SAGE Studio 服务..."
    pkill -f "sage studio" 2>/dev/null || true
    pkill -f "sage-llm-gateway" 2>/dev/null || true
    pkill -f "vllm.entrypoints" 2>/dev/null || true
    sleep 2
    log_success "现有服务已停止"
}

# ==============================================================================
# Step 3: Check Existing SAGE Installation
# ==============================================================================
check_sage_installation() {
    log_step "Step 3: Check Existing SAGE Installation"

    if python -c "import sage.studio; import sage.llm.gateway" 2>/dev/null; then
        SAGE_INSTALLED=true
        log_success "SAGE 已安装"
    else
        SAGE_INSTALLED=false
        log_info "SAGE 未安装"
    fi
}

# ==============================================================================
# Step 4: Install/Update SAGE
# ==============================================================================
install_sage() {
    log_step "Step 4: Install/Update SAGE"

    if [ "$SKIP_INSTALL" = true ]; then
        log_warning "跳过 SAGE 安装步骤 (--skip-install)"
        return
    fi

    cd "$REPO_ROOT"

    # 配置国内 PyPI 镜像加速
    export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
    export PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
    export PIP_DEFAULT_TIMEOUT=300
    export PIP_RETRIES=5

    if [ "$SAGE_INSTALLED" = true ]; then
        log_info "执行增量更新（仅更新 SAGE 包，不重装依赖）..."
        pip install -e packages/sage-common --no-deps -q
        pip install -e packages/sage-platform --no-deps -q
        pip install -e packages/sage-kernel --no-deps -q
        pip install -e packages/sage-libs --no-deps -q
        pip install -e packages/sage-middleware --no-deps -q
        pip install -e packages/sage-apps --no-deps -q
        pip install -e packages/sage-llm-core --no-deps -q
        pip install -e packages/sage-studio --no-deps -q
        pip install -e packages/sage-llm-gateway --no-deps -q
        pip install -e packages/sage-cli --no-deps -q
        pip install -e packages/sage-tools --no-deps -q
        pip install -e packages/sage --no-deps -q
        log_success "增量更新完成"
    elif [ "$DEPS_INSTALLED" = true ]; then
        log_info "核心依赖已存在，仅安装 SAGE 包（带依赖检查）..."
        pip install -e packages/sage-common -q
        pip install -e packages/sage-platform -q
        pip install -e packages/sage-kernel -q
        pip install -e packages/sage-libs -q
        pip install -e packages/sage-middleware -q
        pip install -e packages/sage-apps -q
        pip install -e packages/sage-studio -q
        pip install -e packages/sage-gateway -q
        pip install -e packages/sage-cli -q
        pip install -e packages/sage-tools -q
        pip install -e packages/sage -q
        log_success "SAGE 包安装完成（复用已有依赖）"
    else
        log_info "执行完整安装（首次安装，需要下载所有依赖）..."
        chmod +x ./quickstart.sh
        export SAGE_FORCE_CHINA_MIRROR=true
        ./quickstart.sh --dev --yes --pip
    fi

    log_success "SAGE 安装/更新完成"
}

# ==============================================================================
# Step 5: Verify Installation
# ==============================================================================
verify_installation() {
    log_step "Step 5: Verify Installation"

    python -c "import sage; print('SAGE imported')"
    python -c "import sage.cli; print('sage.cli imported')"
    python -c "import sage.studio; print('sage.studio imported')"

    if command -v sage >/dev/null 2>&1; then
        sage --help > /dev/null && log_success "sage 命令可用"
    else
        log_warning "sage 命令不可用"
    fi
}

# ==============================================================================
# Step 6: Install Frontend Dependencies
# ==============================================================================
install_frontend_deps() {
    log_step "Step 6: Install Frontend Dependencies"

    echo "CONDA_PREFIX: $CONDA_PREFIX"
    echo "PATH (first 3): $(echo $PATH | tr ':' '\n' | head -3 | tr '\n' ':')"

    # 检查 Node.js 版本
    NODE_VERSION=""
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
        echo "当前 Node.js: $(node --version) at $(which node)"
    fi

    if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" -lt 18 ]; then
        log_info "安装 Node.js 20（当前版本: ${NODE_VERSION:-未安装}，需要 18+）..."
        conda install -y nodejs=20 -c conda-forge

        # 强制重新激活 conda 环境以更新 PATH
        conda deactivate
        conda activate ${ACTUAL_CONDA_ENV}

        # 刷新命令缓存
        hash -r

        echo "安装后 Node.js: $(node --version) at $(which node)"
    fi

    echo "Node.js: $(node --version)"
    echo "npm: $(npm --version)"

    # 验证 Node.js 版本满足要求
    FINAL_VERSION=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$FINAL_VERSION" -lt 18 ]; then
        log_error "Node.js 版本过低: $(node --version)，需要 18+"
        exit 1
    fi

    # 安装前端依赖
    sage studio install

    log_success "前端依赖就绪"
}

# ==============================================================================
# Step 7: Build Studio (Production)
# ==============================================================================
build_studio() {
    log_step "Step 7: Build Studio (Production)"

    if [ "$SKIP_BUILD" = true ]; then
        log_warning "跳过前端构建步骤 (--skip-build)"
        return
    fi

    # 验证 Node.js 版本
    echo "Node.js: $(node --version) at $(which node)"
    NODE_MAJOR=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 18 ]; then
        log_error "Node.js 版本过低，需要 18+"
        exit 1
    fi

    # 构建生产版本
    sage studio build

    log_success "Studio 构建完成"
}

# ==============================================================================
# Step 8: Start SAGE Studio
# ==============================================================================
start_studio() {
    log_step "Step 8: Start SAGE Studio"

    if [ "$SKIP_START" = true ]; then
        log_warning "跳过启动步骤 (--skip-start)"
        return
    fi

    log_info "启动 SAGE Studio（生产模式）..."
    log_info "端口: $PORT"

    # 使用生产模式启动
    # 功能流程：
    # 1. Builds RAG index from docs-public if needed
    # 2. Starts Gateway on port 8000
    # 3. Starts local LLM service via sageLLM (default: Qwen2.5-0.5B-Instruct)
    # 4. Starts Vite preview server on port 5173 (from built assets)

    # 启动服务（前台运行，限时3分钟，实时显示日志）
    timeout 180 sage studio start --prod --host 0.0.0.0 --port ${PORT} -y 2>&1 | tee ~/sage-studio-deploy.log &

    # 等待服务启动（轮询检查端口）
    for i in $(seq 1 30); do
        if curl -sf http://localhost:$PORT > /dev/null 2>&1; then
            log_success "Studio 服务已就绪（第 $i 次检查）"
            break
        fi
        echo "⏳ 等待服务启动... ($i/30)"
        sleep 2
    done

    log_success "Studio 已启动"
}

# ==============================================================================
# Step 9: Health Check
# ==============================================================================
health_check() {
    log_step "Step 9: Health Check"

    if [ "$SKIP_START" = true ]; then
        log_warning "跳过健康检查 (--skip-start)"
        return
    fi

    log_info "检查服务健康状态..."

    # 检查服务是否启动
    if curl -f http://localhost:${PORT} 2>/dev/null; then
        log_success "Studio 服务健康，端口 ${PORT} 可访问"
    else
        log_warning "Studio 健康检查失败，查看日志..."
        tail -50 ~/sage-studio-deploy.log || echo "暂无日志"
    fi

    # 检查端口监听状态
    echo ""
    log_info "检查端口监听状态..."
    if command -v netstat &> /dev/null; then
        netstat -tlnp 2>/dev/null | grep ":${PORT}" || log_warning "端口 ${PORT} 未在监听"
    elif command -v ss &> /dev/null; then
        ss -tlnp 2>/dev/null | grep ":${PORT}" || log_warning "端口 ${PORT} 未在监听"
    fi

    # 检查进程状态
    echo ""
    log_info "检查 SAGE Studio 进程..."
    ps aux | grep "[s]age studio" || log_warning "未找到 SAGE Studio 进程"
}

# ==============================================================================
# Step 10: Network Accessibility Check
# ==============================================================================
network_check() {
    log_step "Step 10: Network Accessibility Check"

    if [ "$SKIP_START" = true ]; then
        log_warning "跳过网络检查 (--skip-start)"
        return
    fi

    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

    log_info "测试网络可达性..."
    echo ""
    echo "测试从本机访问："

    # 测试 localhost
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT} | grep -q "200"; then
        log_success "localhost:${PORT} 可访问"
    else
        log_error "localhost:${PORT} 不可访问"
    fi

    # 测试内网IP
    if curl -s -o /dev/null -w "%{http_code}" http://${SERVER_IP}:${PORT} | grep -q "200"; then
        log_success "${SERVER_IP}:${PORT} 可访问"
    else
        log_error "${SERVER_IP}:${PORT} 不可访问"
    fi
}

# ==============================================================================
# Step 11: Deployment Summary
# ==============================================================================
deployment_summary() {
    log_step "Step 11: Deployment Summary"

    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
    HOSTNAME=$(hostname -f 2>/dev/null || echo "localhost")

    echo ""
    echo "======================================"
    echo "  SAGE Studio 部署信息"
    echo "======================================"
    echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo ""
    echo "访问地址:"
    echo "  - 本地: http://localhost:${PORT}"
    echo "  - 内网IP: http://${SERVER_IP}:${PORT}"
    echo "  - 主机名: http://${HOSTNAME}:${PORT}"
    echo ""
    echo "服务状态:"
    echo "  - 端口: ${PORT}"
    echo "  - 监听: 0.0.0.0 (所有网络接口)"
    echo ""
    echo "日志文件:"
    echo "  - Studio 日志: ~/sage-studio-deploy.log"
    echo ""
    echo "管理命令:"
    echo "  - 查看状态: ps aux | grep -E 'sage studio'"
    echo "  - 停止服务: pkill -f 'sage studio'"
    echo "  - 查看日志: tail -f ~/sage-studio-deploy.log"
    echo "======================================"
}

# ==============================================================================
# Main Execution
# ==============================================================================
main() {
    echo ""
    echo "=============================================="
    echo "  SAGE Studio 本地部署测试"
    echo "=============================================="
    echo "端口: $PORT"
    echo "跳过安装: $SKIP_INSTALL"
    echo "跳过构建: $SKIP_BUILD"
    echo "跳过启动: $SKIP_START"
    echo "=============================================="
    echo ""

    cd "$REPO_ROOT"

    # 执行所有步骤
    setup_conda
    stop_existing_services
    check_sage_installation
    install_sage
    verify_installation
    install_frontend_deps
    build_studio
    start_studio
    health_check
    network_check
    deployment_summary

    echo ""
    log_success "部署测试完成."
}

# 运行主函数
main
