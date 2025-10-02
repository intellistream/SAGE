#!/bin/bash

# SAGE Conda 服务条款修复脚本
# 解决新机器上初次使用 Conda 时的服务条款问题

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 引入日志模块
source "../lib/logging.sh"

print_header "🔧 Conda 服务条款修复工具"

main() {
    source ./conda_utils.sh
    accept_conda_tos
}

main "$@"

echo
print_success "🎉 修复完成！现在可以重新运行 SAGE 安装脚本了"
print_status "运行: ./quickstart.sh"
