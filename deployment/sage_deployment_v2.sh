#!/bin/bash

# SAGE System Deployment Script - Modular Version
# 主部署脚本 - 模块化版本
#
# 功能：
# 1. 启动/停止 SAGE 系统
# 2. 检查系统状态和健康度
# 3. 管理 CLI 工具
# 4. 系统诊断和监控

set -e  # 遇到错误立即退出

# 获取脚本目录
SCRIPT_DIR="$(dirname $(realpath $0))"

# 加载配置和模块
load_modules() {
    # 加载配置
    source "$SCRIPT_DIR/config/environment.sh"
    
    # 加载公共函数
    source "$SCRIPT_DIR/scripts/common.sh"
    
    # 加载功能模块
    source "$SCRIPT_DIR/scripts/ray_manager.sh"
    source "$SCRIPT_DIR/scripts/daemon_manager.sh"
    source "$SCRIPT_DIR/scripts/permission_manager.sh"
    source "$SCRIPT_DIR/scripts/cli_manager.sh"
    source "$SCRIPT_DIR/scripts/health_checker.sh"
    source "$SCRIPT_DIR/scripts/system_utils.sh"
    
    # 创建必要目录
    create_directories
}

# 启动系统
start_system() {
    log_info "Starting SAGE System..."
    log_info "Configuration:"
    log_info "  Ray GCS Port: $RAY_HEAD_PORT"
    log_info "  Ray Client Port: $RAY_CLIENT_PORT"
    log_info "  Ray Dashboard Port: $RAY_DASHBOARD_PORT"
    log_info "  Daemon Port: $DAEMON_PORT"
    
    # 检查系统依赖
    if ! check_system_dependencies; then
        log_error "System dependencies check failed"
        exit 1
    fi
    
    # 设置系统权限
    setup_system_directories
    
    # 1. 启动 Ray 集群
    if ! check_ray_status >/dev/null 2>&1; then
        if ! start_ray_head; then
            log_error "Failed to start Ray cluster"
            exit 1
        fi
    else
        log_success "Ray cluster is already running"
        # 仍然需要设置权限
        setup_ray_session_permissions
    fi
    
    # 2. 启动 JobManager Daemon
    if ! check_daemon_status; then
        if ! start_daemon; then
            log_error "Failed to start JobManager Daemon"
            exit 1
        fi
    else
        log_success "JobManager Daemon is already running"
    fi
    
    # 3. 设置命令行工具
    setup_cli_tools
    
    # 4. 显示状态和使用指南
    show_system_status
    show_usage_guide
}

# 停止系统
stop_system() {
    log_info "Stopping SAGE system..."
    
    # 停止守护进程
    stop_daemon
    
    # 停止Ray集群
    stop_ray_cluster
    
    # 清理临时文件
    cleanup_temp_files
    
    log_success "SAGE system stopped"
}

# 重启系统
restart_system() {
    log_info "Restarting SAGE system..."
    stop_system
    sleep 3
    start_system
}

# 显示使用指南
show_usage_guide() {
    echo
    log_info "=== SAGE System Ready ==="
    echo
    echo -e "${GREEN}🎉 SAGE system started successfully!${NC}"
    echo
    
    show_cli_usage_guide
    
    echo -e "${GREEN}🌐 Web Interfaces:${NC}"
    echo "  Ray Dashboard: http://localhost:$RAY_DASHBOARD_PORT"
    echo
    echo -e "${GREEN}📁 Important Paths:${NC}"
    echo "  Logs: $SAGE_LOG_DIR"
    echo "  Ray Temp: $RAY_TEMP_DIR"
    echo "  PID Files: $SAGE_PID_DIR"
    echo
    echo -e "${GREEN}🔄 System Management:${NC}"
    echo "  $0 status        # Check system status"
    echo "  $0 restart       # Restart system" 
    echo "  $0 stop          # Stop system"
    echo "  $0 health        # Health check"
    echo "  $0 monitor       # Real-time monitoring"
    echo
    echo -e "${BLUE}Happy coding with SAGE! 🚀${NC}"
}

# 显示帮助信息
show_help() {
    echo "SAGE System Deployment Script"
    echo "Usage: $0 {COMMAND} [OPTIONS]"
    echo
    echo "COMMANDS:"
    echo "  start           Start Ray cluster and JobManager Daemon"
    echo "  stop            Stop the entire SAGE system"
    echo "  restart         Restart the system"
    echo "  status          Show system status"
    echo "  health          Perform health check"
    echo "  monitor         Real-time system monitoring"
    echo
    echo "  install-cli     Install command line tools"
    echo "  uninstall-cli   Uninstall command line tools"
    echo "  check-cli       Check CLI tools status"
    echo
    echo "  diagnose        System diagnosis"
    echo "  collect-logs    Collect system logs"
    echo "  cleanup         Clean up temporary files"
    echo "  report          Generate system report"
    echo
    echo "  start-ray       Start Ray cluster only"
    echo "  stop-ray        Stop Ray cluster only"
    echo "  restart-ray     Restart Ray cluster only"
    echo "  fix-ray-permissions  Fix Ray session permissions for sudo users"
    echo "  start-daemon    Start JobManager Daemon only"
    echo "  stop-daemon     Stop JobManager Daemon only"
    echo "  restart-daemon  Restart JobManager Daemon only"
    echo
    echo "ENVIRONMENT VARIABLES:"
    echo "  RAY_HEAD_PORT=$RAY_HEAD_PORT         (GCS server port)"
    echo "  RAY_CLIENT_PORT=$RAY_CLIENT_PORT       (Client server port)"
    echo "  RAY_DASHBOARD_PORT=$RAY_DASHBOARD_PORT"
    echo "  DAEMON_HOST=$DAEMON_HOST"
    echo "  DAEMON_PORT=$DAEMON_PORT"
    echo "  SAGE_LOG_DIR=$SAGE_LOG_DIR"
    echo
    echo "EXAMPLES:"
    echo "  $0 start                    # Start the entire system"
    echo "  $0 status                   # Check system status"
    echo "  $0 health                   # Run health checks"
    echo "  $0 monitor 5                # Monitor with 5s refresh"
    echo "  $0 collect-logs /tmp/logs   # Collect logs to specific file"
    echo
}

# 主函数
main() {
    # 加载所有模块
    load_modules
    
    case "${1:-start}" in
        # 系统管理
        start)
            start_system
            ;;
        stop)
            stop_system
            ;;
        restart)
            restart_system
            ;;
        status)
            show_system_status
            ;;
        health)
            perform_health_check
            ;;
        monitor)
            monitor_system_status "${2:-5}"
            ;;
            
        # CLI工具管理
        install-cli)
            setup_cli_tools
            ;;
        uninstall-cli)
            uninstall_cli_tools
            ;;
        check-cli)
            check_cli_tools
            get_cli_info
            ;;
            
        # 单独组件管理
        start-ray)
            if ! check_ray_status >/dev/null 2>&1; then
                start_ray_head
            else
                log_info "Ray cluster is already running"
                show_ray_status
            fi
            ;;
        stop-ray)
            stop_ray_cluster
            ;;
        restart-ray)
            restart_ray_cluster
            ;;
        fix-ray-permissions)
            fix_ray_permissions_standalone
            ;;
        start-daemon)
            if ! check_daemon_status; then
                start_daemon
            else
                log_info "JobManager Daemon is already running"
                get_daemon_info
            fi
            ;;
        stop-daemon)
            stop_daemon
            ;;
        restart-daemon)
            restart_daemon
            ;;
            
        # 系统诊断和维护
        diagnose)
            diagnose_system
            ;;
        collect-logs)
            collect_logs "${2:-/tmp/sage_system_logs_$(date +%Y%m%d_%H%M%S).tar.gz}"
            ;;
        cleanup)
            cleanup_system
            ;;
        report)
            generate_system_report "${2:-/tmp/sage_system_report_$(date +%Y%m%d_%H%M%S).txt}"
            ;;
        performance)
            run_performance_test
            ;;
            
        # 帮助和信息
        help|--help|-h)
            show_help
            ;;
        version|--version|-v)
            echo "SAGE Deployment Script v2.0.0"
            echo "Modular version with enhanced functionality"
            ;;
            
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' to see available commands"
            exit 1
            ;;
    esac
}

# 捕获信号
trap 'log_info "Interrupted, stopping system..."; stop_system; exit 1' INT TERM

# 执行主函数
main "$@"
