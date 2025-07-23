#!/bin/bash

# Health Check and Status Monitoring Module
# 健康检查和状态监控模块

# 检查系统依赖
check_system_dependencies() {
    log_info "Checking system dependencies..."
    local missing_deps=()
    
    # 必需的命令列表
    local required_commands=("ray" "python3" "lsof" "ps" "kill")
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps+=("$cmd")
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies and try again"
        return 1
    else
        log_success "All system dependencies are available"
        return 0
    fi
}

# 检查Python环境
check_python_environment() {
    log_info "Checking Python environment..."
    
    # 检查Python版本
    local python_version=$(python3 --version 2>&1)
    log_info "Python version: $python_version"
    
    # 检查SAGE相关模块
    local project_root=$(get_project_root)
    export PYTHONPATH="$project_root:$PYTHONPATH"
    
    local python_cmd=$(get_python_env_command "sage")
    local env_info=$(get_python_env_info)
    log_info "Checking Python environment: $env_info"
    
    local modules_check=$($python_cmd -c "
import sys
missing_modules = []
try:
    import ray
    print(f'Ray version: {ray.__version__}')
except ImportError:
    missing_modules.append('ray')

try:
    import sage_core
    print('SAGE core module: OK')
except ImportError:
    missing_modules.append('sage_core')

if missing_modules:
    print(f'Missing modules: {missing_modules}')
    sys.exit(1)
else:
    print('Python environment: OK')
" 2>&1)
    
    if [ $? -eq 0 ]; then
        log_success "Python environment check passed"
        echo "$modules_check" | while read line; do log_info "$line"; done
        return 0
    else
        log_error "Python environment check failed"
        echo "$modules_check" | while read line; do log_error "$line"; done
        return 1
    fi
}

# 检查网络端口
check_network_ports() {
    log_info "Checking network port status..."
    
    local ports_info=(
        "Ray GCS:$RAY_HEAD_PORT"
        "Ray Client:$RAY_CLIENT_PORT" 
        "Ray Dashboard:$RAY_DASHBOARD_PORT"
        "JobManager Daemon:$DAEMON_PORT"
    )
    
    for port_info in "${ports_info[@]}"; do
        local name="${port_info%:*}"
        local port="${port_info#*:}"
        
        if check_port "$port"; then
            log_success "$name (port $port): In use"
        else
            log_info "$name (port $port): Available"
        fi
    done
}

# 系统整体健康检查
perform_health_check() {
    log_info "=== SAGE System Health Check ==="
    local health_score=0
    local total_checks=5
    
    # 1. 系统依赖检查
    echo -e "\n${BLUE}1. System Dependencies:${NC}"
    if check_system_dependencies; then
        health_score=$((health_score + 1))
    fi
    
    # 2. Python环境检查
    echo -e "\n${BLUE}2. Python Environment:${NC}"
    if check_python_environment; then
        health_score=$((health_score + 1))
    fi
    
    # 3. Ray集群状态
    echo -e "\n${BLUE}3. Ray Cluster:${NC}"
    if check_ray_status >/dev/null 2>&1; then
        log_success "Ray cluster is running"
        health_score=$((health_score + 1))
    else
        log_warning "Ray cluster is not running"
    fi
    
    # 4. JobManager守护进程状态
    echo -e "\n${BLUE}4. JobManager Daemon:${NC}"
    if check_daemon_status; then
        health_score=$((health_score + 1))
    else
        log_warning "JobManager Daemon is not running or unhealthy"
    fi
    
    # 5. CLI工具状态
    echo -e "\n${BLUE}5. CLI Tools:${NC}"
    if check_cli_tools; then
        health_score=$((health_score + 1))
    else
        log_warning "CLI tools are not properly configured"
    fi
    
    # 6. 网络端口状态
    echo -e "\n${BLUE}6. Network Ports:${NC}"
    check_network_ports
    
    # 健康评分
    echo -e "\n${BLUE}=== Health Summary ===${NC}"
    local health_percentage=$((health_score * 100 / total_checks))
    
    if [ $health_percentage -eq 100 ]; then
        log_success "System Health: Excellent ($health_score/$total_checks checks passed)"
        return 0
    elif [ $health_percentage -ge 80 ]; then
        log_success "System Health: Good ($health_score/$total_checks checks passed)"
        return 0
    elif [ $health_percentage -ge 60 ]; then
        log_warning "System Health: Fair ($health_score/$total_checks checks passed)"
        return 1
    else
        log_error "System Health: Poor ($health_score/$total_checks checks passed)"
        return 1
    fi
}

# 显示系统状态
show_system_status() {
    echo
    log_info "=== SAGE System Status ==="
    
    # Ray 状态
    echo -e "\n${BLUE}Ray Cluster:${NC}"
    if check_ray_status >/dev/null 2>&1; then
        echo "  ✓ Running"
        echo "  GCS Port: $RAY_HEAD_PORT"
        echo "  Client Port: $RAY_CLIENT_PORT" 
        echo "  Dashboard Port: $RAY_DASHBOARD_PORT"
        echo "  Dashboard URL: http://localhost:$RAY_DASHBOARD_PORT"
    else
        echo "  ✗ Not running"
    fi
    
    # JobManager Daemon 状态
    echo -e "\n${BLUE}JobManager Daemon:${NC}"
    if check_daemon_status; then
        echo "  ✓ Running and healthy"
        echo "  Host: 127.0.0.1"
        echo "  Port: 19001" 
        echo "  API Endpoint: tcp://127.0.0.1:19001"
        
        # 获取项目根目录
        local project_root
        if command -v get_project_root >/dev/null 2>&1; then
            project_root=$(get_project_root)
        else
            project_root="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
        fi
        
        # 显示 Actor 信息
        local python_cmd=$(get_python_env_command "sage")
        local actor_info=$($python_cmd -c "
import sys
sys.path.append('$project_root')
try:
    from sage_core.jobmanager_client import JobManagerClient
    client = JobManagerClient('127.0.0.1', 19001)
    response = client._send_request({'action': 'get_actor_info', 'request_id': '123'})
    if response and response.get('status') == 'success':
        info = response.get('actor_info', {})
        print(f\"  Actor: {info.get('actor_name', 'N/A')}@{info.get('namespace', 'N/A')}\")
        print(f\"  Actor ID: {info.get('actor_id', 'N/A')}\")
        print(f\"  Status: {info.get('status', 'N/A')}\")
    else:
        print('  Actor info unavailable')
except Exception as e:
    print(f'  Actor info error: {e}')
" 2>/dev/null)
        echo "$actor_info"
    else
        echo "  ✗ Not running or unhealthy"
    fi
    
    # 命令行工具状态
    echo -e "\n${BLUE}Command Line Tools:${NC}"
    if command -v sage-jm >/dev/null 2>&1; then
        echo "  ✓ sage-jm command available"
        echo "  Location: $(which sage-jm)"
    else
        echo "  ✗ sage-jm command not available"
    fi
    
    # 系统资源状态
    echo -e "\n${BLUE}System Resources:${NC}"
    echo "  CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')%"
    echo "  Memory Usage: $(free | grep Mem | awk '{printf("%.1f%%\n", $3/$2 * 100.0)}')"
    echo "  Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
    
    # 重要路径信息
    echo -e "\n${BLUE}Important Paths:${NC}"
    echo "  Project Root: $(get_project_root)"
    echo "  Log Directory: $SAGE_LOG_DIR"
    echo "  PID Directory: $SAGE_PID_DIR"
    echo "  Ray Temp Directory: $RAY_TEMP_DIR"
    
    # 日志文件状态
    echo -e "\n${BLUE}Log Files:${NC}"
    if [ -d "$SAGE_LOG_DIR" ]; then
        local log_count=$(find "$SAGE_LOG_DIR" -name "*.log" -type f | wc -l)
        echo "  Log files found: $log_count"
        
        # 显示最近的几个日志文件
        local recent_logs=$(find "$SAGE_LOG_DIR" -name "*.log" -type f -printf '%T+ %p\n' | sort -r | head -3 | cut -d' ' -f2-)
        if [ -n "$recent_logs" ]; then
            echo "  Recent logs:"
            echo "$recent_logs" | while read log_file; do
                local size=$(du -h "$log_file" | cut -f1)
                echo "    $log_file ($size)"
            done
        fi
    else
        echo "  Log directory not found: $SAGE_LOG_DIR"
    fi
}

# 监控系统状态（实时）
monitor_system_status() {
    local refresh_interval=${1:-5}
    
    log_info "Starting system monitoring (refresh every ${refresh_interval}s, Ctrl+C to stop)..."
    
    while true; do
        clear
        echo "SAGE System Monitor - $(date)"
        echo "=================================="
        
        # 简化的状态显示
        echo -e "\n${BLUE}Services Status:${NC}"
        
        # Ray状态
        if check_ray_status >/dev/null 2>&1; then
            echo "  Ray Cluster: ✓ Running"
        else
            echo "  Ray Cluster: ✗ Stopped"
        fi
        
        # Daemon状态
        if check_daemon_status >/dev/null 2>&1; then
            echo "  JobManager: ✓ Healthy"
        else
            echo "  JobManager: ✗ Unhealthy"
        fi
        
        # 系统资源
        echo -e "\n${BLUE}System Resources:${NC}"
        echo "  CPU: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')%"
        echo "  MEM: $(free | grep Mem | awk '{printf("%.1f%%\n", $3/$2 * 100.0)}')"
        echo "  DISK: $(df -h / | awk 'NR==2{printf "%s", $5}')"
        
        echo -e "\n${BLUE}Press Ctrl+C to stop monitoring${NC}"
        sleep "$refresh_interval"
    done
}
