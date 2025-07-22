#!/bin/bash

# JobManager Daemon Management Module
# JobManager守护进程管理模块

# 检查 JobManager Daemon 状态
check_daemon_status() {
    # 使用默认配置
    local daemon_host="127.0.0.1"
    local daemon_port=19001
    
    if check_port $daemon_port; then
        # 获取项目根目录
        local project_root
        if command -v get_project_root >/dev/null 2>&1; then
            project_root=$(get_project_root)
        else
            # 备用方式：从当前脚本目录推导
            project_root="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
        fi
        
        # 尝试健康检查
        local health_check=$(python3 -c "
import sys
sys.path.append('$project_root')
try:
    from sage_core.jobmanager_client import JobManagerClient
    client = JobManagerClient('$daemon_host', $daemon_port)
    response = client.health_check()
    if response and response.get('status') == 'success':
        print('healthy')
    else:
        print('unhealthy')
except Exception as e:
    print('error')
    print(f'Debug: {str(e)}', file=sys.stderr)
" 2>&1)
        
        # 检查结果（只取第一行，忽略调试信息）
        local status=$(echo "$health_check" | head -n1)
        
        if [ "$status" = "healthy" ]; then
            log_success "JobManager Daemon is running and healthy"
            return 0
        else
            log_warning "JobManager Daemon is running but not healthy"
            log_detail "Health check result: $health_check"
            return 1
        fi
    else
        log_info "JobManager Daemon is not running (port $daemon_port not in use)"
        return 1
    fi
}

# 启动 JobManager Daemon
start_daemon() {
    log_info "Starting JobManager Daemon..."
    
    # 使用默认配置
    local daemon_host="127.0.0.1"
    local daemon_port=19001
    local actor_name="sage_global_jobmanager"
    local namespace="sage_system"
    local sage_log_dir="${SAGE_LOG_DIR:-$HOME/SAGE/logs}"
    
    # 检查守护进程端口
    if check_port $daemon_port; then
        log_error "Port $daemon_port is already in use"
        log_error "Please stop the conflicting service or use a different port"
        return 1
    fi
    
    # 获取脚本目录和项目根目录
    local script_dir
    local project_root
    
    if command -v get_script_dir >/dev/null 2>&1; then
        script_dir=$(get_script_dir)
        project_root=$(get_project_root)
    else
        # 备用方式：从当前脚本位置推导
        local current_script="$(realpath "${BASH_SOURCE[0]}")"
        script_dir="$(dirname "$current_script")"
        project_root="$(dirname "$script_dir")"
    fi
    
    # 设置 Python 路径
    export PYTHONPATH="$project_root:$PYTHONPATH"
    
    # 创建日志目录
    mkdir -p "$sage_log_dir/daemon"
    
    # 后台启动守护进程 - 使用绝对路径确保正确执行
    local daemon_script="$project_root/deployment/jobmanager_daemon.py"
    local daemon_log="$sage_log_dir/daemon/sage_daemon.log"
    
    if [ ! -f "$daemon_script" ]; then
        log_error "Daemon script not found: $daemon_script"
        return 1
    fi
    
    nohup python3 "$daemon_script" \
        --host "$daemon_host" \
        --port "$daemon_port" \
        --actor-name "$actor_name" \
        --namespace "$namespace" \
        > "$daemon_log" 2>&1 &
    
    local daemon_pid=$!
    log_info "JobManager Daemon started with PID: $daemon_pid"
    
    # 保存PID
    create_pid_file "daemon" "$daemon_pid"
    
    # 等待守护进程启动
    local startup_timeout=30
    if wait_for_port $daemon_port $startup_timeout; then
        # 再次检查健康状态
        sleep 2
        if check_daemon_status; then
            log_success "JobManager Daemon started successfully"
            return 0
        else
            log_error "JobManager Daemon started but health check failed"
            # 显示日志以帮助调试
            log_info "Daemon log output:"
            tail -20 "$daemon_log"
            return 1
        fi
    else
        log_error "JobManager Daemon failed to start within $startup_timeout seconds"
        # 显示日志以帮助调试
        log_info "Daemon log output:"
        tail -20 "$daemon_log"
        return 1
    fi
}

# 停止 JobManager Daemon
stop_daemon() {
    log_info "Stopping JobManager Daemon..."
    
    # 使用默认配置
    local daemon_port=19001
    local shutdown_timeout=15
    
    # 尝试从PID文件读取PID
    local daemon_pid
    if daemon_pid=$(read_pid_file "daemon"); then
        if is_process_running "$daemon_pid"; then
            log_info "Stopping JobManager Daemon (PID: $daemon_pid)..."
            kill "$daemon_pid"
            
            # 等待进程停止
            local count=0
            while [ $count -lt $shutdown_timeout ] && is_process_running "$daemon_pid"; do
                sleep 1
                count=$((count + 1))
                echo -n "."
            done
            echo
            
            # 如果进程仍在运行，强制杀死
            if is_process_running "$daemon_pid"; then
                log_warning "Force killing daemon process"
                kill -9 "$daemon_pid" 2>/dev/null || true
            fi
        fi
        remove_pid_file "daemon"
    else
        log_warning "PID file not found, searching for daemon process..."
        # 尝试通过端口查找并停止进程
        if command -v lsof >/dev/null 2>&1; then
            local daemon_processes=$(lsof -ti :$daemon_port 2>/dev/null || true)
            if [ -n "$daemon_processes" ]; then
                log_info "Found processes using port $daemon_port: $daemon_processes"
                echo "$daemon_processes" | xargs kill 2>/dev/null || true
            fi
        else
            log_warning "lsof not available, cannot search by port"
        fi
    fi
    
    # 验证停止状态
    if ! check_port $daemon_port; then
        log_success "JobManager Daemon stopped successfully"
        return 0
    else
        log_warning "JobManager Daemon may still be running"
        return 1
    fi
}

# 重启 JobManager Daemon
restart_daemon() {
    log_info "Restarting JobManager Daemon..."
    stop_daemon
    sleep 3
    start_daemon
}

# 获取守护进程信息
get_daemon_info() {
    # 使用默认配置
    local daemon_host="127.0.0.1"
    local daemon_port=19001
    
    if check_daemon_status; then
        echo "JobManager Daemon Status: Running and Healthy"
        echo "Host: $daemon_host"
        echo "Port: $daemon_port"
        echo "API Endpoint: tcp://$daemon_host:$daemon_port"
        
        # 获取项目根目录
        local project_root
        if command -v get_project_root >/dev/null 2>&1; then
            project_root=$(get_project_root)
        else
            project_root="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"
        fi
        
        # 显示 Actor 信息
        local actor_info=$(python3 -c "
import sys
sys.path.append('$project_root')
try:
    from sage_core.jobmanager_client import JobManagerClient
    client = JobManagerClient('$daemon_host', $daemon_port)
    response = client._send_request({'action': 'get_actor_info', 'request_id': '123'})
    if response and response.get('status') == 'success':
        info = response.get('actor_info', {})
        print(f\"Actor Name: {info.get('actor_name', 'N/A')}\")
        print(f\"Namespace: {info.get('namespace', 'N/A')}\")  
        print(f\"Actor ID: {info.get('actor_id', 'N/A')}\")
        print(f\"Status: {info.get('status', 'N/A')}\")
    else:
        print('Actor info unavailable - Response:', response)
except Exception as e:
    print(f'Actor info error: {e}')
" 2>/dev/null)
        echo "$actor_info"
        
        # 显示PID信息
        if daemon_pid=$(read_pid_file "daemon"); then
            echo "Process ID: $daemon_pid"
        fi
        
        return 0
    else
        echo "JobManager Daemon Status: Not Running or Unhealthy"
        return 1
    fi
}
