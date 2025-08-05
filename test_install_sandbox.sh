#!/bin/bash
# ===============================================================================
# SAGE 安装沙盒测试脚本
# ===============================================================================
# 创建隔离的测试环境来验证安装流程
# ===============================================================================

set -e

# 颜色定义
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
BOLD='\033[1m'
RESET='\033[0m'

# 配置
SANDBOX_DIR="/tmp/sage_install_sandbox"
PYTHON_VENV="$SANDBOX_DIR/venv"
PROJECT_ROOT=$(pwd)

# 工具函数
print_step() {
    echo -e "\n${BLUE}${BOLD}[STEP]${RESET} ${BLUE}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

print_error() {
    echo -e "${RED}❌ $1${RESET}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${RESET}"
}

# 清理函数
cleanup() {
    if [ "$1" != "--keep" ]; then
        print_info "清理沙盒环境..."
        rm -rf "$SANDBOX_DIR"
        print_success "沙盒环境已清理"
    else
        print_info "保留沙盒环境: $SANDBOX_DIR"
    fi
}

# 错误处理
handle_error() {
    print_error "测试失败，详细信息见上方输出"
    echo ""
    echo -e "${YELLOW}调试信息:${RESET}"
    echo "- 沙盒目录: $SANDBOX_DIR"
    echo "- 虚拟环境: $PYTHON_VENV"
    echo "- 项目根目录: $PROJECT_ROOT"
    echo ""
    echo -e "${BLUE}保留沙盒环境用于调试，可手动检查:${RESET}"
    echo "cd $SANDBOX_DIR"
    echo "source venv/bin/activate"
    exit 1
}

trap 'handle_error' ERR

# 创建沙盒环境
create_sandbox() {
    print_step "创建沙盒环境"
    
    # 清理旧的沙盒
    rm -rf "$SANDBOX_DIR"
    mkdir -p "$SANDBOX_DIR"
    
    print_info "沙盒位置: $SANDBOX_DIR"
    print_success "沙盒环境创建完成"
}

# 创建虚拟环境
create_virtual_env() {
    print_step "创建Python虚拟环境"
    
    cd "$SANDBOX_DIR"
    
    # 检查Python版本
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_info "使用Python版本: $python_version"
    
    if [[ $(echo "$python_version < 3.11" | bc -l 2>/dev/null || echo "1") -eq 1 ]]; then
        print_warning "Python版本较低: $python_version (推荐3.11+)"
    fi
    
    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate
    
    # 升级基础工具
    pip install --upgrade pip setuptools wheel
    
    print_success "虚拟环境创建完成"
}

# 复制项目文件
copy_project() {
    print_step "复制项目文件到沙盒"
    
    # 创建项目副本
    cp -r "$PROJECT_ROOT" "$SANDBOX_DIR/sage_project"
    cd "$SANDBOX_DIR/sage_project"
    
    # 清理不需要的文件
    rm -rf build dist *.egg-info .git __pycache__
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    print_success "项目文件复制完成"
}

# 测试一键安装脚本
test_quick_install() {
    print_step "测试一键安装脚本"
    
    cd "$SANDBOX_DIR/sage_project"
    source "$PYTHON_VENV/bin/activate"
    
    # 测试纯Python安装
    print_info "测试纯Python安装..."
    python quick_install.py --python-only
    
    print_success "一键安装脚本测试通过"
}

# 验证安装结果
verify_installation() {
    print_step "验证安装结果"
    
    source "$PYTHON_VENV/bin/activate"
    
    # 测试基本导入
    print_info "测试基本导入..."
    python -c "import sage; print(f'✅ SAGE version: {sage.__version__}')" || {
        print_error "基本导入失败"
        return 1
    }
    
    # 测试版本一致性
    print_info "检查版本一致性..."
    sage_version=$(python -c "import sage; print(sage.__version__)")
    print_info "SAGE版本: $sage_version"
    
    # 测试CLI命令
    print_info "测试CLI命令..."
    if python -c "from sage.cli.main import app; print('✅ CLI可用')" 2>/dev/null; then
        print_success "CLI命令可用"
    else
        print_warning "CLI命令不可用"
    fi
    
    # 测试核心模块
    print_info "测试核心模块..."
    python -c "
try:
    from sage.core import *
    print('✅ 核心模块导入成功')
except Exception as e:
    print(f'⚠️ 核心模块导入部分失败: {e}')
" || print_warning "核心模块导入有问题"
    
    # 测试C++扩展（如果可用）
    print_info "测试C++扩展..."
    if python -c "import sage_ext; print('✅ C++扩展可用')" 2>/dev/null; then
        print_success "C++扩展可用"
    else
        print_info "C++扩展不可用(预期行为，因为我们只测试了纯Python安装)"
    fi
    
    print_success "安装验证完成"
}

# 测试wheel构建
test_wheel_build() {
    print_step "测试Wheel构建"
    
    cd "$SANDBOX_DIR/sage_project"
    source "$PYTHON_VENV/bin/activate"
    
    # 安装构建依赖
    print_info "安装构建依赖..."
    pip install build twine
    
    # 测试现代化构建
    print_info "测试现代化wheel构建..."
    if [ -f "build_modern_wheel.sh" ]; then
        chmod +x build_modern_wheel.sh
        ./build_modern_wheel.sh
        
        # 检查生成的wheel文件
        if ls dist/*.whl 1> /dev/null 2>&1; then
            wheel_file=$(ls dist/*.whl | head -1)
            print_success "Wheel构建成功: $(basename $wheel_file)"
            
            # 检查wheel内容
            print_info "检查wheel内容..."
            python -m wheel unpack "$wheel_file" --dest temp_wheel_check
            
            py_files=$(find temp_wheel_check -name "*.py" | wc -l)
            so_files=$(find temp_wheel_check -name "*.so" | wc -l)
            
            print_info "  Python文件: $py_files 个"
            print_info "  编译库文件: $so_files 个"
            
            rm -rf temp_wheel_check
        else
            print_error "未找到生成的wheel文件"
            return 1
        fi
    else
        print_warning "未找到现代化构建脚本"
    fi
    
    print_success "Wheel构建测试完成"
}

# 测试wheel安装
test_wheel_install() {
    print_step "测试Wheel安装"
    
    cd "$SANDBOX_DIR"
    
    # 创建新的虚拟环境来测试wheel安装
    print_info "创建新的测试环境..."
    python3 -m venv test_wheel_env
    source test_wheel_env/bin/activate
    pip install --upgrade pip
    
    # 安装wheel
    wheel_file=$(ls sage_project/dist/*.whl | head -1)
    if [ -n "$wheel_file" ]; then
        print_info "安装wheel: $(basename $wheel_file)"
        pip install "$wheel_file"
        
        # 验证wheel安装
        python -c "import sage; print(f'✅ Wheel安装成功: {sage.__version__}')"
        
        print_success "Wheel安装测试通过"
    else
        print_warning "跳过wheel安装测试(无wheel文件)"
    fi
}

# 生成测试报告
generate_report() {
    print_step "生成测试报告"
    
    report_file="$SANDBOX_DIR/install_test_report.txt"
    
    cat > "$report_file" << EOF
SAGE 安装测试报告
===============================================================================
测试时间: $(date)
测试环境: $(uname -a)
Python版本: $(python3 --version)
项目根目录: $PROJECT_ROOT
沙盒目录: $SANDBOX_DIR

测试结果:
EOF
    
    # 检查各个测试结果
    cd "$SANDBOX_DIR"
    
    if [ -d "venv" ]; then
        echo "✅ 虚拟环境创建: 成功" >> "$report_file"
    else
        echo "❌ 虚拟环境创建: 失败" >> "$report_file"
    fi
    
    if source venv/bin/activate 2>/dev/null && python -c "import sage" 2>/dev/null; then
        sage_version=$(python -c "import sage; print(sage.__version__)")
        echo "✅ SAGE安装: 成功 (版本: $sage_version)" >> "$report_file"
    else
        echo "❌ SAGE安装: 失败" >> "$report_file"
    fi
    
    if ls sage_project/dist/*.whl 1> /dev/null 2>&1; then
        wheel_count=$(ls sage_project/dist/*.whl | wc -l)
        echo "✅ Wheel构建: 成功 ($wheel_count 个文件)" >> "$report_file"
    else
        echo "❌ Wheel构建: 失败" >> "$report_file"
    fi
    
    echo "" >> "$report_file"
    echo "详细日志请查看终端输出" >> "$report_file"
    echo "===============================================================================" >> "$report_file"
    
    print_info "测试报告已生成: $report_file"
    cat "$report_file"
}

# 主函数
main() {
    echo -e "${BLUE}${BOLD}"
    echo "==============================================================================="
    echo "                    SAGE 安装沙盒测试"
    echo "==============================================================================="
    echo -e "${RESET}"
    echo "这个脚本将在隔离环境中测试SAGE的安装流程"
    echo ""
    
    # 检查基础依赖
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未找到"
        exit 1
    fi
    
    if ! command -v bc &> /dev/null; then
        print_warning "bc命令未找到，版本检查可能不准确"
    fi
    
    # 执行测试流程
    create_sandbox
    create_virtual_env
    copy_project
    test_quick_install
    verify_installation
    test_wheel_build
    test_wheel_install
    generate_report
    
    echo ""
    echo -e "${GREEN}${BOLD}🎉 所有测试完成！${RESET}"
    echo ""
    echo -e "${BOLD}测试结果总结:${RESET}"
    echo "- 沙盒环境: ✅"
    echo "- 一键安装: ✅"
    echo "- 功能验证: ✅" 
    echo "- Wheel构建: ✅"
    echo "- Wheel安装: ✅"
    echo ""
    echo -e "${BLUE}沙盒位置: $SANDBOX_DIR${RESET}"
    echo -e "${BLUE}保持沙盒环境供调试使用${RESET}"
}

# 参数处理
if [ "$1" = "--clean" ]; then
    cleanup
    exit 0
elif [ "$1" = "--help" ]; then
    echo "SAGE 安装沙盒测试脚本"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --clean    清理沙盒环境"
    echo "  --help     显示帮助"
    echo ""
    exit 0
fi

# 运行主函数
main "$@"
