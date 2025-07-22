#!/bin/bash

# Common functions and utilities for SAGE deployment
# 公共函数和工具库

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

# 获取脚本目录
get_script_dir() {
    echo "$(dirname $(realpath $0))"
}

# 获取项目根目录
get_project_root() {
    echo "$(dirname $(get_script_dir))"
}

# 加载配置文件
load_config() {
    local config_file="$(get_script_dir)/config/environment.sh"
    if [ -f "$config_file" ]; then
        source "$config_file"
        log_info "Configuration loaded from $config_file"
    else
        log_warning "Configuration file not found: $config_file"
        log_info "Using default configuration"
    fi
}

# 创建PID文件
create_pid_file() {
    local service_name=$1
    local pid=$2
    local pid_dir="/tmp/sage"
    
    mkdir -p "$pid_dir"
    echo "$pid" > "$pid_dir/${service_name}.pid"
    log_info "PID file created: $pid_dir/${service_name}.pid"
}

# 读取PID文件
read_pid_file() {
    local service_name=$1
    local pid_file="/tmp/sage/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
        return 0
    else
        return 1
    fi
}

# 删除PID文件
remove_pid_file() {
    local service_name=$1
    local pid_file="/tmp/sage/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        rm -f "$pid_file"
        log_info "PID file removed: $pid_file"
    fi
}

# 检查进程是否运行
is_process_running() {
    local pid=$1
    if kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}
