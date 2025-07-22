#!/bin/bash

# JobManager Daemon Management Module
# JobManager守护进程管理模块

# 检查 JobManager Daemon 状态
check_daemon_status() {
    if check_port $DAEMON_PORT; then
        # 尝试健康检查
        local health_check=$(python3 -c "
import sys
sys.path.append('$(get_project_root)')
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
    
    # 获取脚本目录和项目根目录
    local script_dir=$(get_script_dir)
    local project_root=$(get_project_root)
    
    # 设置 Python 路径
    export PYTHONPATH="$project_root:$PYTHONPATH"
    
    # 创建日志目录
    mkdir -p "$SAGE_LOG_DIR/daemon"
    
    # 后台启动守护进程
    local daemon_log="$SAGE_LOG_DIR/daemon/sage_daemon.log"
    nohup python3 "$script_dir/jobmanager_daemon.py" \
        --host "$DAEMON_HOST" \
        --port "$DAEMON_PORT" \
        --actor-name "$ACTOR_NAME" \
        --namespace "$NAMESPACE" \
        > "$daemon_log" 2>&1 &
    
    local daemon_pid=$!
    log_info "JobManager Daemon started with PID: $daemon_pid"
    
    # 保存PID
    create_pid_file "daemon" "$daemon_pid"
    
    # 等待守护进程启动
    if wait_for_port $DAEMON_PORT $STARTUP_TIMEOUT; then
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
        log_error "JobManager Daemon failed to start"
        # 显示日志以帮助调试
        log_info "Daemon log output:"
        tail -20 "$daemon_log"
        return 1
    fi
}

# 停止 JobManager Daemon
stop_daemon() {
    log_info "Stopping JobManager Daemon..."
    
    # 尝试从PID文件读取PID
    local daemon_pid
    if daemon_pid=$(read_pid_file "daemon"); then
        if is_process_running "$daemon_pid"; then
            log_info "Stopping JobManager Daemon (PID: $daemon_pid)..."
            kill "$daemon_pid"
            
            # 等待进程停止
            local count=0
            while [ $count -lt $SHUTDOWN_TIMEOUT ] && is_process_running "$daemon_pid"; do
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
        local daemon_processes=$(lsof -ti :$DAEMON_PORT)
        if [ -n "$daemon_processes" ]; then
            log_info "Found processes using port $DAEMON_PORT: $daemon_processes"
            echo "$daemon_processes" | xargs kill
        fi
    fi
    
    # 验证停止状态
    if ! check_port $DAEMON_PORT; then
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
    if check_daemon_status; then
        echo "JobManager Daemon Status: Running and Healthy"
        echo "Host: $DAEMON_HOST"
        echo "Port: $DAEMON_PORT"
        echo "API Endpoint: tcp://$DAEMON_HOST:$DAEMON_PORT"
        
        # 显示 Actor 信息
        local actor_info=$(python3 -c "
import sys
sys.path.append('$(get_project_root)')
from sage_core.jobmanager_client import JobManagerClient
try:
    client = JobManagerClient('$DAEMON_HOST', $DAEMON_PORT)
    response = client.get_actor_info()
    if response.get('status') == 'success':
        info = response.get('actor_info', {})
        print(f\"Actor Name: {info.get('actor_name', 'N/A')}\")
        print(f\"Namespace: {info.get('namespace', 'N/A')}\")
        print(f\"Actor ID: {info.get('actor_id', 'N/A')}\")
    else:
        print('Actor info unavailable')
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
