#!/bin/bash
#
# SAGE Studio 启动脚本
# 用于启动和管理 Studio 前端服务
#

# 动态获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 脚本配置
STUDIO_DIR="$SAGE_ROOT/packages/sage-tools/src/sage/tools/frontend/studio"
STUDIO_PORT=4200
STUDIO_HOST="0.0.0.0"
PID_FILE="/tmp/sage-studio.pid"
RUN_DIR="$HOME/.sage/run"
PID_FILE="$RUN_DIR/sage-studio.pid"
LOG_FILE="$RUN_DIR/sage-studio.log"

LOG_DIR="$HOME/.sage/logs"
LOG_FILE="$LOG_DIR/sage-studio.log"

# Ensure log directory exists with proper permissions
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    chmod 700 "$LOG_DIR"
fi
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装，请先安装 Node.js 18+"
        exit 1
    fi
    
    # 检查版本
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        print_error "Node.js 版本过低，需要 18+，当前版本: $(node --version)"
        exit 1
    fi
    
    # 检查 npm
    if ! command -v npm &> /dev/null; then
        print_error "npm 未安装"
        exit 1
    fi
    
    # 检查项目目录
    if [ ! -d "$STUDIO_DIR" ]; then
        print_error "Studio 项目目录不存在: $STUDIO_DIR"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 安装依赖
install_dependencies() {
    print_info "安装 Studio 依赖..."
    
    cd "$STUDIO_DIR" || exit 1
    
    if [ ! -d "node_modules" ] || [ ! -f "package-lock.json" ]; then
        print_info "正在安装 npm 依赖..."
        npm install
        if [ $? -eq 0 ]; then
            print_success "依赖安装完成"
        else
            print_error "依赖安装失败"
            exit 1
        fi
    else
        print_info "依赖已存在，跳过安装"
    fi
}

# 启动 Studio
start_studio() {
    print_info "启动 SAGE Studio..."
    
    # 检查是否已经运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_warning "Studio 已经在运行 (PID: $PID)"
            print_info "访问地址: http://localhost:$STUDIO_PORT"
            return 0
        else
            # PID文件存在但进程不存在，清理
            rm -f "$PID_FILE"
        fi
    fi
    
    cd "$STUDIO_DIR" || exit 1
    
    # 后台启动
    nohup npm start > "$LOG_FILE" 2>&1 &
    STUDIO_PID=$!
    
    # 保存PID
    echo $STUDIO_PID > "$PID_FILE"
    
    # 等待启动
    print_info "等待服务启动..."
    sleep 5
    
    # 检查是否启动成功
    if ps -p $STUDIO_PID > /dev/null 2>&1; then
        print_success "Studio 启动成功!"
        print_info "PID: $STUDIO_PID"
        print_info "访问地址: http://localhost:$STUDIO_PORT"
        print_info "日志文件: $LOG_FILE"
    else
        print_error "Studio 启动失败"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 停止 Studio
stop_studio() {
    print_info "停止 SAGE Studio..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            sleep 2
            
            # 强制杀死如果还在运行
            # 等待进程退出，最多 10 秒
            TIMEOUT=10
            while [ $TIMEOUT -gt 0 ]; do
                if ! ps -p $PID > /dev/null 2>&1; then
                    break
                fi
                sleep 1
                TIMEOUT=$((TIMEOUT - 1))
            done
            
            # 强制杀死如果还在运行
            if ps -p $PID > /dev/null 2>&1; then
                print_warning "进程未能在规定时间内退出，强制杀死 (SIGKILL)"
                kill -9 $PID
            fi
            
            rm -f "$PID_FILE"
            print_success "Studio 已停止"
        else
            print_warning "Studio 进程不存在"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "Studio 未运行"
    fi
}

# 检查状态
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            print_success "Studio 正在运行 (PID: $PID)"
            print_info "访问地址: http://localhost:$STUDIO_PORT"
            
            # 检查端口
            if command -v netstat &> /dev/null; then
                if netstat -tuln | grep ":$STUDIO_PORT " > /dev/null; then
                    print_success "端口 $STUDIO_PORT 监听正常"
                else
                    print_warning "端口 $STUDIO_PORT 未监听"
                fi
            fi
        else
            print_error "Studio 进程不存在 (PID文件存在但进程已死)"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "Studio 未运行"
    fi
}

# 查看日志
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "显示最近 50 行日志:"
        echo ""
        tail -n 50 "$LOG_FILE"
    else
        print_warning "日志文件不存在: $LOG_FILE"
    fi
}

# 主函数
main() {
    case "$1" in
        start)
            check_dependencies
            install_dependencies
            start_studio
            ;;
        stop)
            stop_studio
            ;;
        restart)
            stop_studio
            sleep 2
            check_dependencies
            install_dependencies
            start_studio
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs
            ;;
        install)
            check_dependencies
            install_dependencies
            ;;
        *)
            echo "使用方法: $0 {start|stop|restart|status|logs|install}"
            echo ""
            echo "命令说明:"
            echo "  start    - 启动 Studio 服务"
            echo "  stop     - 停止 Studio 服务"
            echo "  restart  - 重启 Studio 服务"
            echo "  status   - 检查服务状态"
            echo "  logs     - 查看运行日志"
            echo "  install  - 安装依赖"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
