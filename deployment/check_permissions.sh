#!/bin/bash

# SAGE Shared Permissions Checker
# SAGE 共享权限检测脚本
#
# 功能：
# 1. 检测所有SAGE相关目录的权限状态
# 2. 验证用户权限配置
# 3. 提供权限问题诊断建议
# 4. 生成权限状态报告

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_header() { echo -e "${PURPLE}[===]${NC} $1"; }
log_detail() { echo -e "${CYAN}[→]${NC}   $1"; }

# Get script directory and load configuration
SCRIPT_DIR="$(dirname $(realpath $0))"
source "$SCRIPT_DIR/config/environment.sh" 2>/dev/null || {
    log_warning "Cannot load environment config, using defaults"
    RAY_TEMP_DIR="/var/lib/ray_shared"
    SAGE_LOG_DIR="/home/$(whoami)/SAGE/logs"
    SAGE_PID_DIR="/tmp/sage"
    SAGE_TEMP_DIR="/tmp/sage"
}

# Global variables for statistics
TOTAL_CHECKS=0
PASSED_CHECKS=0
WARNING_CHECKS=0
FAILED_CHECKS=0

# Increment check counters
increment_check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    case "$1" in
        "pass") PASSED_CHECKS=$((PASSED_CHECKS + 1)) ;;
        "warn") WARNING_CHECKS=$((WARNING_CHECKS + 1)) ;;
        "fail") FAILED_CHECKS=$((FAILED_CHECKS + 1)) ;;
    esac
}

# Check if user is in sudo group
is_sudo_user() {
    if groups | grep -q sudo; then
        return 0
    else
        return 1
    fi
}

# Get expected permissions based on user type
get_expected_permissions() {
    if is_sudo_user; then
        echo "root:sudo 775/664"
    else
        echo "user:user 755/644"
    fi
}

# Check directory permissions
check_directory_permissions() {
    local dir_path=$1
    local dir_name=$2
    local is_critical=${3:-true}
    
    log_info "Checking $dir_name: $dir_path"
    
    if [ ! -d "$dir_path" ]; then
        log_error "Directory does not exist: $dir_path"
        increment_check "fail"
        return 1
    fi
    
    # Get directory information
    local owner=$(stat -c "%U" "$dir_path" 2>/dev/null || echo "unknown")
    local group=$(stat -c "%G" "$dir_path" 2>/dev/null || echo "unknown")
    local perms=$(stat -c "%a" "$dir_path" 2>/dev/null || echo "000")
    local readable=$([ -r "$dir_path" ] && echo "yes" || echo "no")
    local writable=$([ -w "$dir_path" ] && echo "yes" || echo "no")
    local executable=$([ -x "$dir_path" ] && echo "yes" || echo "no")
    
    log_detail "Owner: $owner"
    log_detail "Group: $group"
    log_detail "Permissions: $perms"
    log_detail "Access: r=$readable w=$writable x=$executable"
    
    # Check setgid bit
    local setgid_info=""
    if [ -d "$dir_path" ]; then
        local full_perms=$(stat -c "%A" "$dir_path" 2>/dev/null || echo "")
        if [[ "$full_perms" == *"s"* ]]; then
            setgid_info=" (setgid enabled)"
        fi
    fi
    if [ -n "$setgid_info" ]; then
        log_detail "Special bits:$setgid_info"
    fi
    
    # Determine if permissions are correct
    local status="pass"
    local expected_perms=$(get_expected_permissions)
    
    if is_sudo_user; then
        # For sudo users, expect root:sudo ownership
        if [ "$owner" != "root" ] || [ "$group" != "sudo" ]; then
            if [ "$is_critical" = "true" ]; then
                status="warn"
                log_warning "Expected root:sudo ownership, got $owner:$group"
            fi
        fi
        
        # Check if permissions allow group write access
        if [[ ! "$perms" =~ ^[0-9]*[67][0-9]$ ]] && [[ ! "$perms" =~ ^[0-9]*7[0-9][0-9]$ ]]; then
            if [ "$is_critical" = "true" ]; then
                status="warn"  
                log_warning "Expected group write permissions (x6x or x7x), got $perms"
            fi
        fi
    else
        # For regular users, check if they have access
        if [ "$writable" = "no" ] && [ "$is_critical" = "true" ]; then
            status="fail"
            log_error "No write access to critical directory"
        fi
    fi
    
    # Final status
    case $status in
        "pass")
            log_success "Directory permissions OK"
            ;;
        "warn")
            log_warning "Directory permissions suboptimal but functional"
            ;;
        "fail")
            log_error "Directory permissions problematic"
            ;;
    esac
    
    increment_check "$status"
    echo
}

# Check file permissions
check_file_permissions() {
    local file_path=$1
    local file_desc=$2
    
    log_info "Checking $file_desc: $file_path"
    
    if [ ! -f "$file_path" ]; then
        log_warning "File does not exist: $file_path"
        increment_check "warn"
        echo
        return 1
    fi
    
    # Get file information
    local owner=$(stat -c "%U" "$file_path" 2>/dev/null || echo "unknown")
    local group=$(stat -c "%G" "$file_path" 2>/dev/null || echo "unknown")
    local perms=$(stat -c "%a" "$file_path" 2>/dev/null || echo "000")
    local readable=$([ -r "$file_path" ] && echo "yes" || echo "no")
    local writable=$([ -w "$file_path" ] && echo "yes" || echo "no")
    local size=$(stat -c "%s" "$file_path" 2>/dev/null || echo "0")
    local modified=$(stat -c "%y" "$file_path" 2>/dev/null || echo "unknown")
    
    log_detail "Owner: $owner"
    log_detail "Group: $group"
    log_detail "Permissions: $perms"
    log_detail "Access: r=$readable w=$writable"
    log_detail "Size: $size bytes"
    log_detail "Modified: $modified"
    
    # Check if accessible
    if [ "$readable" = "yes" ]; then
        log_success "File is accessible"
        increment_check "pass"
    else
        log_error "File is not accessible"
        increment_check "fail"
    fi
    
    echo
}

# Check process permissions
check_running_processes() {
    log_info "Checking running SAGE processes"
    
    # Check Ray processes
    local ray_processes=$(pgrep -f "ray" 2>/dev/null | wc -l)
    if [ $ray_processes -gt 0 ]; then
        log_success "Ray processes running: $ray_processes"
        
        # Show Ray process details
        log_detail "Ray processes:"
        pgrep -f "ray" -a | while read pid cmd; do
            local user=$(ps -o user= -p $pid 2>/dev/null || echo "unknown")
            log_detail "  PID $pid ($user): $cmd"
        done
        increment_check "pass"
    else
        log_warning "No Ray processes found"
        increment_check "warn"
    fi
    
    echo
    
    # Check daemon processes
    local daemon_processes=$(pgrep -f "jobmanager_daemon" 2>/dev/null | wc -l)
    if [ $daemon_processes -gt 0 ]; then
        log_success "JobManager Daemon processes running: $daemon_processes"
        increment_check "pass"
    else
        log_warning "No JobManager Daemon processes found"
        increment_check "warn"
    fi
    
    echo
}

# Check lock files
check_lock_files() {
    log_info "Checking for problematic lock files"
    
    local lock_dirs=("/var/lib/ray_shared" "/tmp/ray")
    local total_locks=0
    local old_locks=0
    
    for dir in "${lock_dirs[@]}"; do
        if [ -d "$dir" ]; then
            local locks=$(find "$dir" -name "*.lock" 2>/dev/null | wc -l)
            local old_locks_in_dir=$(find "$dir" -name "*.lock" -mtime +1 2>/dev/null | wc -l)
            
            total_locks=$((total_locks + locks))
            old_locks=$((old_locks + old_locks_in_dir))
            
            if [ $locks -gt 0 ]; then
                log_detail "Lock files in $dir: $locks (old: $old_locks_in_dir)"
                
                # Show some lock file details
                find "$dir" -name "*.lock" 2>/dev/null | head -3 | while read lock_file; do
                    local lock_age=$(stat -c "%Y" "$lock_file" 2>/dev/null || echo "0")
                    local current_time=$(date +%s)
                    local age_hours=$(( (current_time - lock_age) / 3600 ))
                    local lock_owner=$(stat -c "%U" "$lock_file" 2>/dev/null || echo "unknown")
                    log_detail "  $(basename $lock_file) - ${age_hours}h old, owner: $lock_owner"
                done
            fi
        fi
    done
    
    if [ $total_locks -eq 0 ]; then
        log_success "No lock files found"
        increment_check "pass"
    elif [ $old_locks -gt 0 ]; then
        log_warning "Found $old_locks old lock files (>24h), consider cleaning"
        log_detail "Run: find /var/lib/ray_shared /tmp/ray -name '*.lock' -mtime +1 -delete"
        increment_check "warn"
    else
        log_info "Found $total_locks recent lock files (normal for active system)"
        increment_check "pass"
    fi
    
    echo
}

# Show user and group information
show_user_info() {
    log_header "User and Group Information"
    
    local current_user=$(whoami)
    local primary_group=$(id -gn)
    local all_groups=$(groups)
    local uid=$(id -u)
    local gid=$(id -g)
    
    log_info "Current user: $current_user (UID: $uid)"
    log_info "Primary group: $primary_group (GID: $gid)"
    log_info "All groups: $all_groups"
    
    if is_sudo_user; then
        log_success "User is in sudo group (shared permissions enabled)"
        log_detail "Permission strategy: root:sudo with 775/664 permissions"
    else
        log_warning "User is NOT in sudo group (individual permissions)"
        log_detail "Permission strategy: user:user with 755/644 permissions"
        log_detail "Consider: sudo usermod -a -G sudo $current_user"
    fi
    
    echo
}

# Main permission check function
run_permission_checks() {
    log_header "SAGE Shared Directory Permission Checks"
    echo
    
    # Check critical directories
    check_directory_permissions "$RAY_TEMP_DIR" "Ray Shared Directory" true
    check_directory_permissions "$SAGE_PID_DIR" "SAGE PID Directory" true  
    check_directory_permissions "$SAGE_LOG_DIR" "SAGE Log Directory" true
    check_directory_permissions "/tmp/ray" "Ray Session Directory" false
    
    # Check for specific files
    if [ -f "$SAGE_PID_DIR/daemon.pid" ]; then
        check_file_permissions "$SAGE_PID_DIR/daemon.pid" "Daemon PID File"
    fi
    
    # Check Ray session latest link
    if [ -L "/tmp/ray/session_latest" ]; then
        local session_dir=$(readlink -f "/tmp/ray/session_latest" 2>/dev/null || echo "")
        if [ -n "$session_dir" ] && [ -d "$session_dir" ]; then
            check_directory_permissions "$session_dir" "Current Ray Session" false
            
            if [ -f "$session_dir/session.json" ]; then
                check_file_permissions "$session_dir/session.json" "Ray Session Config"
            fi
        fi
    fi
    
    # Check processes and locks
    check_running_processes
    check_lock_files
}

# Generate recommendations
generate_recommendations() {
    log_header "Recommendations"
    
    if [ $FAILED_CHECKS -gt 0 ]; then
        log_error "Found $FAILED_CHECKS critical permission issues"
        log_info "Run: ./sage_deployment.sh fix-permissions"
    fi
    
    if [ $WARNING_CHECKS -gt 0 ]; then
        log_warning "Found $WARNING_CHECKS permission warnings"
        if ! is_sudo_user; then
            log_info "Consider adding user to sudo group for shared access:"
            log_detail "sudo usermod -a -G sudo $(whoami)"
            log_detail "Then logout and login again"
        fi
    fi
    
    if [ $FAILED_CHECKS -eq 0 ] && [ $WARNING_CHECKS -eq 0 ]; then
        log_success "All permission checks passed!"
        log_info "SAGE system should work properly"
    fi
    
    echo
    log_info "Available fix commands:"
    log_detail "./sage_deployment.sh fix-permissions      # Fix all permissions"
    log_detail "./sage_deployment.sh setup-permissions    # Setup from scratch"  
    log_detail "./fix_permissions.sh                      # Standalone fix script"
    
    echo
}

# Show summary
show_summary() {
    log_header "Summary"
    
    local pass_color=$GREEN
    local warn_color=$YELLOW  
    local fail_color=$RED
    
    if [ $FAILED_CHECKS -gt 0 ]; then
        local status_color=$fail_color
        local status_text="FAILED"
    elif [ $WARNING_CHECKS -gt 0 ]; then
        local status_color=$warn_color
        local status_text="WARNING"
    else
        local status_color=$pass_color
        local status_text="PASSED"
    fi
    
    echo -e "Total Checks: $TOTAL_CHECKS"
    echo -e "${pass_color}Passed: $PASSED_CHECKS${NC}"
    echo -e "${warn_color}Warnings: $WARNING_CHECKS${NC}" 
    echo -e "${fail_color}Failed: $FAILED_CHECKS${NC}"
    echo
    echo -e "Overall Status: ${status_color}$status_text${NC}"
    echo
}

# Main function
main() {
    echo "========================================"
    echo "  SAGE Shared Permissions Checker"
    echo "  共享权限检测工具"  
    echo "========================================"
    echo
    
    show_user_info
    run_permission_checks
    generate_recommendations
    show_summary
    
    # Exit with appropriate code
    if [ $FAILED_CHECKS -gt 0 ]; then
        exit 1
    elif [ $WARNING_CHECKS -gt 0 ]; then
        exit 2
    else
        exit 0
    fi
}

# Run the main function
main "$@"
