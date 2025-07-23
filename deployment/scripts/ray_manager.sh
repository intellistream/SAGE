#!/bin/bash

# Ray Cluster Management Module
# Ray集群管理模块

# 检查 Ray 状态
check_ray_status() {
    if ray status >/dev/null 2>&1; then
        log_success "Ray cluster is running"
        return 0
    else
        log_info "Ray cluster is not running"
        return 1
    fi
}

# 显示 Ray 详细状态
show_ray_status() {
    if check_ray_status; then
        ray status
        return 0
    else
        return 1
    fi
}

# 设置 Ray temp 目录权限
setup_ray_temp_dir() {
    log_info "Setting up Ray temp directory: $RAY_TEMP_DIR"
    
    if [ ! -d "$RAY_TEMP_DIR" ]; then
        sudo mkdir -p "$RAY_TEMP_DIR"
        log_info "Created Ray temp directory: $RAY_TEMP_DIR"
    fi
    
    sudo chmod 1777 "$RAY_TEMP_DIR"
    log_success "Ray temp directory permissions set"
}

# 修复 Ray session 权限 (集成 fix_ray_permissions.sh 功能)
fix_ray_session_permissions() {
    log_info "Fixing Ray session permissions with enhanced group access..."
    
    # 主要检查路径列表
    local session_paths=(
        "$RAY_TEMP_DIR/session_latest"
        "/var/lib/ray_shared/session_latest"
        "/tmp/ray/session_latest"
    )
    
    local fixed_any=false
    local target_group="sudo"
    
    for session_link in "${session_paths[@]}"; do
        log_info "Checking Ray session link: $session_link"
        
        # 检查软链接是否存在
        if [ ! -L "$session_link" ]; then
            log_info "Session link not found or not a symlink: $session_link"
            continue
        fi
        
        # 获取实际指向的路径
        local real_session_dir=$(readlink -f "$session_link")
        log_info "Session link points to: $real_session_dir"
        
        # 检查路径是否有效
        if [ ! -d "$real_session_dir" ]; then
            log_warning "Real session directory does not exist: $real_session_dir"
            continue
        fi
        
        log_info "Fixing permissions for session directory: $real_session_dir"
        
        # 修改组归属到 sudo 组
        if sudo chgrp -R "$target_group" "$real_session_dir" 2>/dev/null; then
            log_success "Changed group ownership to '$target_group' for $real_session_dir"
        else
            log_warning "Failed to change group ownership for $real_session_dir"
            continue
        fi
        
        # 添加组读写执行权限
        if sudo chmod -R g+rwX "$real_session_dir" 2>/dev/null; then
            log_success "Added group rwX permissions for $real_session_dir"
        else
            log_warning "Failed to add group permissions for $real_session_dir"
            continue
        fi
        
        # 设置目录为 setgid：后续创建文件自动继承组
        if sudo find "$real_session_dir" -type d -exec chmod g+s {} \; 2>/dev/null; then
            log_success "Set setgid on directories in $real_session_dir"
        else
            log_warning "Failed to set setgid on directories in $real_session_dir"
        fi
        
        # 特别设置关键文件权限（如果存在）
        local important_files=("$real_session_dir/session.json" "$real_session_dir/ray_param.json")
        for file in "${important_files[@]}"; do
            if [ -f "$file" ]; then
                if sudo chmod 664 "$file" 2>/dev/null; then
                    log_success "Fixed permissions for: $(basename $file)"
                fi
            fi
        done
        
        fixed_any=true
        log_success "Ray session permissions fixed for: $real_session_dir"
    done
    
    if [ "$fixed_any" = true ]; then
        log_success "Ray session permissions fixed! All sudo users can now access Ray sessions"
    else
        log_warning "No Ray session links found to fix permissions"
    fi
}

# 设置 Ray session 权限
setup_ray_session_permissions() {
    log_info "Setting Ray session permissions..."
    
    # 直接使用新的修复方法
    fix_ray_session_permissions
}

# 启动 Ray head 节点
start_ray_head() {
    log_info "Starting Ray head node..."
    
    # 检查端口冲突
    log_info "Checking port availability..."
    local ports_to_check=($RAY_HEAD_PORT $RAY_CLIENT_PORT $RAY_DASHBOARD_PORT)
    local conflicts=()
    
    for port in "${ports_to_check[@]}"; do
        if check_port $port; then
            conflicts+=($port)
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        log_error "Port conflicts detected: ${conflicts[*]}"
        log_error "Please stop conflicting services or use different ports"
        return 1
    fi
    
    # 设置 Ray temp 目录
    setup_ray_temp_dir
    
    # 启动 Ray head，明确指定端口避免冲突
    log_info "Starting Ray with ports: GCS=$RAY_HEAD_PORT, Client=$RAY_CLIENT_PORT, Dashboard=$RAY_DASHBOARD_PORT"
    
    ray start --head \
        --temp-dir="$RAY_TEMP_DIR" \
        --disable-usage-stats \
        --verbose \
        --resources="$RAY_RESOURCES"
        # --port=$RAY_HEAD_PORT \
        # --dashboard-port=$RAY_DASHBOARD_PORT \
        # --ray-client-server-port=$RAY_CLIENT_PORT \
    
    # 等待 Ray 启动完成
    sleep 5
    
    # 设置 session 权限
    setup_ray_session_permissions
    
    # 验证 Ray 状态
    if check_ray_status; then
        log_success "Ray head node started successfully"
        log_info "Ray ports: GCS=$RAY_HEAD_PORT, Client=$RAY_CLIENT_PORT, Dashboard=$RAY_DASHBOARD_PORT"
        return 0
    else
        log_error "Failed to start Ray head node"
        return 1
    fi
}

# 停止 Ray 集群
stop_ray_cluster() {
    if check_ray_status >/dev/null 2>&1; then
        log_info "Stopping Ray cluster..."
        ray stop
        sleep 2
        
        if ! check_ray_status >/dev/null 2>&1; then
            log_success "Ray cluster stopped successfully"
            return 0
        else
            log_warning "Ray cluster may not have stopped completely"
            return 1
        fi
    else
        log_info "Ray cluster is not running"
        return 0
    fi
}

# 重启 Ray 集群
restart_ray_cluster() {
    log_info "Restarting Ray cluster..."
    stop_ray_cluster
    sleep 3
    start_ray_head
}

# 获取 Ray 集群信息
get_ray_info() {
    if check_ray_status >/dev/null 2>&1; then
        echo "Ray Cluster Status: Running"
        echo "GCS Port: $RAY_HEAD_PORT"
        echo "Client Port: $RAY_CLIENT_PORT"
        echo "Dashboard Port: $RAY_DASHBOARD_PORT"
        echo "Dashboard URL: http://localhost:$RAY_DASHBOARD_PORT"
        echo "Temp Directory: $RAY_TEMP_DIR"
        return 0
    else
        echo "Ray Cluster Status: Not Running"
        return 1
    fi
}

# 独立的权限修复功能（等同于原 fix_ray_permissions.sh）
fix_ray_permissions_standalone() {
    log_info "=== Ray Permissions Repair Tool ==="
    log_info "This function provides the same functionality as fix_ray_permissions.sh"
    
    # 主要检查路径列表
    local session_paths=(
        "$RAY_TEMP_DIR/session_latest"
        "/var/lib/ray_shared/session_latest"
        "/tmp/ray/session_latest"
    )
    
    local target_group="sudo"
    local fixed_count=0
    
    for session_link in "${session_paths[@]}"; do
        echo "🔍 Checking Ray session link: $session_link"
        
        # 检查软链接是否存在
        if [ ! -L "$session_link" ]; then
            echo "❌ $session_link is not a symlink, skipping."
            continue
        fi
        
        # 获取实际指向的路径
        local real_session_dir=$(readlink -f "$session_link")
        echo "📍 Symlink points to: $real_session_dir"
        
        # 检查路径是否有效
        if [ ! -d "$real_session_dir" ]; then
            echo "❌ Real directory does not exist: $real_session_dir"
            continue
        fi
        
        echo "🛠️ Fixing permissions for group '$target_group' with group write access..."
        
        # 修改组归属
        if sudo chgrp -R "$target_group" "$real_session_dir"; then
            echo "✅ Changed group ownership to '$target_group'"
        else
            echo "❌ Failed to change group ownership"
            continue
        fi
        
        # 添加组读写执行权限
        if sudo chmod -R g+rwX "$real_session_dir"; then
            echo "✅ Added group rwX permissions"
        else
            echo "❌ Failed to add group permissions"
            continue
        fi
        
        # 设置目录为 setgid：后续创建文件自动继承组
        if sudo find "$real_session_dir" -type d -exec chmod g+s {} \;; then
            echo "✅ Set setgid on directories for automatic group inheritance"
        else
            echo "❌ Failed to set setgid"
        fi
        
        fixed_count=$((fixed_count + 1))
        echo "✅ Permission fix completed for: $real_session_dir"
        echo ""
    done
    
    if [ $fixed_count -gt 0 ]; then
        echo "🍰 Permission repair completed! Fixed $fixed_count Ray sessions."
        echo "All sudo users can now happily use Ray!"
        log_success "Ray permissions fixed for $fixed_count sessions"
        return 0
    else
        echo "⚠️ No Ray session links found to fix."
        log_warning "No Ray sessions found to repair permissions"
        return 1
    fi
}
