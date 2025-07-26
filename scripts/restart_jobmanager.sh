#!/bin/bash
# 
# SAGE JobManager 重启脚本 (Shell版本)
# 用法: ./restart_jobmanager.sh [--host HOST] [--port PORT] [--force]
#

set -e

# 默认配置
HOST="127.0.0.1"
PORT="19001"
FORCE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  --host HOST     JobManager主机地址 (默认: 127.0.0.1)"
            echo "  --port PORT     JobManager端口 (默认: 19001)"
            echo "  --force         强制重启，不询问确认"
            echo "  -h, --help      显示此帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 -h 或 --help 查看帮助"
            exit 1
            ;;
    esac
done

echo "=================================="
echo "SAGE JobManager 重启工具 (Shell版)"
echo "=================================="
echo "目标地址: $HOST:$PORT"
echo "项目目录: $PROJECT_ROOT"

# 检查JobManager是否运行
check_running() {
    if command -v nc >/dev/null 2>&1; then
        nc -z "$HOST" "$PORT" 2>/dev/null
    elif command -v telnet >/dev/null 2>&1; then
        timeout 2 telnet "$HOST" "$PORT" >/dev/null 2>&1
    else
        # 使用Python检查
        python3 -c "
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('$HOST', $PORT))
    sock.close()
    exit(0 if result == 0 else 1)
except:
    exit(1)
"
    fi
}

# 停止JobManager
stop_jobmanager() {
    echo "正在停止JobManager..."
    
    # 查找并终止JobManager进程
    PIDS=$(pgrep -f "job_manager.*--port $PORT" 2>/dev/null || true)
    
    if [ -n "$PIDS" ]; then
        echo "找到JobManager进程: $PIDS"
        
        # 首先发送TERM信号
        for pid in $PIDS; do
            echo "向进程 $pid 发送SIGTERM..."
            kill -TERM "$pid" 2>/dev/null || true
        done
        
        # 等待进程退出
        for i in {1..10}; do
            if ! check_running; then
                echo "JobManager已停止"
                return 0
            fi
            echo "等待进程退出... ($i/10)"
            sleep 1
        done
        
        # 如果仍未退出，发送KILL信号
        echo "进程未正常退出，发送SIGKILL..."
        for pid in $PIDS; do
            kill -KILL "$pid" 2>/dev/null || true
        done
        
        sleep 2
    else
        echo "未找到JobManager进程"
    fi
    
    if check_running; then
        echo "警告: JobManager可能仍在运行"
        return 1
    else
        echo "JobManager已成功停止"
        return 0
    fi
}

# 启动JobManager
start_jobmanager() {
    echo "正在启动JobManager..."
    
    cd "$PROJECT_ROOT"
    
    # 后台启动JobManager
    nohup python3 -m sage.jobmanager.job_manager \
        --host "$HOST" \
        --port "$PORT" \
        > /dev/null 2>&1 &
    
    local jobmanager_pid=$!
    echo "JobManager进程ID: $jobmanager_pid"
    
    # 等待启动完成
    for i in {1..15}; do
        sleep 1
        if check_running; then
            echo "JobManager启动成功! (地址: $HOST:$PORT)"
            return 0
        fi
        echo "等待JobManager启动... ($i/15)"
    done
    
    echo "错误: JobManager启动超时"
    return 1
}

# 主逻辑
main() {
    local is_running=false
    
    if check_running; then
        is_running=true
        echo "JobManager当前状态: 运行中"
    else
        echo "JobManager当前状态: 未运行"
    fi
    
    if [ "$is_running" = true ]; then
        if [ "$FORCE" = false ]; then
            echo ""
            echo "警告: JobManager正在运行，重启将中止所有正在运行的作业!"
            read -p "是否继续? (y/N): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "操作已取消"
                exit 0
            fi
        fi
        
        if ! stop_jobmanager; then
            echo "错误: 停止JobManager失败"
            exit 1
        fi
    fi
    
    if start_jobmanager; then
        echo ""
        echo "✅ JobManager重启完成!"
        echo "可以使用以下命令检查状态:"
        echo "  python3 -c \"from sage.jobmanager.jobmanager_client import JobManagerClient; print(JobManagerClient('$HOST', $PORT).health_check())\""
    else
        echo "❌ JobManager重启失败!"
        exit 1
    fi
}

# 捕获中断信号
trap 'echo ""; echo "操作被中断"; exit 1' INT TERM

# 执行主函数
main
