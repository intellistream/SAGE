#!/bin/bash

# SAGE Python工具接口
# 为bash脚本提供Python工具的接口函数

# 获取Python helper的路径 (内部工具，不对用户直接暴露)
PYTHON_HELPER="$PROJECT_ROOT/packages/sage-tools/src/sage/tools/internal/_quickstart_helper.py"

# 检查Python helper是否存在
check_python_helper() {
    if [ ! -f "$PYTHON_HELPER" ]; then
        echo "❌ Python助手不存在: $PYTHON_HELPER"
        echo "   请确保已正确克隆项目或安装sage-common包"
        return 1
    fi
    return 0
}

# Python工具接口函数
py_check_system() {
    local result=$(python "$PYTHON_HELPER" check-system 2>/dev/null)
    echo "$result"
    if [[ "$result" == SUCCESS:* ]]; then
        return 0
    else
        return 1
    fi
}

py_list_conda_envs() {
    python "$PYTHON_HELPER" list-conda-envs 2>/dev/null
}

py_check_conda_env() {
    local env_name="$1"
    local result=$(python "$PYTHON_HELPER" check-conda-env "$env_name" 2>/dev/null)
    if [ "$result" = "EXISTS" ]; then
        return 0
    else
        return 1
    fi
}

py_create_conda_env() {
    local env_name="$1"
    local python_version="${2:-3.11}"
    local result=$(python "$PYTHON_HELPER" create-conda-env "$env_name" "$python_version" 2>&1)
    echo "$result"
    if [[ "$result" == SUCCESS:* ]]; then
        return 0
    else
        return 1
    fi
}

py_install_requirements() {
    local project_root="$1"
    local result=$(python "$PYTHON_HELPER" install-requirements "$project_root" 2>&1)
    echo "$result"
    if [[ "$result" == SUCCESS:* ]]; then
        return 0
    else
        return 1
    fi
}

py_test_installation() {
    local result=$(python "$PYTHON_HELPER" test-installation 2>&1)
    echo "$result"
    if [[ "$result" == SUCCESS:* ]]; then
        return 0
    else
        return 1
    fi
}

py_get_system_info() {
    python "$PYTHON_HELPER" get-system-info 2>/dev/null
}

# 兼容性函数 - 如果Python工具不可用，回退到原始bash函数
safe_print_header() {
    echo -e "\n\033[0;35m================================\033[0m"
    echo -e "\033[0;35m$1\033[0m"
    echo -e "\033[0;35m================================\033[0m\n"
}

safe_print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

safe_print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

safe_print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

safe_print_status() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

# 兼容性包装函数
print_header() {
    safe_print_header "$1"
}

print_success() {
    safe_print_success "$1"
}

print_error() {
    safe_print_error "$1"
}

print_warning() {
    safe_print_warning "$1"
}

print_status() {
    safe_print_status "$1"
}
