#!/bin/bash
#
# Ray启动器 - Bash版本
# 支持自动探测公网IP并启动Ray集群
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 默认配置
RAY_HEAD_PORT=${RAY_HEAD_PORT:-10001}
RAY_DASHBOARD_PORT=${RAY_DASHBOARD_PORT:-8265}
RAY_CLIENT_PORT=${RAY_CLIENT_PORT:-10002}
RAY_TEMP_DIR=${RAY_TEMP_DIR:-/tmp/ray_shared}
RAY_DASHBOARD_HOST=${RAY_DASHBOARD_HOST:-0.0.0.0}
AUTO_DETECT_IP=${AUTO_DETECT_IP:-true}
VERBOSE=${VERBOSE:-false}

# 获取公网IP
get_public_ip() {
    log_info "Detecting public IP address..."
    
    local detected_ip=""
    
    # 方法1: 从网络接口获取非本地IP
    log_info "Method 1: Checking network interfaces..."
    
    # 优先检查的网络接口
    local preferred_interfaces=("eth0" "ens3" "ens4" "ens5" "enp0s3" "enp0s8" "wlan0")
    
    for interface in "${preferred_interfaces[@]}"; do
        if ip addr show "$interface" >/dev/null 2>&1; then
            local ip=$(ip addr show "$interface" | grep -oP 'inet \K[\d.]+' | head -1)
            if [[ -n "$ip" && "$ip" != "127."* && "$ip" != "169.254."* ]]; then
                log_info "Found IP $ip on interface $interface"
                detected_ip="$ip"
                break
            fi
        fi
    done
    
    # 如果没找到，检查所有接口
    if [[ -z "$detected_ip" ]]; then
        log_info "Checking all network interfaces..."
        local all_ips=$(ip addr show | grep -oP 'inet \K[\d.]+' | grep -v '^127\.' | grep -v '^169\.254\.' | head -1)
        if [[ -n "$all_ips" ]]; then
            detected_ip="$all_ips"
            log_info "Found IP from all interfaces: $detected_ip"
        fi
    fi
    
    # 方法2: 通过外部服务获取公网IP
    if [[ -z "$detected_ip" ]]; then
        log_info "Method 2: Using external IP detection services..."
        
        local ip_services=(
            "https://api.ipify.org"
            "https://ifconfig.me/ip"
            "https://ipecho.net/plain"
            "https://checkip.amazonaws.com"
        )
        
        for service in "${ip_services[@]}"; do
            log_info "Trying service: $service"
            local ip=$(timeout 5 curl -s "$service" 2>/dev/null | tr -d '\n\r' | grep -oP '[\d.]+' | head -1)
            if [[ -n "$ip" && "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
                detected_ip="$ip"
                log_info "Found public IP via $service: $detected_ip"
                break
            fi
        done
    fi
    
    # 方法3: 通过连接测试获取本机IP
    if [[ -z "$detected_ip" ]]; then
        log_info "Method 3: Using connection test method..."
        
        # 使用Python获取IP（如果可用）
        if command -v python3 >/dev/null 2>&1; then
            local ip=$(python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    print(ip)
except:
    pass
" 2>/dev/null)
            if [[ -n "$ip" && "$ip" != "127."* ]]; then
                detected_ip="$ip"
                log_info "Found IP via Python method: $detected_ip"
            fi
        fi
    fi
    
    # 方法4: 使用hostname解析
    if [[ -z "$detected_ip" ]]; then
        log_info "Method 4: Using hostname resolution..."
        local hostname_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [[ -n "$hostname_ip" && "$hostname_ip" != "127."* && "$hostname_ip" != "169.254."* ]]; then
            detected_ip="$hostname_ip"
            log_info "Found IP via hostname: $detected_ip"
        fi
    fi
    
    # 如果都没找到，使用默认值
    if [[ -z "$detected_ip" ]]; then
        log_warning "Could not detect public IP, using localhost"
        detected_ip="127.0.0.1"
    fi
    
    echo "$detected_ip"
}

# 检查端口是否可用
check_port_available() {
    local port=$1
    if netstat -tln 2>/dev/null | grep -q ":$port "; then
        return 1  # 端口被占用
    else
        return 0  # 端口可用
    fi
}

# 找到可用端口
find_available_port() {
    local start_port=$1
    local max_attempts=${2:-100}
    
    for ((i=0; i<max_attempts; i++)); do
        local port=$((start_port + i))
        if check_port_available "$port"; then
            echo "$port"
            return 0
        fi
    done
    
    log_error "Could not find available port starting from $start_port"
    return 1
}

# 检查Ray是否在运行
is_ray_running() {
    # 方法1: 使用ray status命令
    if command -v ray >/dev/null 2>&1; then
        if ray status >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    # 方法2: 检查Ray进程
    if pgrep -f "ray.*raylet" >/dev/null 2>&1; then
        return 0
    fi
    
    # 方法3: 检查端口占用
    if netstat -tln 2>/dev/null | grep -q ":$RAY_HEAD_PORT "; then
        return 0
    fi
    
    return 1
}

# 停止Ray集群
stop_ray() {
    log_info "Stopping Ray cluster..."
    
    # 尝试优雅停止
    if command -v ray >/dev/null 2>&1; then
        if ray stop >/dev/null 2>&1; then
            log_success "Ray cluster stopped gracefully"
            return 0
        fi
    fi
    
    # 强制停止Ray进程
    log_warning "Graceful stop failed, forcing stop..."
    if pgrep -f "ray" >/dev/null; then
        pkill -f "ray" 2>/dev/null || true
        sleep 2
        pkill -9 -f "ray" 2>/dev/null || true
        log_success "Ray cluster force stopped"
    else
        log_info "No Ray processes found"
    fi
    
    return 0
}

# 获取系统资源
get_system_memory() {
    # 获取系统总内存（字节）
    local total_memory=$(grep MemTotal /proc/meminfo | awk '{print $2 * 1024}')
    
    # 计算对象存储内存（30%的系统内存）
    local object_store_memory=$((total_memory * 30 / 100))
    
    echo "$object_store_memory"
}

# 启动Ray头节点
start_ray_head() {
    log_info "Starting Ray head node..."
    
    # 检查是否已经在运行
    if is_ray_running; then
        log_success "Ray cluster is already running"
        show_connection_info
        return 0
    fi
    
    # 获取IP地址
    local node_ip="127.0.0.1"
    if [[ "$AUTO_DETECT_IP" == "true" ]]; then
        node_ip=$(get_public_ip)
    fi
    
    log_info "Using node IP: $node_ip"
    
    # 检查端口可用性
    local head_port="$RAY_HEAD_PORT"
    local dashboard_port="$RAY_DASHBOARD_PORT"
    
    if ! check_port_available "$head_port"; then
        log_warning "Port $head_port is not available, finding alternative..."
        head_port=$(find_available_port "$head_port")
        if [[ $? -ne 0 ]]; then
            log_error "Could not find available port for Ray head"
            return 1
        fi
        log_info "Using alternative head port: $head_port"
        RAY_HEAD_PORT="$head_port"
    fi
    
    if ! check_port_available "$dashboard_port"; then
        log_warning "Port $dashboard_port is not available, finding alternative..."
        dashboard_port=$(find_available_port "$dashboard_port")
        if [[ $? -ne 0 ]]; then
            log_error "Could not find available port for Ray dashboard"
            return 1
        fi
        log_info "Using alternative dashboard port: $dashboard_port"
        RAY_DASHBOARD_PORT="$dashboard_port"
    fi
    
    # 创建临时目录
    mkdir -p "$RAY_TEMP_DIR"
    
    # 获取系统内存
    local object_store_memory=$(get_system_memory)
    
    # 构建Ray启动命令
    local cmd=(
        "ray" "start" "--head"
        "--port=$head_port"
        "--node-ip-address=$node_ip"
        "--temp-dir=$RAY_TEMP_DIR"
        "--object-store-memory=$object_store_memory"
        "--dashboard-host=$RAY_DASHBOARD_HOST"
        "--dashboard-port=$dashboard_port"
        "--resources={\"jobmanager\": 1.0}"
    )
    
    if [[ "$VERBOSE" == "true" ]]; then
        cmd+=("--verbose")
    fi
    
    # 执行启动命令
    log_info "Executing: ${cmd[*]}"
    
    if "${cmd[@]}"; then
        log_success "Ray head node started successfully"
        
        # 等待Ray完全启动
        log_info "Waiting for Ray cluster to be ready..."
        sleep 5
        
        # 验证启动状态
        if is_ray_running; then
            log_success "Ray cluster is ready"
            show_connection_info "$node_ip" "$head_port" "$dashboard_port"
            return 0
        else
            log_error "Ray cluster failed to start properly"
            return 1
        fi
    else
        log_error "Failed to start Ray head node"
        return 1
    fi
}

# 显示连接信息
show_connection_info() {
    local node_ip=${1:-$(get_public_ip)}
    local head_port=${2:-$RAY_HEAD_PORT}
    local dashboard_port=${3:-$RAY_DASHBOARD_PORT}
    
    echo
    log_success "=== Ray Cluster Connection Info ==="
    echo "Node IP: $node_ip"
    echo "Head Port: $head_port"
    echo "Dashboard: http://$node_ip:$dashboard_port"
    echo "Ray Address: ray://$node_ip:$head_port"
    echo
    log_info "=== Environment Variables ==="
    echo "export RAY_ADDRESS=ray://$node_ip:$head_port"
    echo "export RAY_DASHBOARD_HOST=$node_ip"
    echo "export RAY_DASHBOARD_PORT=$dashboard_port"
    echo
}

# 获取Ray集群状态
get_ray_status() {
    if ! is_ray_running; then
        echo "Ray cluster is not running"
        return 1
    fi
    
    local node_ip=$(get_public_ip)
    
    echo "=== Ray Cluster Status ==="
    echo "Status: Running"
    echo "Node IP: $node_ip"
    echo "Head Port: $RAY_HEAD_PORT"
    echo "Dashboard: http://$node_ip:$RAY_DASHBOARD_PORT"
    
    # 尝试显示详细状态
    if command -v ray >/dev/null 2>&1; then
        echo
        echo "=== Detailed Status ==="
        ray status 2>/dev/null || echo "Detailed status not available"
    fi
}

# 重启Ray集群
restart_ray() {
    log_info "Restarting Ray cluster..."
    stop_ray
    sleep 3
    start_ray_head
}

# 显示帮助信息
show_help() {
    echo "Ray Launcher - 支持自动IP检测的Ray集群启动器"
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "COMMANDS:"
    echo "  start       启动Ray头节点 (默认)"
    echo "  stop        停止Ray集群"
    echo "  restart     重启Ray集群"
    echo "  status      显示Ray集群状态"
    echo "  ip          显示检测到的IP地址"
    echo "  help        显示帮助信息"
    echo
    echo "OPTIONS:"
    echo "  --head-port PORT        Ray头节点端口 (默认: 10001)"
    echo "  --dashboard-port PORT   Dashboard端口 (默认: 8265)"
    echo "  --temp-dir DIR          临时目录 (默认: /tmp/ray_shared)"
    echo "  --no-auto-ip           不自动检测IP，使用127.0.0.1"
    echo "  --verbose              详细输出"
    echo
    echo "ENVIRONMENT VARIABLES:"
    echo "  RAY_HEAD_PORT          Ray头节点端口"
    echo "  RAY_DASHBOARD_PORT     Dashboard端口"
    echo "  RAY_TEMP_DIR           临时目录"
    echo "  AUTO_DETECT_IP         是否自动检测IP (true/false)"
    echo
    echo "EXAMPLES:"
    echo "  $0                     # 启动Ray集群"
    echo "  $0 start --verbose     # 详细输出启动Ray"
    echo "  $0 status              # 查看状态"
    echo "  $0 --no-auto-ip        # 使用localhost启动"
}

# 主函数
main() {
    local command="start"
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|ip|help)
                command=$1
                shift
                ;;
            --head-port)
                RAY_HEAD_PORT=$2
                shift 2
                ;;
            --dashboard-port)
                RAY_DASHBOARD_PORT=$2
                shift 2
                ;;
            --temp-dir)
                RAY_TEMP_DIR=$2
                shift 2
                ;;
            --no-auto-ip)
                AUTO_DETECT_IP=false
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 执行命令
    case $command in
        start)
            start_ray_head
            ;;
        stop)
            stop_ray
            ;;
        restart)
            restart_ray
            ;;
        status)
            get_ray_status
            ;;
        ip)
            local ip=$(get_public_ip)
            echo "Detected IP: $ip"
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# 如果直接运行脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
