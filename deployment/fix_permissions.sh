#!/bin/bash

# Emergency Permission Fix Script for Shared Lab Environment
# 实验室共享机器权限紧急修复脚本

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=== SAGE Permission Fix Tool for Shared Lab Environment ==="
echo

# Get current user info
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

log_info "Running as user: $CURRENT_USER:$CURRENT_GROUP"

# Check if user is in sudo group
if groups | grep -q sudo; then
    PERMISSION_MODE="sudo_shared"
    log_info "User is in sudo group - using shared permissions (root:sudo 775)"
else
    PERMISSION_MODE="individual"
    log_warning "User not in sudo group - using individual permissions (user:user 755)"
fi
echo

# Fix /tmp/sage directory permissions
log_info "Fixing /tmp/sage directory permissions..."
SAGE_TMP_DIR="/tmp/sage"

if [ -d "$SAGE_TMP_DIR" ]; then
    if [ "$PERMISSION_MODE" = "sudo_shared" ]; then
        # Shared permissions for sudo group
        sudo chown -R root:sudo "$SAGE_TMP_DIR"
        sudo chmod 775 "$SAGE_TMP_DIR"
        sudo chmod g+s "$SAGE_TMP_DIR"
        sudo chmod -R 664 "$SAGE_TMP_DIR"/*.pid 2>/dev/null || true
        log_success "/tmp/sage configured for sudo group sharing"
    else
        # Individual permissions
        OWNER=$(stat -c "%U" "$SAGE_TMP_DIR")
        if [ "$OWNER" != "$CURRENT_USER" ]; then
            log_warning "Directory owned by $OWNER, changing to $CURRENT_USER"
            sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$SAGE_TMP_DIR"
        fi
        chmod 755 "$SAGE_TMP_DIR"
        chmod -R u+rw "$SAGE_TMP_DIR"
        log_success "/tmp/sage configured for individual user"
    fi
else
    log_info "Creating /tmp/sage directory"
    mkdir -p "$SAGE_TMP_DIR"
    if [ "$PERMISSION_MODE" = "sudo_shared" ]; then
        sudo chown root:sudo "$SAGE_TMP_DIR"
        sudo chmod 775 "$SAGE_TMP_DIR"
        sudo chmod g+s "$SAGE_TMP_DIR"
    else
        chmod 755 "$SAGE_TMP_DIR"
    fi
    log_success "/tmp/sage directory created"
fi

# Fix Ray shared directory permissions  
log_info "Fixing Ray shared directory permissions..."
RAY_SHARED_DIR="/var/lib/ray_shared"

if [ -d "$RAY_SHARED_DIR" ]; then
    if [ "$PERMISSION_MODE" = "sudo_shared" ]; then
        # Shared permissions for sudo group
        sudo chown -R root:sudo "$RAY_SHARED_DIR"
        sudo chmod -R 775 "$RAY_SHARED_DIR"
        sudo chmod g+s "$RAY_SHARED_DIR"
        find "$RAY_SHARED_DIR" -name "*.lock" -exec sudo chmod 664 {} \; 2>/dev/null || true
        find "$RAY_SHARED_DIR" -name "*.json" -exec sudo chmod 664 {} \; 2>/dev/null || true
        log_success "Ray shared directory configured for sudo group sharing"
    else
        # Individual permissions
        OWNER=$(stat -c "%U" "$RAY_SHARED_DIR" 2>/dev/null || echo "unknown")
        if [ "$OWNER" != "$CURRENT_USER" ] && [ "$OWNER" != "unknown" ]; then
            log_warning "Ray shared directory owned by $OWNER, trying to fix"
            if sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$RAY_SHARED_DIR" 2>/dev/null; then
                log_success "Ray shared directory ownership changed"
            else
                log_warning "Cannot change ownership, setting broader permissions"
                sudo chmod -R 755 "$RAY_SHARED_DIR" 2>/dev/null || true
            fi
        fi
        sudo chmod -R u+rw "$RAY_SHARED_DIR" 2>/dev/null || true
        find "$RAY_SHARED_DIR" -name "*.lock" -exec sudo chmod 666 {} \; 2>/dev/null || true
        find "$RAY_SHARED_DIR" -name "*.json" -exec sudo chmod 644 {} \; 2>/dev/null || true
        log_success "Ray shared directory configured for individual user"
    fi
else
    log_warning "Ray shared directory not found: $RAY_SHARED_DIR"
fi

# Fix any existing Ray sessions in /tmp/ray
log_info "Fixing Ray session permissions in /tmp/ray..."
RAY_TMP_DIR="/tmp/ray"

if [ -d "$RAY_TMP_DIR" ]; then
    if [ "$PERMISSION_MODE" = "sudo_shared" ]; then
        # Shared permissions for sudo group
        sudo chown -R root:sudo "$RAY_TMP_DIR"
        sudo chmod -R 775 "$RAY_TMP_DIR"
        sudo chmod g+s "$RAY_TMP_DIR"
        log_success "Ray sessions configured for sudo group sharing"
    else
        # Individual permissions
        sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$RAY_TMP_DIR" 2>/dev/null || true
        chmod -R 755 "$RAY_TMP_DIR" 2>/dev/null || true
        log_success "Ray sessions configured for individual user"
    fi
    
    # Fix session_latest symlink if it exists
    SESSION_LATEST="$RAY_TMP_DIR/session_latest"
    if [ -L "$SESSION_LATEST" ]; then
        ACTUAL_SESSION=$(readlink -f "$SESSION_LATEST")
        if [ -d "$ACTUAL_SESSION" ]; then
            log_info "Fixing permissions for session: $ACTUAL_SESSION"
            if [ "$PERMISSION_MODE" = "sudo_shared" ]; then
                sudo chown -R root:sudo "$ACTUAL_SESSION" 2>/dev/null || true
                sudo chmod -R 775 "$ACTUAL_SESSION" 2>/dev/null || true
            else
                sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$ACTUAL_SESSION" 2>/dev/null || true
                chmod -R 755 "$ACTUAL_SESSION" 2>/dev/null || true
            fi
        fi
    fi
else
    log_info "No existing Ray sessions found in /tmp/ray"
fi

# Clean up any stale lock files
log_info "Cleaning up stale lock files..."
find /var/lib/ray_shared -name "*.lock" -mtime +1 -delete 2>/dev/null || true
find /tmp/ray -name "*.lock" -mtime +1 -delete 2>/dev/null || true
log_success "Stale lock files cleaned"

echo
log_success "=== Permission fix completed! ==="
if [ "$PERMISSION_MODE" = "sudo_shared" ]; then
    log_info "✨ Configured for shared lab environment with sudo group permissions"
    log_info "   - All SAGE users in sudo group can access shared resources"
    log_info "   - Files are owned by root:sudo with 775/664 permissions"
else
    log_info "⚠️  Configured for individual user (not in sudo group)"
    log_info "   - Only current user can access SAGE resources"
    log_info "   - Consider adding user to sudo group for shared access"
fi
log_info "🚀 You can now try running the SAGE system again."
echo
