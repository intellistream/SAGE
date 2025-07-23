#!/bin/bash
# SAGE System Installation Script
# 系统级安装脚本，用于在多用户环境下正确部署SAGE CLI工具

set -e

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
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# 获取脚本目录
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 系统路径定义
SAGE_LIB_DIR="/usr/local/lib/sage"
SAGE_BIN_DIR="/usr/local/bin"
SAGE_SHARE_DIR="/usr/local/share/sage"
SAGE_GROUP="sage"

# 创建SAGE用户组
create_sage_group() {
    log_info "Creating sage group..."
    if ! getent group "$SAGE_GROUP" >/dev/null 2>&1; then
        groupadd "$SAGE_GROUP"
        log_success "Created sage group"
    else
        log_info "sage group already exists"
    fi
}

# 创建必要的目录
create_directories() {
    log_info "Creating system directories..."
    
    mkdir -p "$SAGE_LIB_DIR"
    mkdir -p "$SAGE_SHARE_DIR"
    mkdir -p "/var/log/sage"
    mkdir -p "/var/lib/sage"
    mkdir -p "/etc/sage"
    
    log_success "Created system directories"
}

# 复制文件到系统位置
install_files() {
    log_info "Installing SAGE files..."
    
    # 复制CLI相关文件
    cp "$SCRIPT_DIR/../app/jobmanager_controller.py" "$SAGE_LIB_DIR/"
    cp "$SCRIPT_DIR/sage_jm_wrapper.sh" "$SAGE_LIB_DIR/"
    
    # 复制配置文件
    if [ -d "$SCRIPT_DIR/config" ]; then
        cp -r "$SCRIPT_DIR/config" "/etc/sage/"
    fi
    
    # 如果有模板文件也复制
    if [ -d "$SCRIPT_DIR/templates" ]; then
        cp -r "$SCRIPT_DIR/templates" "$SAGE_SHARE_DIR/"
    fi
    
    log_success "Files installed to system locations"
}

# 设置文件权限
set_permissions() {
    log_info "Setting up permissions..."
    
    # 设置目录权限
    chown -R root:"$SAGE_GROUP" "$SAGE_LIB_DIR"
    chown -R root:"$SAGE_GROUP" "/var/log/sage"
    chown -R root:"$SAGE_GROUP" "/var/lib/sage"
    chown -R root:"$SAGE_GROUP" "/etc/sage"
    
    # 设置文件权限
    chmod 755 "$SAGE_LIB_DIR"
    chmod 755 "$SAGE_LIB_DIR/sage_jm_wrapper.sh"
    chmod 644 "$SAGE_LIB_DIR/jobmanager_controller.py"
    
    # 设置日志和数据目录权限，允许sage组写入
    chmod 775 "/var/log/sage"
    chmod 775 "/var/lib/sage"
    
    log_success "Permissions set correctly"
}

# 创建命令行工具符号链接
setup_cli_symlink() {
    log_info "Setting up CLI command..."
    
    local symlink_path="$SAGE_BIN_DIR/sage-jm"
    local wrapper_script="$SAGE_LIB_DIR/sage_jm_wrapper.sh"
    
    # 删除旧的符号链接
    if [ -L "$symlink_path" ]; then
        rm -f "$symlink_path"
    elif [ -f "$symlink_path" ]; then
        log_warning "File exists at $symlink_path, backing up to ${symlink_path}.backup"
        mv "$symlink_path" "${symlink_path}.backup"
    fi
    
    # 创建新的符号链接
    ln -s "$wrapper_script" "$symlink_path"
    chmod 755 "$symlink_path"
    
    log_success "CLI command 'sage-jm' installed"
}

# 添加用户到sage组
add_users_to_sage_group() {
    log_info "Adding users to sage group..."
    
    # 获取所有非系统用户
    local users=$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd)
    
    for user in $users; do
        if id "$user" >/dev/null 2>&1; then
            usermod -a -G "$SAGE_GROUP" "$user"
            log_info "Added user $user to sage group"
        fi
    done
    
    # 添加当前sudo用户
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        usermod -a -G "$SAGE_GROUP" "$SUDO_USER"
        log_info "Added sudo user $SUDO_USER to sage group"
    fi
    
    log_success "Users added to sage group"
}

# 创建环境配置文件
create_environment_config() {
    log_info "Creating environment configuration..."
    
    cat > "/etc/sage/environment.conf" << 'EOF'
# SAGE System Configuration
# This file contains system-wide settings for SAGE

# Paths
SAGE_HOME=/opt/sage
SAGE_LOG_DIR=/var/log/sage
SAGE_DATA_DIR=/var/lib/sage
SAGE_CONFIG_DIR=/etc/sage

# Ray Configuration
RAY_TEMP_DIR=/var/lib/sage/ray

# Permissions
SAGE_GROUP=sage
EOF

    chmod 644 "/etc/sage/environment.conf"
    log_success "Environment configuration created"
}

# 验证安装
verify_installation() {
    log_info "Verifying installation..."
    
    # 检查文件是否存在
    local files=(
        "$SAGE_LIB_DIR/jobmanager_controller.py"
        "$SAGE_LIB_DIR/sage_jm_wrapper.sh"
        "$SAGE_BIN_DIR/sage-jm"
        "/etc/sage/environment.conf"
    )
    
    for file in "${files[@]}"; do
        if [ ! -e "$file" ]; then
            log_error "Missing file: $file"
            return 1
        fi
    done
    
    # 检查sage-jm命令是否可用
    if command -v sage-jm >/dev/null 2>&1; then
        log_success "sage-jm command is available"
    else
        log_warning "sage-jm command not found in PATH"
    fi
    
    # 检查用户组
    if getent group "$SAGE_GROUP" >/dev/null 2>&1; then
        log_success "sage group exists"
    else
        log_error "sage group not found"
        return 1
    fi
    
    log_success "Installation verification completed"
}

# 显示安装后说明
show_post_install_info() {
    log_info "Installation completed successfully!"
    echo
    log_info "Post-installation notes:"
    echo "1. Users need to log out and log back in for group changes to take effect"
    echo "2. The 'sage-jm' command is now available system-wide"
    echo "3. Configuration files are in /etc/sage/"
    echo "4. Log files will be stored in /var/log/sage/"
    echo "5. Data files will be stored in /var/lib/sage/"
    echo
    log_info "To verify the installation, run: sage-jm --help"
}

# 主函数
main() {
    log_info "Starting SAGE system installation..."
    
    check_root
    create_sage_group
    create_directories
    install_files
    set_permissions
    setup_cli_symlink
    add_users_to_sage_group
    create_environment_config
    verify_installation
    show_post_install_info
    
    log_success "SAGE system installation completed!"
}

# 运行主函数
main "$@"
