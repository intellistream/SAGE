#!/bin/bash

# PyPI 认证设置脚本
# 帮助设置 PyPI 和 TestPyPI 的认证信息

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
PyPI 认证设置脚本

用法: $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -i, --interactive   交互式设置
    -c, --check         检查现有配置
    -r, --reset         重置配置文件

此脚本将帮助您设置 PyPI 上传所需的认证信息。

需要的信息:
1. PyPI API Token (https://pypi.org/manage/account/token/)
2. TestPyPI API Token (https://test.pypi.org/manage/account/token/)

EOF
}

# 检查现有配置
check_config() {
    log_info "检查现有 PyPI 配置..."
    
    local pypirc_file="$HOME/.pypirc"
    
    if [[ -f "$pypirc_file" ]]; then
        log_info "找到现有的 .pypirc 文件"
        
        # 检查是否包含 PyPI 配置
        if grep -q "\[pypi\]" "$pypirc_file"; then
            log_success "PyPI 配置存在"
        else
            log_warning "PyPI 配置缺失"
        fi
        
        # 检查是否包含 TestPyPI 配置
        if grep -q "\[testpypi\]" "$pypirc_file"; then
            log_success "TestPyPI 配置存在"
        else
            log_warning "TestPyPI 配置缺失"
        fi
        
        echo
        log_info "当前配置内容:"
        cat "$pypirc_file"
    else
        log_warning "未找到 .pypirc 文件"
    fi
    
    # 检查环境变量
    if [[ -n "$TWINE_USERNAME" ]]; then
        log_info "TWINE_USERNAME 环境变量已设置: $TWINE_USERNAME"
    fi
    
    if [[ -n "$TWINE_PASSWORD" ]]; then
        log_info "TWINE_PASSWORD 环境变量已设置"
    fi
}

# 创建 .pypirc 文件
create_pypirc() {
    local pypirc_file="$HOME/.pypirc"
    
    log_info "创建 .pypirc 文件..."
    
    cat > "$pypirc_file" << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
EOF
    
    # 设置适当的权限
    chmod 600 "$pypirc_file"
    
    log_success ".pypirc 文件已创建"
}

# 交互式设置
interactive_setup() {
    log_info "开始交互式设置..."
    
    local pypirc_file="$HOME/.pypirc"
    
    # 询问是否要创建/覆盖 .pypirc 文件
    if [[ -f "$pypirc_file" ]]; then
        echo
        read -p "检测到现有的 .pypirc 文件，是否要覆盖？(y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "保持现有配置"
            return 0
        fi
    fi
    
    # 创建基本的 .pypirc 文件
    create_pypirc
    
    echo
    log_warning "重要提示:"
    echo "1. 您需要手动添加 API tokens 到 .pypirc 文件中"
    echo "2. 或者使用环境变量 TWINE_PASSWORD"
    echo
    echo "获取 API tokens:"
    echo "- PyPI: https://pypi.org/manage/account/token/"
    echo "- TestPyPI: https://test.pypi.org/manage/account/token/"
    echo
    
    read -p "是否要现在编辑 .pypirc 文件？(y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} "$pypirc_file"
    fi
    
    echo
    log_info "您也可以使用环境变量:"
    echo "export TWINE_USERNAME=__token__"
    echo "export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    echo
    echo "建议将这些添加到您的 ~/.bashrc 或 ~/.zshrc 文件中"
}

# 重置配置
reset_config() {
    local pypirc_file="$HOME/.pypirc"
    
    echo
    read -p "确定要重置 PyPI 配置吗？这将删除现有的 .pypirc 文件。(y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ -f "$pypirc_file" ]]; then
            rm "$pypirc_file"
            log_success ".pypirc 文件已删除"
        else
            log_info "没有找到 .pypirc 文件"
        fi
    else
        log_info "操作已取消"
    fi
}

# 显示使用示例
show_examples() {
    cat << 'EOF'

使用示例:

1. 设置环境变量方式:
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

2. 使用 .pypirc 文件:
   编辑 ~/.pypirc，添加:
   
   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   
   [testpypi]  
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

3. 测试配置:
   twine upload --repository testpypi dist/*

4. 正式上传:
   twine upload dist/*

EOF
}

# 默认配置
INTERACTIVE=false
CHECK_ONLY=false
RESET=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            show_examples
            exit 0
            ;;
        -i|--interactive)
            INTERACTIVE=true
            shift
            ;;
        -c|--check)
            CHECK_ONLY=true
            shift
            ;;
        -r|--reset)
            RESET=true
            shift
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 主逻辑
if [[ "$CHECK_ONLY" == "true" ]]; then
    check_config
elif [[ "$RESET" == "true" ]]; then
    reset_config
elif [[ "$INTERACTIVE" == "true" ]]; then
    interactive_setup
else
    # 默认行为：检查配置并提供建议
    check_config
    echo
    log_info "使用 '$0 --interactive' 进行交互式设置"
    log_info "使用 '$0 --help' 查看更多信息"
fi
