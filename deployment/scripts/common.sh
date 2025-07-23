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
    
    # 优先使用 ss (更可靠，特别是在多租户环境下)
    if command -v ss >/dev/null 2>&1; then
        if ss -ltn | grep -q ":$port "; then
            return 0  # 端口被占用
        fi
    fi
    
    # 备用方案：使用 netstat
    if command -v netstat >/dev/null 2>&1; then
        if netstat -ltn | grep -q ":$port "; then
            return 0  # 端口被占用
        fi
    fi
    
    # 最后备用方案：使用 lsof (可能在多租户环境下失败)
    if command -v lsof >/dev/null 2>&1; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 0  # 端口被占用
        fi
    fi
    
    return 1  # 端口未被占用
}

# 查找使用指定端口的进程PID
find_port_processes() {
    local port=$1
    local pids=""
    
    # 优先使用 ss (更可靠，特别是在多租户环境下)
    if command -v ss >/dev/null 2>&1; then
        # 需要sudo权限才能看到进程信息
        if command -v sudo >/dev/null 2>&1; then
            pids=$(sudo ss -ltnp 2>/dev/null | grep ":$port " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | head -1)
        fi
    fi
    
    # 备用方案：使用 netstat
    if [ -z "$pids" ] && command -v netstat >/dev/null 2>&1; then
        if command -v sudo >/dev/null 2>&1; then
            pids=$(sudo netstat -ltnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$' | head -1)
        fi
    fi
    
    # 第三备用方案：使用 lsof
    if [ -z "$pids" ] && command -v lsof >/dev/null 2>&1; then
        if command -v sudo >/dev/null 2>&1; then
            pids=$(sudo lsof -ti :$port 2>/dev/null | head -1)
        else
            pids=$(lsof -ti :$port 2>/dev/null | head -1)
        fi
    fi
    
    # 最后备用方案：通过进程命令行搜索
    if [ -z "$pids" ]; then
        # 搜索包含端口的进程命令行
        pids=$(ps aux | grep "[p]ort.*$port\\|--port.*$port\\|:$port" | awk '{print $2}' | head -1)
    fi
    
    echo "$pids"
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

# 创建PID文件（适配共享机器）
create_pid_file() {
    local service_name=$1
    local pid=$2
    local pid_dir="/tmp/sage"
    
    # 确保目录存在并且有正确的权限
    if [ ! -d "$pid_dir" ]; then
        mkdir -p "$pid_dir" 2>/dev/null || {
            log_warning "Cannot create $pid_dir, trying with sudo"
            sudo mkdir -p "$pid_dir"
            
            # 检查用户是否在sudo组并设置相应权限
            if groups | grep -q sudo; then
                sudo chown root:sudo "$pid_dir"
                sudo chmod 775 "$pid_dir"
                sudo chmod g+s "$pid_dir"
                log_info "PID directory configured for sudo group sharing"
            else
                sudo chown $(whoami):$(id -gn) "$pid_dir"
                log_info "PID directory configured for single user"
            fi
        }
    fi
    
    # 检查目录权限
    if [ ! -w "$pid_dir" ]; then
        log_warning "No write permission for $pid_dir, fixing permissions"
        if groups | grep -q sudo; then
            # 为sudo组用户设置共享权限
            sudo chown root:sudo "$pid_dir"
            sudo chmod 775 "$pid_dir"
            sudo chmod g+s "$pid_dir"
        else
            # 为普通用户设置个人权限
            sudo chown $(whoami):$(id -gn) "$pid_dir"
            chmod 755 "$pid_dir"
        fi
    fi
    
    # 创建PID文件
    local pid_file="$pid_dir/${service_name}.pid"
    if echo "$pid" > "$pid_file" 2>/dev/null; then
        # 如果是sudo组用户，确保文件权限正确
        if groups | grep -q sudo; then
            chmod 664 "$pid_file" 2>/dev/null || true
        fi
        log_info "PID file created: $pid_file"
    else
        log_error "Failed to create PID file: $pid_file"
        return 1
    fi
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

# 检测并获取合适的Python环境命令
get_python_env_command() {
    local preferred_env="${1:-sage}"
    local python_cmd="python3"
    
    # 检查是否在虚拟环境中
    if [ -n "$VIRTUAL_ENV" ]; then
        # log_info "Using active virtual environment: $VIRTUAL_ENV"
        echo "$python_cmd"
        return 0
    fi
    
    # 检查conda环境
    if command -v conda >/dev/null 2>&1; then
        # 检查是否已经在目标环境中
        if [ "$CONDA_DEFAULT_ENV" = "$preferred_env" ]; then
            # log_info "Already in conda environment: $preferred_env"
            echo "$python_cmd"
            return 0
        fi
        
        # 检查目标环境是否存在
        if conda info --envs 2>/dev/null | grep -q "^${preferred_env} "; then
            # log_info "Using conda environment: $preferred_env"
            echo "conda run -n $preferred_env python3"
            return 0
        elif conda info --envs 2>/dev/null | grep -q " ${preferred_env} "; then
            # log_info "Using conda environment: $preferred_env"
            echo "conda run -n $preferred_env python3"
            return 0
        else
            log_warning "Conda environment '$preferred_env' not found, available environments:"
            conda info --envs 2>/dev/null | grep -v "^#" | head -5
        fi
    fi
    
    # 检查mamba环境
    if command -v mamba >/dev/null 2>&1; then
        if mamba info --envs 2>/dev/null | grep -q "^${preferred_env} \\|  ${preferred_env} "; then
            # log_info "Using mamba environment: $preferred_env"
            echo "mamba run -n $preferred_env python3"
            return 0
        fi
    fi
    
    # 检查micromamba环境
    if command -v micromamba >/dev/null 2>&1; then
        if micromamba env list 2>/dev/null | grep -q "^${preferred_env} \\|  ${preferred_env} "; then
            # log_info "Using micromamba environment: $preferred_env"
            echo "micromamba run -n $preferred_env python3"
            return 0
        fi
    fi
    
    # 回退到系统Python
    # log_info "Using system Python (no preferred environment found)"
    echo "$python_cmd"
    return 1  # 返回1表示没有找到首选环境，但仍提供备用选项
}

# 在指定环境中执行Python命令
run_python_in_env() {
    local env_name="${1:-sage}"
    shift
    local python_args="$@"
    
    local python_cmd=$(get_python_env_command "$env_name")
    eval "$python_cmd $python_args"
}

# 获取环境信息用于显示
get_python_env_info() {
    local env_info=""
    
    if [ -n "$VIRTUAL_ENV" ]; then
        env_info="Virtual Env: $(basename "$VIRTUAL_ENV")"
    elif [ -n "$CONDA_DEFAULT_ENV" ]; then
        env_info="Conda Env: $CONDA_DEFAULT_ENV"
    elif command -v conda >/dev/null 2>&1 && conda info --envs 2>/dev/null | grep -q "sage"; then
        env_info="Conda Available (sage env detected)"
    elif command -v mamba >/dev/null 2>&1 && mamba info --envs 2>/dev/null | grep -q "sage"; then
        env_info="Mamba Available (sage env detected)"
    else
        env_info="System Python"
    fi
    
    echo "$env_info"
}
