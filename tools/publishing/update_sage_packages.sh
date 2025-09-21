#!/bin/bash

# SAGE 闭源包精确更新脚本
# 只清理和更新 intellistream-sage 相关包，保留其他依赖项缓存

set -e

# 输出颜色
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

print_info() {
    echo -e "${BLUE}i $1${NC}"
}

# 确认函数
confirm() {
    read -p "$1 (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# 检查 Python 环境
check_python() {
    print_header "检查 Python 环境"
    
    if ! command -v python3 &> /dev/null; then
        print_error "未找到 python3 命令"
        exit 1
    fi
    
    if ! command -v pip &> /dev/null; then
        print_error "未找到 pip 命令"
        exit 1
    fi
    
    print_info "Python 版本: $(python3 --version)"
    print_info "Pip 版本: $(pip --version)"
    print_success "Python 环境检查通过"
}

# 精确卸载 intellistream-sage 包
uninstall_intellistream_sage() {
    print_header "精确卸载 intellistream-sage 相关包"
    
    # 列出已安装的 intellistream-sage 包
    print_info "当前已安装的 intellistream-sage 相关包:"
    pip list | grep -i intellistream-sage || true
    
    # 获取所有 intellistream-sage 包的列表
    SAGE_PACKAGES=$(pip list | grep -i intellistream-sage | awk '{print $1}')
    
    if [ -z "$SAGE_PACKAGES" ]; then
        print_warning "未找到已安装的 intellistream-sage 包"
        return 0
    fi
    
    # 卸载所有 intellistream-sage 包
    for pkg in $SAGE_PACKAGES; do
        print_info "卸载 $pkg..."
        pip uninstall -y "$pkg"
    done
    
    # 清理 pip 缓存中的 intellistream-sage 包
    print_info "清理 pip 缓存中的 intellistream-sage 包..."
    if pip cache list | grep -q intellistream-sage; then
        pip cache remove intellistream-sage*
    fi
    
    print_success "intellistream-sage 相关包卸载完成"
}

# 清理 site-packages 中的残留文件
clean_site_packages() {
    print_header "清理 site-packages 中的残留文件"
    
    # 获取 site-packages 路径
    SITE_PACKAGES=$(python3 -c "import site; print(site.getsitepackages()[0])")
    
    print_info "检查 $SITE_PACKAGES 中的残留文件"
    
    # 检查并删除 intellistream_sage 目录和 egg 信息
    if [ -d "$SITE_PACKAGES/intellistream_sage" ]; then
        print_info "删除 $SITE_PACKAGES/intellistream_sage 目录"
        rm -rf "$SITE_PACKAGES/intellistream_sage"
    fi
    
    # 检查并删除 intellistream_sage*.egg-info 目录
    for egg_info in "$SITE_PACKAGES"/intellistream_sage*.egg-info; do
        if [ -d "$egg_info" ]; then
            print_info "删除 $egg_info 目录"
            rm -rf "$egg_info"
        fi
    done
    
    # 检查并删除 sage 命名空间中的 kernel 子目录
    if [ -d "$SITE_PACKAGES/sage/kernel" ]; then
        print_info "删除 $SITE_PACKAGES/sage/kernel 目录"
        rm -rf "$SITE_PACKAGES/sage/kernel"
    fi
    
    # 检查并删除 sage 命名空间中的其他闭源组件目录
    for dir in middleware utils; do
        if [ -d "$SITE_PACKAGES/sage/$dir" ]; then
            print_info "删除 $SITE_PACKAGES/sage/$dir 目录"
            rm -rf "$SITE_PACKAGES/sage/$dir"
        fi
    done
    
    print_success "残留文件清理完成"
}

# 安装最新版本
install_latest() {
    print_header "安装最新版本"
    
    # 安装最新版本，--no-cache-dir 确保从网络获取最新版本
    print_info "安装 intellistream-sage-kernel..."
    pip install --no-cache-dir intellistream-sage-kernel
    
    print_info "安装 intellistream-sage-utils..."
    pip install --no-cache-dir intellistream-sage-utils
    
    print_info "安装 intellistream-sage-middleware..."
    pip install --no-cache-dir intellistream-sage-middleware
    
    print_info "安装 intellistream-sage..."
    pip install --no-cache-dir intellistream-sage
    
    print_success "安装完成"
}

# 验证安装
verify_installation() {
    print_header "验证安装"
    
    print_info "已安装的 intellistream-sage 相关包:"
    pip list | grep -i intellistream-sage
    
    # 尝试导入关键模块
    print_info "尝试导入 sage.kernel.JobManagerClient..."
    if python3 -c "from sage.kernel.jobmanager.jobmanager_client import JobManagerClient; print('导入成功: JobManagerClient 版本', getattr(JobManagerClient, '__version__', 'Unknown'))" 2>/dev/null; then
        print_success "JobManagerClient 导入成功"
    else
        print_error "JobManagerClient 导入失败"
        python3 -c "import sage.kernel; print('sage.kernel 中的内容:', dir(sage.kernel))"
    fi
    
    print_info "验证完成"
}

# 主函数
main() {
    print_header "SAGE 闭源包精确更新工具"
    
    check_python
    
    if confirm "是否卸载当前已安装的 intellistream-sage 相关包?"; then
        uninstall_intellistream_sage
        clean_site_packages
    else
        print_warning "跳过卸载步骤"
    fi
    
    if confirm "是否安装最新版本的 intellistream-sage 相关包?"; then
        install_latest
        verify_installation
    else
        print_warning "跳过安装步骤"
    fi
    
    print_header "操作完成"
}

# 执行主函数
main
