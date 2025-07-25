#!/bin/bash

# Permission and Directory Management Module
# 权限和目录管理模块

# 检查用户是否在sudo组
is_sudo_user() {
    if groups | grep -q sudo; then
        return 0  # true
    else
        return 1  # false
    fi
}

# 显示权限配置信息
show_permission_info() {
    local current_user=$(whoami)
    local current_group=$(id -gn)
    
    log_info "Permission Configuration for Shared Lab Environment:"
    log_info "  Current User: $current_user"
    log_info "  Primary Group: $current_group"
    
    if is_sudo_user; then
        log_info "  User Type: Sudo user (shared permissions enabled)"
        log_info "  Permission Strategy: root:sudo with 775 permissions"
    else
        log_warning "  User Type: Regular user (individual permissions)"
        log_info "  Permission Strategy: user:user with 755 permissions"
    fi
    echo
}

# 设置系统目录权限
setup_system_directories() {
    log_info "Setting up system directories for shared lab environment..."
    
    # 显示权限配置信息
    show_permission_info
    
    # 创建必要的目录
    local directories=(
        "$RAY_TEMP_DIR"
        "$SAGE_LOG_DIR"
        "$SAGE_PID_DIR" 
        "$SAGE_TEMP_DIR"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            log_info "Creating directory: $dir"
            if mkdir -p "$dir" 2>/dev/null; then
                log_success "Created directory: $dir"
            else
                log_warning "Failed to create directory, trying with sudo: $dir"
                sudo mkdir -p "$dir"
                log_success "Created directory with sudo: $dir"
            fi
        fi
    done
    
    # 设置目录权限
    fix_ray_shared_permissions
    setup_ray_temp_dir_permissions
    setup_log_directory_permissions
    setup_pid_directory_permissions
    setup_ray_session_permissions
}

# 设置Ray临时目录权限
setup_ray_temp_dir_permissions() {
    log_info "Setting Ray temp directory permissions: $RAY_TEMP_DIR"
    
    if [ -d "$RAY_TEMP_DIR" ]; then
        # 设置临时目录权限为1777 (sticky bit + rwxrwxrwx)
        if chmod 1777 "$RAY_TEMP_DIR" 2>/dev/null; then
            log_success "Ray temp directory permissions set"
        else
            log_warning "Failed to set permissions, trying with sudo"
            sudo chmod 1777 "$RAY_TEMP_DIR"
            log_success "Ray temp directory permissions set with sudo"
        fi
    else
        log_error "Ray temp directory does not exist: $RAY_TEMP_DIR"
        return 1
    fi
}

# 设置日志目录权限（适配共享机器）
setup_log_directory_permissions() {
    log_info "Setting log directory permissions for shared lab environment: $SAGE_LOG_DIR"
    
    if [ -d "$SAGE_LOG_DIR" ]; then
        # 检查是否在sudo组
        if groups | grep -q sudo; then
            log_info "Configuring log directory for sudo group sharing"
            
            # 设置目录所有者为root，但给sudo组读写权限
            sudo chown -R root:sudo "$SAGE_LOG_DIR" 2>/dev/null || true
            
            # 设置权限：owner=rwx, group(sudo)=rwx, other=r-x
            sudo chmod 775 "$SAGE_LOG_DIR" 2>/dev/null || true
            
            # 设置setgid位，确保新创建的文件继承sudo组
            sudo chmod g+s "$SAGE_LOG_DIR" 2>/dev/null || true
            
            # 设置子目录权限
            local subdirs=("daemon" "jobmanager")
            for subdir in "${subdirs[@]}"; do
                local full_path="$SAGE_LOG_DIR/$subdir"
                if [ ! -d "$full_path" ]; then
                    sudo mkdir -p "$full_path"
                fi
                sudo chown root:sudo "$full_path" 2>/dev/null || true
                sudo chmod 775 "$full_path" 2>/dev/null || true
                sudo chmod g+s "$full_path" 2>/dev/null || true
            done
            
            log_success "Log directory configured for sudo group sharing"
        else
            log_warning "User not in sudo group, using standard permissions"
            
            # 设置标准权限
            chmod 755 "$SAGE_LOG_DIR" 2>/dev/null || sudo chmod 755 "$SAGE_LOG_DIR"
            
            # 设置子目录权限
            local subdirs=("daemon" "jobmanager")
            for subdir in "${subdirs[@]}"; do
                local full_path="$SAGE_LOG_DIR/$subdir"
                if [ ! -d "$full_path" ]; then
                    mkdir -p "$full_path" 2>/dev/null || sudo mkdir -p "$full_path"
                fi
                chmod 755 "$full_path" 2>/dev/null || sudo chmod 755 "$full_path"
            done
            
            log_success "Log directory permissions set for single user"
        fi
    else
        log_error "Log directory does not exist: $SAGE_LOG_DIR"
        return 1
    fi
}

# 设置PID目录权限（适配共享机器）
setup_pid_directory_permissions() {
    log_info "Setting PID directory permissions for shared lab environment: $SAGE_PID_DIR"
    
    if [ -d "$SAGE_PID_DIR" ]; then
        # 检查是否在sudo组
        if groups | grep -q sudo; then
            log_info "Configuring PID directory for sudo group sharing"
            
            # 设置目录所有者为root，但给sudo组读写权限
            sudo chown -R root:sudo "$SAGE_PID_DIR" 2>/dev/null || true
            
            # 设置权限：owner=rwx, group(sudo)=rwx, other=r-x
            sudo chmod 775 "$SAGE_PID_DIR" 2>/dev/null || true
            
            # 设置setgid位，确保新创建的文件继承sudo组
            sudo chmod g+s "$SAGE_PID_DIR" 2>/dev/null || true
            
            log_success "PID directory configured for sudo group sharing"
        else
            log_warning "User not in sudo group, using standard permissions"
            
            # 检查目录所有者
            local owner=$(stat -c "%U" "$SAGE_PID_DIR")
            local current_user=$(whoami)
            
            if [ "$owner" != "$current_user" ]; then
                log_warning "PID directory owned by $owner, changing to $current_user"
                sudo chown -R "$current_user:$current_user" "$SAGE_PID_DIR"
            fi
            
            # 设置标准权限
            chmod 755 "$SAGE_PID_DIR" 2>/dev/null || sudo chmod 755 "$SAGE_PID_DIR"
            chmod u+w "$SAGE_PID_DIR" 2>/dev/null || sudo chmod u+w "$SAGE_PID_DIR"
            
            log_success "PID directory permissions set for single user"
        fi
    else
        log_error "PID directory does not exist: $SAGE_PID_DIR"
        return 1
    fi
}

# 设置Ray session权限（适配共享机器）
setup_ray_session_permissions() {
    log_info "Setting Ray session permissions for shared lab environment..."
    
    # 查找最新的 Ray session
    local ray_session_dir="/tmp/ray"
    if [ -d "$ray_session_dir" ]; then
        # 检查是否在sudo组
        if groups | grep -q sudo; then
            log_info "Configuring Ray sessions for sudo group sharing"
            
            # 设置整个/tmp/ray目录权限
            sudo chown -R root:sudo "$ray_session_dir" 2>/dev/null || true
            sudo chmod -R 775 "$ray_session_dir" 2>/dev/null || true
            sudo chmod g+s "$ray_session_dir" 2>/dev/null || true
            
            # 处理session_latest符号链接
            local session_latest="$ray_session_dir/session_latest"
            if [ -L "$session_latest" ]; then
                local actual_session=$(readlink -f "$session_latest")
                if [ -d "$actual_session" ]; then
                    log_info "Setting permissions for Ray session: $actual_session"
                    sudo chown -R root:sudo "$actual_session" 2>/dev/null || true
                    sudo chmod -R 775 "$actual_session" 2>/dev/null || true
                    
                    # 特别设置 session.json 权限
                    local session_json="$actual_session/session.json"
                    if [ -f "$session_json" ]; then
                        sudo chmod 664 "$session_json"
                        log_success "Ray session configured for sudo group sharing"
                    else
                        log_warning "session.json not found at $session_json"
                    fi
                fi
            fi
        else
            log_warning "User not in sudo group, using standard permissions"
            
            # 给 session_latest 符号链接设置权限
            local session_latest="$ray_session_dir/session_latest"
            if [ -L "$session_latest" ]; then
                local actual_session=$(readlink -f "$session_latest")
                if [ -d "$actual_session" ]; then
                    log_info "Setting permissions for Ray session: $actual_session"
                    sudo chmod -R 755 "$actual_session" 2>/dev/null || true
                    
                    # 特别设置 session.json 权限
                    local session_json="$actual_session/session.json"
                    if [ -f "$session_json" ]; then
                        sudo chmod 644 "$session_json"
                        log_success "Ray session permissions updated"
                    else
                        log_warning "session.json not found at $session_json"
                    fi
                fi
            fi
        fi
    else
        log_warning "Ray session directory not found at $ray_session_dir"
    fi
}

# 验证权限设置
verify_permissions() {
    log_info "Verifying permission settings..."
    local errors=0
    
    # 检查Ray临时目录
    if [ -d "$RAY_TEMP_DIR" ]; then
        local perm=$(stat -c "%a" "$RAY_TEMP_DIR")
        if [ "$perm" = "1777" ]; then
            log_success "Ray temp directory permissions OK: $perm"
        else
            log_error "Ray temp directory permissions incorrect: expected 1777, got $perm"
            errors=$((errors + 1))
        fi
    else
        log_error "Ray temp directory not found: $RAY_TEMP_DIR"
        errors=$((errors + 1))
    fi
    
    # 检查日志目录
    if [ -d "$SAGE_LOG_DIR" ]; then
        local perm=$(stat -c "%a" "$SAGE_LOG_DIR")
        if [ "$perm" = "755" ]; then
            log_success "Log directory permissions OK: $perm"
        else
            log_warning "Log directory permissions: expected 755, got $perm"
        fi
    else
        log_error "Log directory not found: $SAGE_LOG_DIR"
        errors=$((errors + 1))
    fi
    
    # 检查PID目录
    if [ -d "$SAGE_PID_DIR" ]; then
        local perm=$(stat -c "%a" "$SAGE_PID_DIR")
        if [ "$perm" = "755" ]; then
            log_success "PID directory permissions OK: $perm"
        else
            log_warning "PID directory permissions: expected 755, got $perm"
        fi
    else
        log_error "PID directory not found: $SAGE_PID_DIR"
        errors=$((errors + 1))
    fi
    
    if [ $errors -eq 0 ]; then
        log_success "All permission checks passed"
        return 0
    else
        log_error "Permission verification failed with $errors errors"
        return 1
    fi
}

# 修复Ray shared目录权限（适配共享机器）
fix_ray_shared_permissions() {
    log_info "Fixing Ray shared directory permissions for shared lab environment..."
    
    local ray_shared_dir="/var/lib/ray_shared"
    
    if [ -d "$ray_shared_dir" ]; then
        # 检查是否在sudo组
        if groups | grep -q sudo; then
            log_info "User is in sudo group, setting up shared permissions"
            
            # 设置目录所有者为root，但给sudo组读写权限
            sudo chown -R root:sudo "$ray_shared_dir" 2>/dev/null || true
            
            # 设置权限：owner=rwx, group(sudo)=rwx, other=r-x
            sudo chmod -R 775 "$ray_shared_dir" 2>/dev/null || true
            
            # 设置setgid位，确保新创建的文件继承sudo组
            sudo chmod g+s "$ray_shared_dir" 2>/dev/null || true
            
            # 处理锁文件 - 给sudo组写权限
            find "$ray_shared_dir" -name "*.lock" -exec sudo chmod 664 {} \; 2>/dev/null || true
            
            log_success "Ray shared directory configured for sudo group sharing"
        else
            log_warning "User not in sudo group, using standard permissions"
            # 获取当前用户
            local current_user=$(whoami)
            local current_group=$(id -gn)
            
            # 设置用户所有权
            sudo chown -R "$current_user:$current_group" "$ray_shared_dir" 2>/dev/null || {
                log_warning "Cannot change ownership, setting broader permissions"
                sudo chmod -R 755 "$ray_shared_dir" 2>/dev/null || true
            }
            
            # 确保用户有读写权限
            sudo chmod -R u+rw "$ray_shared_dir" 2>/dev/null || true
            
            log_success "Ray shared directory permissions set for single user"
        fi
    else
        log_warning "Ray shared directory not found: $ray_shared_dir"
    fi
}

# 清理临时文件和目录
cleanup_temp_files() {
    log_info "Cleaning up temporary files..."
    
    # 清理PID文件
    if [ -d "$SAGE_PID_DIR" ]; then
        rm -f "$SAGE_PID_DIR"/*.pid
        log_success "PID files cleaned"
    fi
    
    # # 清理临时文件
    # if [ -d "$SAGE_TEMP_DIR" ]; then
    #     rm -rf "$SAGE_TEMP_DIR"/*
    #     log_success "Temp files cleaned"
    # fi
    
    # # 清理旧的日志文件（保留最近的几个）
    # if [ -d "$SAGE_LOG_DIR" ]; then
    #     find "$SAGE_LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    #     log_success "Old log files cleaned"
    # fi
}

# 修复权限问题
fix_permissions() {
    log_info "Attempting to fix permission issues..."
    
    # 重新设置所有权限
    setup_system_directories
    
    # 验证修复结果
    verify_permissions
}
