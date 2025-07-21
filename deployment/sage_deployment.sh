#!/bin/bash

# SAGE System Startup Script
# 功能：
# 1. 检查并启动 Ray head 节点
# 2. 设置 Ray session 权限
# 3. 检查并启动 JobManager Daemon
# 4. 验证系统状态

set -e  # 遇到错误立即退出

# 配置参数
RAY_HEAD_PORT=${RAY_HEAD_PORT:-10001}           # GCS server port
RAY_CLIENT_PORT=${RAY_CLIENT_PORT:-10002}       # Client server port (新增)
RAY_DASHBOARD_PORT=${RAY_DASHBOARD_PORT:-8265}
RAY_TEMP_DIR=${RAY_TEMP_DIR:-/var/lib/ray_shared}
DAEMON_HOST=${DAEMON_HOST:-127.0.0.1}
DAEMON_PORT=${DAEMON_PORT:-19001}
ACTOR_NAME=${ACTOR_NAME:-sage_global_jobmanager}
NAMESPACE=${NAMESPACE:-sage_system}

# 颜色输出
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

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Command '$1' not found. Please install it first."
        exit 1
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口未被占用
    fi
}

# 检查端口范围是否可用
check_port_range() {
    local start_port=$1
    local end_port=$2
    local conflicts=()
    
    for port in $(seq $start_port $end_port); do
        if check_port $port; then
            conflicts+=($port)
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        log_warning "Ports in use: ${conflicts[*]}"
        return 1
    else
        return 0
    fi
}

# 等待端口启动
wait_for_port() {
    local port=$1
    local timeout=${2:-30}
    local count=0
    
    log_info "Waiting for port $port to be ready..."
    
    while [ $count -lt $timeout ]; do
        if check_port $port; then
            log_success "Port $port is ready"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    
    echo
    log_error "Timeout waiting for port $port"
    return 1
}

# 设置 Ray temp 目录权限
setup_ray_temp_dir() {
    log_info "Setting up Ray temp directory: $RAY_TEMP_DIR"
    
    if [ ! -d "$RAY_TEMP_DIR" ]; then
        sudo mkdir -p "$RAY_TEMP_DIR"
        log_info "Created Ray temp directory: $RAY_TEMP_DIR"
    fi
    
    sudo chmod 1777 "$RAY_TEMP_DIR"
    log_success "Ray temp directory permissions set"
}

# 设置 Ray session 权限
setup_ray_session_permissions() {
    log_info "Setting Ray session permissions..."
    
    # 查找最新的 Ray session
    local ray_session_dir="/tmp/ray"
    if [ -d "$ray_session_dir" ]; then
        # 给 session_latest 符号链接设置权限
        local session_latest="$ray_session_dir/session_latest"
        if [ -L "$session_latest" ]; then
            local actual_session=$(readlink -f "$session_latest")
            if [ -d "$actual_session" ]; then
                log_info "Setting permissions for Ray session: $actual_session"
                sudo chmod -R 755 "$actual_session" 2>/dev/null || true
                
                # 特别设置 session.json 权限
                local session_json="$actual_session/session.json"
                if [ -f "$session_json" ]; then
                    sudo chmod 644 "$session_json"
                    log_success "Ray session permissions updated"
                else
                    log_warning "session.json not found at $session_json"
                fi
            fi
        fi
    else
        log_warning "Ray session directory not found at $ray_session_dir"
    fi
}

# 检查 Ray 状态
check_ray_status() {
    if ray status >/dev/null 2>&1; then
        log_success "Ray cluster is running"
        ray status
        return 0
    else
        log_info "Ray cluster is not running"
        return 1
    fi
}

# 启动 Ray head 节点
start_ray_head() {
    log_info "Starting Ray head node..."
    
    # 检查端口冲突
    log_info "Checking port availability..."
    local ports_to_check=($RAY_HEAD_PORT $RAY_CLIENT_PORT $RAY_DASHBOARD_PORT)
    local conflicts=()
    
    for port in "${ports_to_check[@]}"; do
        if check_port $port; then
            conflicts+=($port)
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        log_error "Port conflicts detected: ${conflicts[*]}"
        log_error "Please stop conflicting services or use different ports"
        exit 1
    fi
    
    # 设置 Ray temp 目录
    setup_ray_temp_dir
    
    # 启动 Ray head，明确指定端口避免冲突
    log_info "Starting Ray with ports: GCS=$RAY_HEAD_PORT, Client=$RAY_CLIENT_PORT, Dashboard=$RAY_DASHBOARD_PORT"
    
    ray start --head \
        --temp-dir="$RAY_TEMP_DIR" \
        --disable-usage-stats \
        --verbose \
        --resources='{"jobmanager": 1.0}'  # 添加自定义资源
        # --port=$RAY_HEAD_PORT \
        # --dashboard-port=$RAY_DASHBOARD_PORT \
        #--ray-client-server-port=$RAY_CLIENT_PORT \

    
    # 等待 Ray 启动完成
    sleep 5
    
    # 设置 session 权限
    setup_ray_session_permissions
    
    # 验证 Ray 状态
    if check_ray_status; then
        log_success "Ray head node started successfully"
        log_info "Ray ports: GCS=$RAY_HEAD_PORT, Client=$RAY_CLIENT_PORT, Dashboard=$RAY_DASHBOARD_PORT"
    else
        log_error "Failed to start Ray head node"
        exit 1
    fi
}

# 检查 JobManager Daemon 状态
check_daemon_status() {
    if check_port $DAEMON_PORT; then
        # 尝试健康检查
        local health_check=$(python3 -c "
import sys
sys.path.append('$(dirname $(realpath $0))/..')
from sage_core.jobmanager_client import JobManagerClient
try:
    client = JobManagerClient('$DAEMON_HOST', $DAEMON_PORT)
    response = client.health_check()
    if response.get('status') == 'success':
        print('healthy')
    else:
        print('unhealthy')
except:
    print('error')
" 2>/dev/null)
        
        if [ "$health_check" = "healthy" ]; then
            log_success "JobManager Daemon is running and healthy"
            return 0
        else
            log_warning "JobManager Daemon is running but not healthy"
            return 1
        fi
    else
        log_info "JobManager Daemon is not running"
        return 1
    fi
}

# 启动 JobManager Daemon
start_daemon() {
    log_info "Starting JobManager Daemon..."
    
    # 检查守护进程端口
    if check_port $DAEMON_PORT; then
        log_error "Port $DAEMON_PORT is already in use"
        log_error "Please stop the conflicting service or use a different port"
        return 1
    fi
    
    # 获取脚本目录
    local script_dir=$(dirname $(realpath $0))
    local project_root=$(dirname "$script_dir")
    
    # 设置 Python 路径
    export PYTHONPATH="$project_root:$PYTHONPATH"
    
    # 后台启动守护进程
    nohup python3 "$script_dir/jobmanager_daemon.py" \
        --host "$DAEMON_HOST" \
        --port "$DAEMON_PORT" \
        --actor-name "$ACTOR_NAME" \
        --namespace "$NAMESPACE" \
        > /tmp/sage_daemon.log 2>&1 &
    
    local daemon_pid=$!
    log_info "JobManager Daemon started with PID: $daemon_pid"
    
    # 等待守护进程启动
    if wait_for_port $DAEMON_PORT 30; then
        # 再次检查健康状态
        sleep 2
        if check_daemon_status; then
            log_success "JobManager Daemon started successfully"
            echo $daemon_pid > /tmp/sage_daemon.pid
        else
            log_error "JobManager Daemon started but health check failed"
            # 显示日志以帮助调试
            log_info "Daemon log output:"
            tail -20 /tmp/sage_daemon.log
            return 1
        fi
    else
        log_error "JobManager Daemon failed to start"
        # 显示日志以帮助调试
        log_info "Daemon log output:"
        tail -20 /tmp/sage_daemon.log
        return 1
    fi
}

# 显示系统状态
show_status() {
    echo
    log_info "=== SAGE System Status ==="
    
    # Ray 状态
    echo -e "\n${BLUE}Ray Cluster:${NC}"
    if check_ray_status >/dev/null 2>&1; then
        echo "  ✓ Running"
        echo "  GCS Port: $RAY_HEAD_PORT"
        echo "  Client Port: $RAY_CLIENT_PORT" 
        echo "  Dashboard Port: $RAY_DASHBOARD_PORT"
    else
        echo "  ✗ Not running"
    fi
    
    # JobManager Daemon 状态
    echo -e "\n${BLUE}JobManager Daemon:${NC}"
    if check_daemon_status; then
        echo "  ✓ Running and healthy at $DAEMON_HOST:$DAEMON_PORT"
        
        # 显示 Actor 信息
        local actor_info=$(python3 -c "
import sys
sys.path.append('$(dirname $(realpath $0))/..')
from sage_core.jobmanager_client import JobManagerClient
try:
    client = JobManagerClient('$DAEMON_HOST', $DAEMON_PORT)
    response = client.get_actor_info()
    if response.get('status') == 'success':
        info = response.get('actor_info', {})
        print(f\"  Actor: {info.get('actor_name', 'N/A')}@{info.get('namespace', 'N/A')}\")
        print(f\"  Actor ID: {info.get('actor_id', 'N/A')}\")
    else:
        print('  Actor info unavailable')
except:
    print('  Actor info error')
" 2>/dev/null)
        echo "$actor_info"
    else
        echo "  ✗ Not running or unhealthy"
    fi
    
    # 访问信息
    echo -e "\n${BLUE}Access Information:${NC}"
    echo "  Ray Dashboard: http://localhost:$RAY_DASHBOARD_PORT"
    echo "  JobManager API: tcp://$DAEMON_HOST:$DAEMON_PORT"
    echo "  Logs: /tmp/sage/logs/"
    echo "  Daemon Log: /tmp/sage_daemon.log"
}

# 停止系统
stop_system() {
    log_info "Stopping SAGE system..."
    
    # 停止 JobManager Daemon
    if [ -f /tmp/sage_daemon.pid ]; then
        local daemon_pid=$(cat /tmp/sage_daemon.pid)
        if kill -0 $daemon_pid 2>/dev/null; then
            log_info "Stopping JobManager Daemon (PID: $daemon_pid)..."
            kill $daemon_pid
            sleep 2
            # 强制杀死
            kill -9 $daemon_pid 2>/dev/null || true
        fi
        rm -f /tmp/sage_daemon.pid
    fi
    
    # 停止 Ray
    if ray status >/dev/null 2>&1; then
        log_info "Stopping Ray cluster..."
        ray stop
    fi
    
    log_success "SAGE system stopped"
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            log_info "Starting SAGE System..."
            log_info "Configuration:"
            log_info "  Ray GCS Port: $RAY_HEAD_PORT"
            log_info "  Ray Client Port: $RAY_CLIENT_PORT"
            log_info "  Ray Dashboard Port: $RAY_DASHBOARD_PORT"
            log_info "  Daemon Port: $DAEMON_PORT"
            
            # 检查依赖
            check_command "ray"
            check_command "python3"
            check_command "lsof"
            
            # 1. 检查并启动 Ray
            if ! check_ray_status >/dev/null 2>&1; then
                start_ray_head
            else
                log_success "Ray cluster is already running"
                # 仍然需要设置权限
                setup_ray_session_permissions
            fi
            
            # 2. 检查并启动 JobManager Daemon
            if ! check_daemon_status; then
                start_daemon
            else
                log_success "JobManager Daemon is already running"
            fi
            
            # 3. 显示状态
            show_status
            ;;
            
        stop)
            stop_system
            ;;
            
        restart)
            stop_system
            sleep 2
            main start
            ;;
            
        status)
            show_status
            ;;
            
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            echo
            echo "Commands:"
            echo "  start   - Start Ray cluster and JobManager Daemon"
            echo "  stop    - Stop the entire SAGE system"
            echo "  restart - Restart the system"
            echo "  status  - Show system status"
            echo
            echo "Environment Variables:"
            echo "  RAY_HEAD_PORT=$RAY_HEAD_PORT         (GCS server port)"
            echo "  RAY_CLIENT_PORT=$RAY_CLIENT_PORT       (Client server port)"
            echo "  RAY_DASHBOARD_PORT=$RAY_DASHBOARD_PORT"
            echo "  DAEMON_HOST=$DAEMON_HOST"
            echo "  DAEMON_PORT=$DAEMON_PORT"
            exit 1
            ;;
    esac
}

# 捕获信号
trap 'log_info "Interrupted, stopping system..."; stop_system; exit 1' INT TERM

# 执行主函数
main "$@"