#!/bin/bash

# System Utilities Module
# 系统工具函数模块

# 获取系统信息
get_system_info() {
    echo "SAGE System Information"
    echo "======================"
    echo "Date: $(date)"
    echo "Hostname: $(hostname)"
    echo "OS: $(uname -s)"
    echo "Kernel: $(uname -r)"
    echo "Architecture: $(uname -m)"
    
    # CPU信息
    if [ -f /proc/cpuinfo ]; then
        local cpu_model=$(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | sed 's/^ *//')
        local cpu_cores=$(grep "processor" /proc/cpuinfo | wc -l)
        echo "CPU: $cpu_model ($cpu_cores cores)"
    fi
    
    # 内存信息
    if [ -f /proc/meminfo ]; then
        local total_mem=$(grep "MemTotal" /proc/meminfo | awk '{print $2}')
        local available_mem=$(grep "MemAvailable" /proc/meminfo | awk '{print $2}')
        echo "Memory: $((total_mem/1024))MB total, $((available_mem/1024))MB available"
    fi
    
    # 磁盘信息
    echo "Disk Usage:"
    df -h | grep -E "(^/dev|^tmpfs)" | head -5
    
    echo ""
}

# 获取网络信息
get_network_info() {
    echo "Network Information"
    echo "==================="
    
    # 网络接口
    echo "Network Interfaces:"
    ip addr show | grep -E "(^[0-9]|inet )" | head -10
    
    # 监听端口
    echo -e "\nListening Ports:"
    netstat -tlnp 2>/dev/null | grep LISTEN | head -10
    
    echo ""
}

# 获取进程信息
get_process_info() {
    echo "SAGE Related Processes"
    echo "====================="
    
    # Ray进程
    echo "Ray Processes:"
    ps aux | grep -E "(ray|python.*ray)" | grep -v grep || echo "  No Ray processes found"
    
    # JobManager进程
    echo -e "\nJobManager Processes:"
    ps aux | grep -E "(jobmanager|sage)" | grep -v grep || echo "  No JobManager processes found"
    
    # Python进程
    echo -e "\nPython Processes (last 5):"
    ps aux | grep python | grep -v grep | tail -5 || echo "  No Python processes found"
    
    echo ""
}

# 获取资源使用情况
get_resource_usage() {
    echo "Resource Usage"
    echo "=============="
    
    # CPU使用率
    echo "CPU Usage:"
    top -bn1 | grep "Cpu(s)" | head -1
    
    # 内存使用率
    echo -e "\nMemory Usage:"
    free -h
    
    # 磁盘I/O
    echo -e "\nDisk I/O:"
    iostat -x 1 1 2>/dev/null | tail -n +4 | head -5 || echo "  iostat not available"
    
    # 网络统计
    echo -e "\nNetwork Statistics:"
    cat /proc/net/dev | head -3
    
    echo ""
}

# 收集日志信息
collect_logs() {
    local output_file=${1:-/tmp/sage_system_logs.tar.gz}
    local temp_dir="/tmp/sage_logs_$(date +%Y%m%d_%H%M%S)"
    
    log_info "Collecting system logs to: $output_file"
    
    # 创建临时目录
    mkdir -p "$temp_dir"
    
    # 收集SAGE日志
    if [ -d "$SAGE_LOG_DIR" ]; then
        cp -r "$SAGE_LOG_DIR" "$temp_dir/sage_logs"
    fi
    
    # 收集系统信息
    get_system_info > "$temp_dir/system_info.txt"
    get_network_info > "$temp_dir/network_info.txt"  
    get_process_info > "$temp_dir/process_info.txt"
    get_resource_usage > "$temp_dir/resource_usage.txt"
    
    # 收集配置文件
    if [ -f "$(get_script_dir)/config/environment.sh" ]; then
        cp "$(get_script_dir)/config/environment.sh" "$temp_dir/"
    fi
    
    # 收集Ray日志
    if [ -d "/tmp/ray" ]; then
        find /tmp/ray -name "*.log" -type f -exec cp {} "$temp_dir/" \; 2>/dev/null || true
    fi
    
    # 压缩日志
    tar -czf "$output_file" -C "$(dirname $temp_dir)" "$(basename $temp_dir)" 2>/dev/null
    
    # 清理临时目录
    rm -rf "$temp_dir"
    
    if [ -f "$output_file" ]; then
        log_success "Logs collected successfully: $output_file"
        local size=$(du -h "$output_file" | cut -f1)
        log_info "Archive size: $size"
        return 0
    else
        log_error "Failed to collect logs"
        return 1
    fi
}

# 清理系统临时文件
cleanup_system() {
    log_info "Cleaning up system temporary files..."
    
    # 清理SAGE临时文件
    cleanup_temp_files
    
    # 清理Ray临时文件
    local ray_temp_dirs=("/tmp/ray" "$RAY_TEMP_DIR")
    for ray_dir in "${ray_temp_dirs[@]}"; do
        if [ -d "$ray_dir" ]; then
            log_info "Cleaning Ray temp directory: $ray_dir"
            find "$ray_dir" -type f -name "*.tmp" -delete 2>/dev/null || true
            find "$ray_dir" -type f -name "*.lock" -delete 2>/dev/null || true
        fi
    done
    
    # 清理Python缓存
    local project_root=$(get_project_root)
    if [ -d "$project_root" ]; then
        log_info "Cleaning Python cache files..."
        find "$project_root" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        find "$project_root" -name "*.pyc" -delete 2>/dev/null || true
    fi
    
    log_success "System cleanup completed"
}

# 系统诊断
diagnose_system() {
    log_info "=== SAGE System Diagnosis ==="
    
    # 基础健康检查
    perform_health_check
    
    # 详细系统信息
    echo -e "\n${BLUE}=== Detailed System Information ===${NC}"
    get_system_info
    get_network_info
    get_process_info
    get_resource_usage
    
    # 配置检查
    echo -e "\n${BLUE}=== Configuration Check ===${NC}"
    echo "Environment variables:"
    echo "  RAY_HEAD_PORT=$RAY_HEAD_PORT"
    echo "  RAY_CLIENT_PORT=$RAY_CLIENT_PORT"  
    echo "  RAY_DASHBOARD_PORT=$RAY_DASHBOARD_PORT"
    echo "  DAEMON_HOST=$DAEMON_HOST"
    echo "  DAEMON_PORT=$DAEMON_PORT"
    echo "  SAGE_LOG_DIR=$SAGE_LOG_DIR"
    echo "  RAY_TEMP_DIR=$RAY_TEMP_DIR"
    
    # 权限检查
    echo -e "\n${BLUE}=== Permission Check ===${NC}"
    verify_permissions
    
    # 依赖检查
    echo -e "\n${BLUE}=== Dependencies Check ===${NC}"
    check_system_dependencies
    check_python_environment
    
    log_success "System diagnosis completed"
}

# 性能基准测试
run_performance_test() {
    log_info "Running basic performance tests..."
    
    # CPU测试
    echo -e "\n${BLUE}CPU Performance Test:${NC}"
    local cpu_start=$(date +%s%N)
    python3 -c "
import time
start = time.time()
# 简单的CPU密集任务
for i in range(1000000):
    _ = i * i
end = time.time()
print(f'CPU test completed in {end - start:.3f} seconds')
"
    
    # 磁盘I/O测试
    echo -e "\n${BLUE}Disk I/O Performance Test:${NC}"
    local test_file="/tmp/sage_io_test.tmp"
    dd if=/dev/zero of="$test_file" bs=1M count=100 2>&1 | tail -1
    rm -f "$test_file"
    
    # 内存测试
    echo -e "\n${BLUE}Memory Performance Test:${NC}"
    python3 -c "
import time
import sys
start = time.time()
# 分配100MB内存
data = [0] * (100 * 1024 * 1024 // 8)  # 100MB worth of integers
end = time.time()
print(f'Memory allocation test completed in {end - start:.3f} seconds')
del data
"
    
    log_success "Performance tests completed"
}

# 生成系统报告
generate_system_report() {
    local report_file=${1:-/tmp/sage_system_report_$(date +%Y%m%d_%H%M%S).txt}
    
    log_info "Generating system report: $report_file"
    
    {
        echo "SAGE System Report"
        echo "=================="
        echo "Generated: $(date)"
        echo "Report by: $(whoami)@$(hostname)"
        echo ""
        
        get_system_info
        get_network_info
        get_process_info 
        get_resource_usage
        
        echo "=== System Diagnosis ==="
        diagnose_system
        
    } > "$report_file" 2>&1
    
    if [ -f "$report_file" ]; then
        log_success "System report generated: $report_file"
        local size=$(du -h "$report_file" | cut -f1)
        log_info "Report size: $size"
        return 0
    else
        log_error "Failed to generate system report"
        return 1
    fi
}
