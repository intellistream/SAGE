#!/bin/bash

# Permission and Directory Management Module
# 权限和目录管理模块

# 设置系统目录权限
setup_system_directories() {
    log_info "Setting up system directories..."
    
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
    setup_ray_temp_dir_permissions
    setup_log_directory_permissions
    setup_pid_directory_permissions
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

# 设置日志目录权限
setup_log_directory_permissions() {
    log_info "Setting log directory permissions: $SAGE_LOG_DIR"
    
    if [ -d "$SAGE_LOG_DIR" ]; then
        # 设置日志目录权限为755
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
        
        log_success "Log directory permissions set"
    else
        log_error "Log directory does not exist: $SAGE_LOG_DIR"
        return 1
    fi
}

# 设置PID目录权限
setup_pid_directory_permissions() {
    log_info "Setting PID directory permissions: $SAGE_PID_DIR"
    
    if [ -d "$SAGE_PID_DIR" ]; then
        # 设置PID目录权限为755
        chmod 755 "$SAGE_PID_DIR" 2>/dev/null || sudo chmod 755 "$SAGE_PID_DIR"
        log_success "PID directory permissions set"
    else
        log_error "PID directory does not exist: $SAGE_PID_DIR"
        return 1
    fi
}

# 设置Ray session权限（从ray_manager.sh移过来）
setup_ray_session_permissions() {
    log_info "Setting Ray session permissions..."
    
    # 查找最新的 Ray session
    local ray_session_dir="/tmp/ray"
    if [ -d "$ray_session_dir" ]; then
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
