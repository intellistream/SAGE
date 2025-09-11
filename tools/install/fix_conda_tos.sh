#!/bin/bash

# SAGE Conda 服务条款修复脚本
# 解决新机器上初次使用 Conda 时的服务条款问题

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 引入日志模块
source "$SCRIPT_DIR/logging.sh"

print_header "🔧 Conda 服务条款修复工具"

# 检查 conda 是否可用
if ! command -v conda &> /dev/null; then
    print_error "conda 命令不可用"
    print_status "请先确保 Conda 已正确安装并初始化"
    print_status "运行: source ~/.bashrc 或重新打开终端"
    exit 1
fi

print_status "当前 Conda 版本: $(conda --version)"

# 显示当前频道配置
print_header "📋 当前 Conda 配置"
print_status "当前配置的频道:"
conda config --show channels 2>/dev/null || echo "  (无自定义频道配置)"

echo
print_status "检查服务条款状态..."

# 检查是否有服务条款问题
if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
    print_warning "发现未接受的服务条款"
    
    # 显示需要接受的频道
    echo "需要接受服务条款的频道:"
    conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted" | grep "https://" | sed 's/^[[:space:]]*/  • /'
    
    echo
    echo "选择解决方案:"
    echo "1) 🏃 快速修复 - 自动接受主要频道的服务条款"
    echo "2) 🔄 使用 conda-forge - 配置使用 conda-forge 频道 (推荐)"
    echo "3) 🛠️  手动修复 - 显示手动修复命令"
    echo "4) ❌ 退出"
    
    read -p "请输入选择 (1-4): " choice
    
    case $choice in
        1)
            print_status "自动接受服务条款..."
            
            # 主要频道列表
            channels=(
                "https://repo.anaconda.com/pkgs/main"
                "https://repo.anaconda.com/pkgs/r"
            )
            
            for channel in "${channels[@]}"; do
                print_status "接受频道: $channel"
                if conda tos accept --override-channels --channel "$channel"; then
                    print_success "✓ 已接受: $channel"
                else
                    print_warning "✗ 失败: $channel"
                fi
            done
            ;;
            
        2)
            print_status "配置 conda-forge 频道..."
            
            # 添加 conda-forge 频道并设置优先级
            conda config --add channels conda-forge
            conda config --set channel_priority strict
            
            print_success "✓ 已配置 conda-forge 频道为默认"
            print_status "新的频道配置:"
            conda config --show channels
            ;;
            
        3)
            print_header "🛠️ 手动修复命令"
            echo "请根据上面显示的频道，手动运行以下命令:"
            echo
            conda info 2>&1 | grep "https://" | sed 's/^[[:space:]]*/conda tos accept --override-channels --channel /' | sed 's/$//'
            echo
            echo "或者使用 conda-forge:"
            echo "conda config --add channels conda-forge"
            echo "conda config --set channel_priority strict"
            exit 0
            ;;
            
        4)
            print_status "用户选择退出"
            exit 0
            ;;
            
        *)
            print_error "无效选择"
            exit 1
            ;;
    esac
    
else
    print_success "✓ 所有服务条款都已接受，无需修复"
fi

# 验证修复结果
print_header "🧪 验证修复结果"
print_status "重新检查服务条款状态..."

if conda info 2>&1 | grep -q "Terms of Service have not been accepted"; then
    print_warning "仍有未接受的服务条款，可能需要手动处理"
    print_status "剩余的问题:"
    conda info 2>&1 | grep -A 10 "Terms of Service have not been accepted"
else
    print_success "✅ 所有服务条款问题已解决！"
    
    # 测试创建临时环境
    print_status "测试环境创建功能..."
    test_env_name="sage_test_$$"
    
    if conda create -n "$test_env_name" python=3.11 -y &>/dev/null; then
        print_success "✓ 环境创建测试通过"
        conda env remove -n "$test_env_name" -y &>/dev/null
        print_debug "已清理测试环境"
    else
        print_warning "环境创建测试失败，可能还有其他问题"
    fi
fi

echo
print_success "🎉 修复完成！现在可以重新运行 SAGE 安装脚本了"
print_status "运行: ./quickstart.sh"
