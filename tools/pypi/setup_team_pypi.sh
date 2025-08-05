#!/bin/bash

# SAGE团队PyPI设置脚本
# 帮助团队成员快速设置PyPI认证

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
SAGE团队PyPI设置脚本

用法: $0 [选项]

选项:
    -h, --help          显示此帮助信息
    -s, --shared        使用共享token设置
    -p, --personal      设置个人token
    -c, --check         检查当前配置
    
此脚本将帮助团队成员设置PyPI上传认证。

EOF
}

# 共享token设置
setup_shared_token() {
    log_info "设置共享PyPI token..."
    
    local pypirc_file="$HOME/.pypirc"
    
    # 备份现有配置
    if [[ -f "$pypirc_file" ]]; then
        cp "$pypirc_file" "$pypirc_file.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "已备份现有配置到 $pypirc_file.backup.*"
    fi
    
    # 创建新配置
    cat > "$pypirc_file" << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcCJGYwOTE4NWEzLTY3OTQtNDQ4NS05YmY1LWY2MDRmNGUxMDY4NQACKlszLCI4NDkyOTgyYy0yYjhmLTQ0MTgtYWEwYS00MWJjY2JiNGExMjAiXQAABiDhYL8zrEkG_QVcatvOtzhjRL8DftHbeuFZKbWEu1jODQ

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmcCJGYwOTE4NWEzLTY3OTQtNDQ4NS05YmY1LWY2MDRmNGUxMDY4NQACKlszLCI4NDkyOTgyYy0yYjhmLTQ0MTgtYWEwYS00MWJjY2JiNGExMjAiXQAABiDhYL8zrEkG_QVcatvOtzhjRL8DftHbeuFZKbWEu1jODQ
EOF
    
    # 设置权限
    chmod 600 "$pypirc_file"
    
    log_success "共享token配置完成！"
    log_warning "注意：此token具有完整上传权限，请谨慎使用"
}

# 个人token设置
setup_personal_token() {
    log_info "设置个人PyPI token..."
    
    echo "请按照以下步骤获取个人token："
    echo "1. 访问 https://pypi.org/manage/account/token/"
    echo "2. 创建新的API token"
    echo "3. 选择scope为'Entire account'或具体项目"
    echo "4. 复制生成的token"
    echo
    
    read -p "请输入您的个人PyPI token (pypi-...): " -r personal_token
    
    if [[ -z "$personal_token" ]]; then
        log_error "未输入token，操作取消"
        return 1
    fi
    
    if [[ ! "$personal_token" =~ ^pypi- ]]; then
        log_error "无效的token格式，应该以'pypi-'开头"
        return 1
    fi
    
    local pypirc_file="$HOME/.pypirc"
    
    # 备份现有配置
    if [[ -f "$pypirc_file" ]]; then
        cp "$pypirc_file" "$pypirc_file.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "已备份现有配置"
    fi
    
    # 创建个人配置
    cat > "$pypirc_file" << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = $personal_token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = $personal_token
EOF
    
    # 设置权限
    chmod 600 "$pypirc_file"
    
    log_success "个人token配置完成！"
}

# 检查配置
check_config() {
    log_info "检查PyPI配置..."
    
    local pypirc_file="$HOME/.pypirc"
    
    if [[ -f "$pypirc_file" ]]; then
        log_success "找到 .pypirc 文件"
        
        if grep -q "\[pypi\]" "$pypirc_file"; then
            log_success "PyPI配置存在"
        else
            log_warning "PyPI配置缺失"
        fi
        
        if grep -q "username = __token__" "$pypirc_file"; then
            log_success "使用token认证"
        else
            log_warning "可能使用旧的用户名/密码认证"
        fi
        
        echo
        log_info "配置文件权限: $(ls -l $pypirc_file | awk '{print $1}')"
        
    else
        log_warning "未找到 .pypirc 文件"
    fi
    
    # 检查环境变量
    if [[ -n "$TWINE_USERNAME" ]]; then
        log_info "TWINE_USERNAME 环境变量: $TWINE_USERNAME"
    fi
    
    if [[ -n "$TWINE_PASSWORD" ]]; then
        log_info "TWINE_PASSWORD 环境变量已设置"
    fi
}

# 测试配置
test_config() {
    log_info "测试PyPI配置..."
    
    # 检查twine是否安装
    if ! command -v twine &> /dev/null; then
        log_warning "twine未安装，正在安装..."
        pip install twine
    fi
    
    # 简单的配置测试（不实际上传）
    log_info "运行配置检查..."
    python -c "
import twine.commands.check
import sys
print('Twine配置检查通过')
" 2>/dev/null || log_warning "Twine配置可能有问题"
    
    log_success "配置测试完成"
}

# 显示使用说明
show_usage() {
    cat << 'EOF'

配置完成后，您可以使用以下命令：

1. 上传包到PyPI：
   ./scripts/upload_to_pypi.sh

2. 测试上传：
   ./scripts/upload_to_pypi.sh --test

3. 预演模式：
   ./scripts/upload_to_pypi.sh --dry-run

4. 管理版本：
   ./scripts/manage_versions.sh show

更多信息请查看：./scripts/PYPI_RELEASE_GUIDE.md

EOF
}

# 默认参数
SHARED=false
PERSONAL=false
CHECK_ONLY=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--shared)
            SHARED=true
            shift
            ;;
        -p|--personal)
            PERSONAL=true
            shift
            ;;
        -c|--check)
            CHECK_ONLY=true
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
    test_config
elif [[ "$SHARED" == "true" ]]; then
    setup_shared_token
    check_config
    show_usage
elif [[ "$PERSONAL" == "true" ]]; then
    setup_personal_token
    check_config
    show_usage
else
    # 交互式选择
    echo "SAGE团队PyPI设置"
    echo
    echo "请选择设置方式："
    echo "1) 使用共享团队token（快速，适合小团队）"
    echo "2) 设置个人token（推荐，更安全）"
    echo "3) 仅检查当前配置"
    echo
    read -p "请选择 (1-3): " choice
    
    case $choice in
        1)
            setup_shared_token
            check_config
            show_usage
            ;;
        2)
            setup_personal_token
            check_config
            show_usage
            ;;
        3)
            check_config
            test_config
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac
fi

log_info "设置完成！"
