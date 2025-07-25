#!/bin/bash
# SAGE System Uninstallation Script
# 系统级卸载脚本

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

# 系统路径定义
SAGE_LIB_DIR="/usr/local/lib/sage"
SAGE_BIN_DIR="/usr/local/bin"
SAGE_SHARE_DIR="/usr/local/share/sage"
SAGE_GROUP="sage"

# 删除符号链接
remove_cli_symlink() {
    log_info "Removing CLI command..."
    
    local symlink_path="$SAGE_BIN_DIR/sage-jm"
    
    if [ -L "$symlink_path" ]; then
        rm -f "$symlink_path"
        log_success "Removed sage-jm command"
    elif [ -f "$symlink_path" ]; then
        log_warning "sage-jm exists but is not a symlink, not removing"
    else
        log_info "sage-jm command not found"
    fi
}

# 删除系统文件
remove_system_files() {
    log_info "Removing system files..."
    
    # 删除lib目录
    if [ -d "$SAGE_LIB_DIR" ]; then
        rm -rf "$SAGE_LIB_DIR"
        log_success "Removed $SAGE_LIB_DIR"
    fi
    
    # 删除share目录
    if [ -d "$SAGE_SHARE_DIR" ]; then
        rm -rf "$SAGE_SHARE_DIR"
        log_success "Removed $SAGE_SHARE_DIR"
    fi
    
    # 可选：删除配置目录（询问用户）
    if [ -d "/etc/sage" ]; then
        read -p "Remove configuration directory /etc/sage? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "/etc/sage"
            log_success "Removed /etc/sage"
        else
            log_info "Kept /etc/sage"
        fi
    fi
    
    # 可选：删除日志目录（询问用户）
    if [ -d "/var/log/sage" ]; then
        read -p "Remove log directory /var/log/sage? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "/var/log/sage"
            log_success "Removed /var/log/sage"
        else
            log_info "Kept /var/log/sage"
        fi
    fi
    
    # 可选：删除数据目录（询问用户）
    if [ -d "/var/lib/sage" ]; then
        read -p "Remove data directory /var/lib/sage? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "/var/lib/sage"
            log_success "Removed /var/lib/sage"
        else
            log_info "Kept /var/lib/sage"
        fi
    fi
}

# 询问是否删除用户组
remove_sage_group() {
    if getent group "$SAGE_GROUP" >/dev/null 2>&1; then
        read -p "Remove sage group? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            groupdel "$SAGE_GROUP"
            log_success "Removed sage group"
        else
            log_info "Kept sage group"
        fi
    else
        log_info "sage group not found"
    fi
}

# 验证卸载
verify_uninstallation() {
    log_info "Verifying uninstallation..."
    
    local remaining_files=()
    
    # 检查是否还有残留文件
    if [ -d "$SAGE_LIB_DIR" ]; then
        remaining_files+=("$SAGE_LIB_DIR")
    fi
    
    if [ -d "$SAGE_SHARE_DIR" ]; then
        remaining_files+=("$SAGE_SHARE_DIR")
    fi
    
    if [ -L "$SAGE_BIN_DIR/sage-jm" ] || [ -f "$SAGE_BIN_DIR/sage-jm" ]; then
        remaining_files+=("$SAGE_BIN_DIR/sage-jm")
    fi
    
    if [ ${#remaining_files[@]} -eq 0 ]; then
        log_success "Uninstallation completed successfully"
    else
        log_warning "Some files were not removed:"
        for file in "${remaining_files[@]}"; do
            echo "  - $file"
        done
    fi
}

# 主函数
main() {
    log_info "Starting SAGE system uninstallation..."
    
    check_root
    remove_cli_symlink
    remove_system_files
    remove_sage_group
    verify_uninstallation
    
    log_success "SAGE system uninstallation completed!"
}

# 运行主函数
main "$@"
