#!/bin/bash

# SAGE Conda 服务条款自动接受测试脚本

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 引入工具模块
source "$PROJECT_ROOT/scripts/logging.sh"
source "$PROJECT_ROOT/scripts/conda_utils.sh"

print_header "🧪 测试 Conda 服务条款自动接受功能"

# 检查 conda 是否可用
if ! command -v conda &> /dev/null; then
    print_error "conda 命令不可用，请先安装并初始化 Conda"
    exit 1
fi

print_status "当前 Conda 版本: $(conda --version)"

# 显示当前服务条款状态
print_header "📋 当前服务条款状态"
if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
    print_warning "发现未接受的服务条款:"
    conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted" | grep "https://" | sed 's/^[[:space:]]*/  • /'
    echo
else
    print_success "当前所有服务条款都已接受"
fi

# 测试自动接受功能
print_header "🚀 测试自动接受服务条款"

# 使用 set +e 来避免脚本因为单个命令失败而退出
set +e
accept_conda_tos
tos_result=$?
set -e

if [ $tos_result -eq 0 ]; then
    print_success "服务条款处理完成"
else
    print_warning "服务条款处理过程中有些问题，但可能不影响使用"
fi

# 验证结果
print_header "✅ 验证结果"
if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
    print_warning "仍有未接受的服务条款:"
    conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted"
    echo
    print_status "这可能是正常的，因为可能有其他频道的条款"
else
    print_success "所有服务条款都已接受！"
fi

# 测试环境创建功能
print_header "🔬 测试环境创建功能"
test_env_name="sage_test_tos_$$"

print_status "尝试创建测试环境: $test_env_name"
if conda create -n "$test_env_name" python=3.11 -y; then
    print_success "✓ 环境创建成功！服务条款问题已解决"
    
    # 清理测试环境
    print_status "清理测试环境..."
    conda env remove -n "$test_env_name" -y &>/dev/null
    print_debug "已删除测试环境"
else
    print_error "✗ 环境创建失败，可能还有其他问题"
fi

print_success "🎉 服务条款自动接受功能测试完成！"
