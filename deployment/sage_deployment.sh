#!/bin/bash

# SAGE System Deployment Script - Simplified Version
# 简化版主部署脚本
#
# 缺省参数时自动执行完整部署（系统级安装 + 启动系统）

set -e  # 遇到错误立即退出

# 获取脚本目录
SCRIPT_DIR="$(dirname $(realpath $0))"

# 自动检测python和ray路径
PYTHON_BIN=$(which python)
RAY_BIN=$(which ray)

# 颜色定义
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

# 检查是否以root权限运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        return 1
    fi
    return 0
}

# 检查sudo权限
check_sudo() {
    if sudo -n true 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 加载配置和模块
load_modules() {
    # 加载配置
    if [ -f "$SCRIPT_DIR/config/environment.sh" ]; then
        source "$SCRIPT_DIR/config/environment.sh"
    fi
    
    # 加载公共函数
    if [ -f "$SCRIPT_DIR/scripts/common.sh" ]; then
        source "$SCRIPT_DIR/scripts/common.sh"
    fi
    
    # 加载功能模块
    for module in ray_manager daemon_manager permission_manager cli_manager health_checker system_utils; do
        if [ -f "$SCRIPT_DIR/scripts/$module.sh" ]; then
            source "$SCRIPT_DIR/scripts/$module.sh"
        fi
    done
    
    # 创建必要目录
    if command -v create_directories >/dev/null 2>&1; then
        create_directories
    fi
}

# 系统级安装功能（整合自install_system.sh）
perform_system_installation() {
    log_info "=== Performing System-Level Installation ==="
    
    local PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    local SAGE_LIB_DIR="/usr/local/lib/sage"
    local SAGE_BIN_DIR="/usr/local/bin"
    local SAGE_GROUP="sage"
    
    # 创建SAGE用户组
    log_info "Creating sage group..."
    if ! getent group "$SAGE_GROUP" >/dev/null 2>&1; then
        groupadd "$SAGE_GROUP"
        log_success "Created sage group"
    else
        log_info "sage group already exists"
    fi
    
    # 创建必要的目录
    log_info "Creating system directories..."
    mkdir -p "$SAGE_LIB_DIR"
    mkdir -p "/var/log/sage"
    mkdir -p "/var/lib/sage"
    mkdir -p "/etc/sage"
    log_success "Created system directories"
    
    # 复制文件到系统位置
    log_info "Installing SAGE files..."
    cp "$SCRIPT_DIR/app/jobmanager_controller.py" "$SAGE_LIB_DIR/"
    cp "$SCRIPT_DIR/scripts/sage_jm_wrapper.sh" "$SAGE_LIB_DIR/"
    
    if [ -d "$SCRIPT_DIR/config" ]; then
        cp -r "$SCRIPT_DIR/config" "/etc/sage/"
    fi
    log_success "Files installed to system locations"
    
    # 设置文件权限
    log_info "Setting up permissions..."
    chown -R root:"$SAGE_GROUP" "$SAGE_LIB_DIR"
    chown -R root:"$SAGE_GROUP" "/var/log/sage"
    chown -R root:"$SAGE_GROUP" "/var/lib/sage"
    chown -R root:"$SAGE_GROUP" "/etc/sage"
    
    chmod 755 "$SAGE_LIB_DIR"
    chmod 755 "$SAGE_LIB_DIR/sage_jm_wrapper.sh"
    chmod 644 "$SAGE_LIB_DIR/jobmanager_controller.py"
    chmod 775 "/var/log/sage"
    chmod 775 "/var/lib/sage"
    log_success "Permissions set correctly"
    
    # 创建命令行工具符号链接
    log_info "Setting up CLI command..."
    local symlink_path="$SAGE_BIN_DIR/sage-jm"
    local wrapper_script="$SAGE_LIB_DIR/sage_jm_wrapper.sh"
    
    if [ -L "$symlink_path" ]; then
        rm -f "$symlink_path"
    elif [ -f "$symlink_path" ]; then
        log_warning "File exists at $symlink_path, backing up to ${symlink_path}.backup"
        mv "$symlink_path" "${symlink_path}.backup"
    fi
    
    ln -s "$wrapper_script" "$symlink_path"
    chmod 755 "$symlink_path"
    log_success "CLI command 'sage-jm' installed"
    
    # 添加用户到sage组
    log_info "Adding users to sage group..."
    local users=$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd)
    
    for user in $users; do
        if id "$user" >/dev/null 2>&1; then
            usermod -a -G "$SAGE_GROUP" "$user"
            log_info "Added user $user to sage group"
        fi
    done
    
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        usermod -a -G "$SAGE_GROUP" "$SUDO_USER"
        log_info "Added sudo user $SUDO_USER to sage group"
    fi
    log_success "Users added to sage group"
    
    # 创建环境配置文件
    log_info "Creating environment configuration..."
    cat > "/etc/sage/environment.conf" << 'EOF'
# SAGE System Configuration
SAGE_HOME=/opt/sage
SAGE_LOG_DIR=/var/log/sage
SAGE_DATA_DIR=/var/lib/sage
SAGE_CONFIG_DIR=/etc/sage
RAY_TEMP_DIR=/var/lib/sage/ray
SAGE_GROUP=sage
EOF
    chmod 644 "/etc/sage/environment.conf"
    log_success "Environment configuration created"
    
    log_success "=== System-Level Installation Completed ==="
}

# 设置权限功能
setup_permissions() {
    log_info "=== Setting up permissions ==="
    
    # 如果有permission_manager模块，使用它
    if command -v setup_system_directories >/dev/null 2>&1; then
        setup_system_directories
    else
        # 简单权限设置
        log_info "Setting basic permissions..."
        
        # 创建基本目录
        mkdir -p ~/sage_logs
        mkdir -p /tmp/sage
        
        # 如果是系统级安装，设置系统目录权限
        if [ -d "/var/log/sage" ]; then
            chmod 775 "/var/log/sage" 2>/dev/null || true
            chmod 775 "/var/lib/sage" 2>/dev/null || true
        fi
        
        log_success "Basic permissions set"
    fi
}

# 设置CLI工具
setup_cli_tools() {
    log_info "=== Setting up CLI tools ==="
    
    # 检查是否已经有系统级安装的CLI工具
    if [ -f "/usr/local/lib/sage/sage_jm_wrapper.sh" ] && [ -L "/usr/local/bin/sage-jm" ]; then
        local current_target=$(readlink "/usr/local/bin/sage-jm")
        if [ "$current_target" = "/usr/local/lib/sage/sage_jm_wrapper.sh" ]; then
            log_success "System-level CLI installation detected"
            return 0
        fi
    fi
    
    # 如果有cli_manager模块，使用它
    if command -v setup_cli_tools >/dev/null 2>&1; then
        setup_cli_tools
    else
        # 简单CLI设置
        log_info "Setting up development CLI tools..."
        
        if [ ! -f "$SCRIPT_DIR/scripts/sage_jm_wrapper.sh" ]; then
            log_error "sage_jm_wrapper.sh not found"
            return 1
        fi
        
        chmod +x "$SCRIPT_DIR/scripts/sage_jm_wrapper.sh"
        chmod +x "$SCRIPT_DIR/app/jobmanager_controller.py"
        
        # 尝试创建本地符号链接
        if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
            local symlink_path="/usr/local/bin/sage-jm"
            if [ -L "$symlink_path" ]; then
                sudo rm -f "$symlink_path"
            fi
            sudo ln -s "$SCRIPT_DIR/scripts/sage_jm_wrapper.sh" "$symlink_path"
            log_success "CLI command installed"
        else
            log_warning "Cannot create system-wide CLI command (no sudo)"
            log_info "You can use: $SCRIPT_DIR/scripts/sage_jm_wrapper.sh"
        fi
    fi
}

# 启动Ray集群
start_ray() {
    log_info "Starting Ray cluster..."
    
    if command -v start_ray_head >/dev/null 2>&1; then
        start_ray_head
    else
        # 简单Ray启动
        local ray_head_port=${RAY_HEAD_PORT:-10001}
        local ray_dashboard_port=${RAY_DASHBOARD_PORT:-8265}
        local ray_temp_dir=${RAY_TEMP_DIR:-/var/lib/ray_shared}
        
        mkdir -p "$ray_temp_dir" 2>/dev/null || mkdir -p "/tmp/ray_shared"
        
        # 检查Ray是否已经在运行 - 使用更准确的方法
        local ray_running=false
        if command -v ${RAY_BIN} >/dev/null 2>&1; then
            if ${RAY_BIN} status >/dev/null 2>&1; then
                ray_running=true
            fi
        else
            # Fallback: 检查Ray进程
            if pgrep -f "ray/gcs/gcs_server\|ray/raylet/raylet" >/dev/null; then
                ray_running=true
            fi
        fi
        
        if ! $ray_running; then
            ${RAY_BIN} start --head --port="$ray_head_port" --dashboard-port="$ray_dashboard_port" \
                --temp-dir="$ray_temp_dir" --resources='{"jobmanager": 1.0}' 2>/dev/null || \
            ${RAY_BIN} start --head --port="$ray_head_port" --dashboard-port="$ray_dashboard_port" \
                --temp-dir="/tmp/ray_shared" --resources='{"jobmanager": 1.0}'
            log_success "Ray cluster started"
        else
            log_success "Ray cluster already running"
        fi
    fi
}

# 启动Daemon
start_daemon() {
    log_info "Starting JobManager Daemon..."
    
    if command -v start_daemon >/dev/null 2>&1; then
        start_daemon
    else
        # 简单Daemon启动
        local daemon_script="$SCRIPT_DIR/app/jobmanager_daemon.py"
        
        if [ ! -f "$daemon_script" ]; then
            log_error "jobmanager_daemon.py not found"
            return 1
        fi
        
        if ! pgrep -f "jobmanager_daemon.py" >/dev/null; then
            nohup ${PYTHON_BIN} "$daemon_script" >/dev/null 2>&1 &
            sleep 2
            if pgrep -f "jobmanager_daemon.py" >/dev/null; then
                log_success "JobManager Daemon started"
            else
                log_error "Failed to start JobManager Daemon"
                return 1
            fi
        else
            log_success "JobManager Daemon already running"
        fi
    fi
}

# 启动系统
start_system() {
    log_info "=== Starting SAGE System ==="
    
    # 设置基本环境变量
    export RAY_HEAD_PORT=${RAY_HEAD_PORT:-10001}
    export RAY_CLIENT_PORT=${RAY_CLIENT_PORT:-10002}
    export RAY_DASHBOARD_PORT=${RAY_DASHBOARD_PORT:-8265}
    export DAEMON_HOST=${DAEMON_HOST:-127.0.0.1}
    export DAEMON_PORT=${DAEMON_PORT:-19001}
    
    log_info "Configuration:"
    log_info "  Ray GCS Port: $RAY_HEAD_PORT"
    log_info "  Ray Dashboard Port: $RAY_DASHBOARD_PORT"
    log_info "  Daemon Port: $DAEMON_PORT"
    
    # 1. 启动 Ray 集群
    start_ray
    
    # 2. 启动 JobManager Daemon
    start_daemon
    
    # 3. 验证CLI工具
    log_info "Verifying CLI tools..."
    if command -v sage-jm >/dev/null 2>&1; then
        if timeout 10 sage-jm health >/dev/null 2>&1; then
            log_success "CLI tools working correctly"
        else
            log_warning "CLI tools installed but cannot connect to daemon"
        fi
    else
        log_warning "CLI tools not found"
    fi
    
    # 4. 显示状态
    show_system_status
}

# 停止系统
stop_system() {
    log_info "=== Stopping SAGE system ==="
    
    # 停止守护进程
    if pgrep -f "jobmanager_daemon.py" >/dev/null; then
        pkill -f "jobmanager_daemon.py"
        log_success "JobManager Daemon stopped"
    fi
    
    # 停止Ray集群 - 使用更准确的方法
    if command -v ${RAY_BIN} >/dev/null 2>&1; then
        if ${RAY_BIN} status >/dev/null 2>&1; then
            ${RAY_BIN} stop
            log_success "Ray cluster stopped"
        fi
    else
        # Fallback: 检查并终止Ray进程
        if pgrep -f "ray/gcs/gcs_server\|ray/raylet/raylet" >/dev/null; then
            pkill -f "ray"
            log_success "Ray cluster stopped"
        fi
    fi
    
    log_success "SAGE system stopped"
}

# 显示系统状态
show_system_status() {
    log_info "=== System Status ==="
    
    # Ray状态 - 使用更准确的检测方法
    if command -v ${RAY_BIN} >/dev/null 2>&1; then
        if ${RAY_BIN} status >/dev/null 2>&1; then
            log_success "Ray cluster: Running"
            # 显示Ray资源信息
            local ray_info=$(${RAY_BIN} status 2>/dev/null | grep -E "CPU|GPU|memory" | head -3)
            if [ -n "$ray_info" ]; then
                echo "  $ray_info" | sed 's/^/  /'
            fi
        else
            log_warning "Ray cluster: Stopped"
        fi
    else
        # Fallback: 检查Ray进程
        if pgrep -f "ray/gcs/gcs_server\|ray/raylet/raylet" >/dev/null; then
            log_success "Ray cluster: Running"
        else
            log_warning "Ray cluster: Stopped"
        fi
    fi
    
    # Daemon状态
    if pgrep -f "jobmanager_daemon.py" >/dev/null; then
        log_success "JobManager Daemon: Running"
        local daemon_pid=$(pgrep -f "jobmanager_daemon.py")
        echo "  PID: $daemon_pid"
    else
        log_warning "JobManager Daemon: Stopped"
    fi
    
    # CLI工具状态
    if command -v sage-jm >/dev/null 2>&1; then
        log_success "CLI tools: Available (sage-jm)"
        local symlink_target=$(readlink $(which sage-jm) 2>/dev/null)
        if [ -n "$symlink_target" ]; then
            echo "  Path: $symlink_target"
        fi
        
        # 测试CLI连接
        if timeout 5 sage-jm health >/dev/null 2>&1; then
            echo "  Status: Connected to daemon"
        else
            echo "  Status: Cannot connect to daemon"
        fi
    else
        log_warning "CLI tools: Not found"
    fi
    
    # 端口使用情况
    log_info "Port usage:"
    local ray_port=${RAY_HEAD_PORT:-10001}
    local dashboard_port=${RAY_DASHBOARD_PORT:-8265}
    local daemon_port=${DAEMON_PORT:-19001}
    
    if netstat -tln 2>/dev/null | grep -q ":$ray_port "; then
        echo "  Ray GCS port $ray_port: In use ✓"
    else
        echo "  Ray GCS port $ray_port: Available"
    fi
    
    if netstat -tln 2>/dev/null | grep -q ":$dashboard_port "; then
        echo "  Ray Dashboard port $dashboard_port: In use ✓"
    else
        echo "  Ray Dashboard port $dashboard_port: Available"
    fi
    
    if netstat -tln 2>/dev/null | grep -q ":$daemon_port "; then
        echo "  Daemon port $daemon_port: In use ✓"
    else
        echo "  Daemon port $daemon_port: Available"
    fi
}

# 显示使用指南
show_usage_guide() {
    echo
    log_info "=== SAGE System Ready ==="
    echo
    echo -e "${GREEN}🎉 SAGE system started successfully!${NC}"
    echo
    echo -e "${GREEN}💻 CLI Commands:${NC}"
    echo "  sage-jm status              # Check JobManager status"
    echo "  sage-jm submit <job>        # Submit a job"
    echo "  sage-jm list                # List all jobs"
    echo "  sage-jm health              # Health check"
    echo
    echo -e "${GREEN}🌐 Web Interfaces:${NC}"
    echo "  Ray Dashboard: http://localhost:${RAY_DASHBOARD_PORT:-8265}"
    echo
    echo -e "${GREEN}🔄 System Management:${NC}"
    echo "  $0 status                   # Check system status"
    echo "  $0 stop                     # Stop system"
    echo "  $0 restart                  # Restart system"
    echo
    echo -e "${BLUE}Happy coding with SAGE! 🚀${NC}"
}

# 完整部署功能（缺省行为）
full_deployment() {
    log_info "=== Starting SAGE Full Deployment ==="
    
    # 1. 检查权限并执行系统级安装
    if check_root; then
        log_info "Running with root privileges, performing system-level installation..."
        perform_system_installation
    elif check_sudo; then
        log_info "Sudo available, performing system-level installation..."
        log_warning "System-level installation requires sudo privileges"
        read -p "Proceed with system-level installation? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            log_info "Executing system installation with sudo..."
            sudo -E bash "$0" system-install
            if [ $? -ne 0 ]; then
                log_error "System installation failed"
                exit 1
            fi
        else
            log_info "Skipping system-level installation"
        fi
    else
        log_warning "No sudo access available, skipping system-level installation"
        log_info "Running in development mode..."
    fi
    
    # 2. 加载模块和配置
    load_modules
    
    # 3. 检查和设置权限
    setup_permissions
    
    # 4. 设置CLI工具
    setup_cli_tools
    
    # 5. 启动系统
    start_system
    
    log_success "=== SAGE Full Deployment Completed ==="
    echo
    log_info "Post-deployment notes:"
    echo "1. If system-level installation was performed, users may need to log out and back in"
    echo "2. Use 'sage-jm --help' to see available commands"
    echo "3. Use '$0 stop' to stop the system"
}

# 仅执行系统级安装（内部使用）
system_install_only() {
    if ! check_root; then
        log_error "System installation must be run as root"
        exit 1
    fi
    perform_system_installation
}

# 显示帮助信息
show_help() {
    echo "SAGE System Deployment Script - Simplified Version"
    echo "Usage: $0 [COMMAND]"
    echo
    echo "COMMANDS:"
    echo "  (no command)    Full deployment (system install + start system)"
    echo "  start           Start SAGE system (Ray + Daemon)"
    echo "  stop            Stop SAGE system"
    echo "  restart         Restart SAGE system"
    echo "  status          Show system status"
    echo "  install-system  Perform system-level installation only"
    echo "  help            Show this help message"
    echo
    echo "EXAMPLES:"
    echo "  $0              # Full deployment"
    echo "  $0 start        # Start system only"
    echo "  $0 status       # Check status"
    echo
}

# 主函数
main() {
    case "${1:-}" in
        # 缺省行为：完整部署
        "")
            full_deployment
            ;;
        # 系统管理
        start)
            load_modules
            setup_permissions
            start_system
            ;;
        stop)
            stop_system
            ;;
        restart)
            stop_system
            sleep 3
            load_modules
            setup_permissions
            start_system
            ;;
        status)
            show_system_status
            ;;
            
        # 系统级安装
        install-system)
            if check_root; then
                perform_system_installation
            else
                log_error "System installation requires root privileges"
                log_info "Please run: sudo $0 install-system"
                exit 1
            fi
            ;;
        system-install)
            # 内部使用，由sudo调用
            system_install_only
            ;;
            
        # 帮助
        help|--help|-h)
            show_help
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
