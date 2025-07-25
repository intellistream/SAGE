#!/bin/bash

# CLI Tools Management Module
# 命令行工具管理模块

# 设置命令行工具
setup_cli_tools() {
    log_info "Setting up SAGE command line tools..."
    
    local script_dir=$(get_script_dir)
    local wrapper_script="$script_dir/sage_jm_wrapper.sh"
    local controller_script="$(dirname "$script_dir")/app/jobmanager_controller.py"
    local symlink_path="$CLI_SYMLINK_PATH"
    
    # 检查是否已经进行了系统级安装
    if [ -f "/usr/local/lib/sage/sage_jm_wrapper.sh" ] && [ -L "/usr/local/bin/sage-jm" ]; then
        local current_target=$(readlink "/usr/local/bin/sage-jm")
        if [ "$current_target" = "/usr/local/lib/sage/sage_jm_wrapper.sh" ]; then
            log_success "System-level CLI installation detected"
            log_info "sage-jm command is managed by system installation"
            return 0
        fi
    fi
    
    # 检查 wrapper 脚本是否存在
    if [ ! -f "$wrapper_script" ]; then
        log_error "JobManager wrapper script not found at $wrapper_script"
        log_info "Consider running system installation: sudo ./deployment/install_system.sh"
        return 1
    fi
    
    # 检查 controller 脚本是否存在
    if [ ! -f "$controller_script" ]; then
        log_error "JobManager controller script not found at $controller_script"
        return 1
    fi
    
    # 使脚本可执行
    if chmod +x "$wrapper_script" "$controller_script" 2>/dev/null; then
        log_success "CLI scripts made executable"
    else
        log_warning "Failed to make CLI scripts executable (permission denied)"
        log_info "You may need to run: chmod +x $wrapper_script $controller_script"
    fi
    
    # 检查是否已存在符号链接
    if [ -L "$symlink_path" ]; then
        local current_target=$(readlink "$symlink_path")
        if [ "$current_target" = "$wrapper_script" ]; then
            log_success "Command line tool 'sage-jm' is already set up"
            return 0
        else
            log_info "Updating existing sage-jm symlink to use wrapper script"
            sudo rm -f "$symlink_path"
        fi
    elif [ -f "$symlink_path" ]; then
        log_warning "File exists at $symlink_path (not a symlink)"
        log_info "Please remove it manually to install sage-jm command"
        return 1
    fi
    
    # 创建符号链接，指向wrapper脚本而不是直接指向controller
    if sudo ln -s "$wrapper_script" "$symlink_path" 2>/dev/null; then
        log_success "Command line tool 'sage-jm' installed successfully (using wrapper script)"
        
        # 验证安装
        if command -v sage-jm >/dev/null 2>&1; then
            log_success "sage-jm command is ready to use"
            return 0
        else
            log_warning "sage-jm command not found in PATH"
            log_info "You may need to restart your terminal or add /usr/local/bin to PATH"
            return 1
        fi
    else
        log_warning "Failed to create sage-jm symlink (sudo required)"
        log_info "To manually install the command line tool, run:"
        log_info "  sudo ln -s $wrapper_script $symlink_path"
        return 1
    fi
}

# 检查CLI工具状态
check_cli_tools() {
    local symlink_path="$CLI_SYMLINK_PATH"
    
    if command -v sage-jm >/dev/null 2>&1; then
        log_success "sage-jm command is available"
        
        # 检查符号链接是否正确
        if [ -L "$symlink_path" ]; then
            local target=$(readlink "$symlink_path")
            log_info "sage-jm points to: $target"
            
            if [ -f "$target" ]; then
                log_success "CLI tool target file exists"
                return 0
            else
                log_error "CLI tool target file not found: $target"
                return 1
            fi
        else
            log_warning "sage-jm exists but not as expected symlink"
            return 1
        fi
    else
        log_info "sage-jm command is not available"
        return 1
    fi
}

# 卸载CLI工具
uninstall_cli_tools() {
    log_info "Uninstalling SAGE command line tools..."
    
    local symlink_path="$CLI_SYMLINK_PATH"
    
    if [ -L "$symlink_path" ]; then
        if sudo rm -f "$symlink_path"; then
            log_success "sage-jm command removed successfully"
            return 0
        else
            log_error "Failed to remove sage-jm command (permission denied)"
            return 1
        fi
    elif [ -f "$symlink_path" ]; then
        log_warning "sage-jm exists but is not a symlink"
        log_info "Please manually remove: $symlink_path"
        return 1
    else
        log_info "sage-jm command is not installed"
        return 0
    fi
}

# 重新安装CLI工具
reinstall_cli_tools() {
    log_info "Reinstalling SAGE command line tools..."
    
    uninstall_cli_tools
    sleep 1
    setup_cli_tools
}

# 验证CLI工具功能
verify_cli_tools() {
    log_info "Verifying CLI tools functionality..."
    
    if ! command -v sage-jm >/dev/null 2>&1; then
        log_error "sage-jm command not found"
        return 1
    fi
    
    # 测试help命令
    if sage-jm --help >/dev/null 2>&1; then
        log_success "sage-jm help command works"
    else
        log_error "sage-jm help command failed"
        return 1
    fi
    
    # 测试health命令（如果daemon正在运行）
    if check_port $DAEMON_PORT; then
        if sage-jm health >/dev/null 2>&1; then
            log_success "sage-jm health command works"
        else
            log_warning "sage-jm health command failed (daemon may not be responding)"
        fi
    else
        log_info "Skipping health test (daemon not running)"
    fi
    
    log_success "CLI tools verification completed"
    return 0
}

# 显示CLI工具使用指南
show_cli_usage_guide() {
    echo
    log_info "=== SAGE Command Line Tools Usage Guide ==="
    echo
    
    if command -v sage-jm >/dev/null 2>&1; then
        echo -e "${GREEN}📋 Job Management Commands:${NC}"
        echo "  sage-jm list                    # List all jobs"
        echo "  sage-jm show <job_uuid>         # Show job details"
        echo "  sage-jm stop <job_uuid>         # Stop a job"
        echo "  sage-jm health                  # Check system health"
        echo "  sage-jm monitor                 # Real-time monitoring"
        echo "  sage-jm shell                   # Interactive shell"
        echo
        echo -e "${GREEN}🔍 Monitoring:${NC}"
        echo "  sage-jm monitor --refresh 3     # Monitor with 3s refresh"
        echo "  sage-jm watch <job_uuid>        # Watch specific job"
        echo
        echo -e "${GREEN}ℹ️  Getting Help:${NC}"
        echo "  sage-jm --help                  # Show all commands"
        echo "  sage-jm <command> --help        # Command-specific help"
        echo
    else
        echo -e "${YELLOW}⚠️  CLI Tools Setup Required:${NC}"
        echo "  The 'sage-jm' command is not available in your PATH."
        echo "  To set it up, run:"
        echo "    $0 install-cli"
        echo "  Or manually:"
        echo "    sudo ln -s $(dirname "$(get_script_dir)")/app/jobmanager_controller.py $CLI_SYMLINK_PATH"
        echo
    fi
    
    echo -e "${GREEN}🛠  CLI Management:${NC}"
    echo "  $0 install-cli       # Install/reinstall CLI tools"
    echo "  $0 check-cli         # Check CLI tools status"
    echo
}

# 获取CLI工具信息
get_cli_info() {
    echo "CLI Tools Information:"
    echo "======================"
    
    if command -v sage-jm >/dev/null 2>&1; then
        echo "Status: Installed"
        echo "Command: sage-jm"
        echo "Location: $(which sage-jm)"
        
        if [ -L "$CLI_SYMLINK_PATH" ]; then
            echo "Target: $(readlink $CLI_SYMLINK_PATH)"
        fi
        
        # 显示版本信息（如果支持）
        local version=$(sage-jm --version 2>/dev/null || echo "N/A")
        echo "Version: $version"
    else
        echo "Status: Not Installed"
        echo "Expected location: $CLI_SYMLINK_PATH"
    fi
    
    echo "Controller script: $(dirname "$(get_script_dir)")/app/jobmanager_controller.py"
}
