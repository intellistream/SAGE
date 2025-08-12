#!/bin/bash

# SAGE Kernel 打包验证脚本
# 确保核心功能模块被正确包含在打包结果中

set -e

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 辅助函数
print_header() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

# 检查是否在 sage-kernel 目录
check_directory() {
    if [[ ! -f "pyproject.toml" || ! -d "src/sage/kernel" ]]; then
        print_error "请在 sage-kernel 包目录下运行此脚本"
        exit 1
    fi
    print_success "当前目录: $(pwd)"
}

# 清理旧的构建结果
clean_build() {
    print_header "清理旧的构建结果"
    
    rm -rf build/ dist/ *.egg-info/
    print_success "清理完成"
}

# 构建包
build_package() {
    print_header "构建 sage-kernel 包"
    
    python -m build --wheel
    print_success "构建完成"
}

# 验证构建结果
verify_build() {
    print_header "验证构建结果"
    
    # 检查 wheel 文件是否存在
    WHEEL_FILE=$(find dist/ -name "*.whl" | sort -r | head -n 1)
    if [[ -z "$WHEEL_FILE" ]]; then
        print_error "未找到构建的 wheel 文件"
        exit 1
    fi
    
    print_success "找到 wheel 文件: $WHEEL_FILE"
    
    # 创建临时目录
    TEMP_DIR=$(mktemp -d)
    print_info "创建临时目录: $TEMP_DIR"
    
    # 解压 wheel 文件
    unzip -q "$WHEEL_FILE" -d "$TEMP_DIR"
    print_success "解压 wheel 文件到临时目录"
    
    # 检查关键文件
    print_header "检查核心文件是否存在"
    
    # 检查基本结构
    if [[ ! -d "$TEMP_DIR/sage" ]]; then
        print_error "未找到 sage 包目录"
        exit 1
    fi
    
    if [[ ! -d "$TEMP_DIR/sage/kernel" ]]; then
        print_error "未找到 sage/kernel 目录"
        exit 1
    fi
    
    # 检查 jobmanager
    if [[ ! -d "$TEMP_DIR/sage/kernel/jobmanager" ]]; then
        print_error "未找到 jobmanager 目录"
        print_warning "这可能导致导入错误: 'cannot import name JobManagerClient from sage.kernel'"
    else
        print_success "找到 jobmanager 目录"
        
        if [[ -f "$TEMP_DIR/sage/kernel/jobmanager/jobmanager_client.py" ]]; then
            print_success "找到 JobManagerClient 实现"
        else
            print_error "未找到 JobManagerClient 实现文件"
        fi
    fi
    
    # 检查 runtime
    if [[ ! -d "$TEMP_DIR/sage/kernel/runtime" ]]; then
        print_error "未找到 runtime 目录"
    else
        print_success "找到 runtime 目录"
    fi
    
    # 检查 enterprise
    if [[ -d "$TEMP_DIR/sage/kernel/enterprise" ]]; then
        print_warning "找到 enterprise 目录，但这应该被排除在外"
    else
        print_success "未找到 enterprise 目录 (正确)"
    fi
    
    # 显示包内文件
    print_header "wheel 包内文件列表"
    find "$TEMP_DIR/sage" -type f | sort
    
    # 清理临时目录
    rm -rf "$TEMP_DIR"
    print_success "清理临时目录"
}

# 主函数
main() {
    print_header "SAGE Kernel 打包验证"
    
    check_directory
    clean_build
    build_package
    verify_build
    
    print_header "验证完成"
    print_success "如果未发现错误，sage-kernel 打包正确"
}

# 执行主函数
main
