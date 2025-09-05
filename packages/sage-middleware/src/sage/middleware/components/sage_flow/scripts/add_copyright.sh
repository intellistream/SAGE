#!/bin/bash

# SAGE Flow 批量添加版权信息脚本
# 为所有 C++ 文件添加标准的 Apache 2.0 版权声明

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# 日志函数
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

# 版权声明模板
readonly COPYRIGHT_HEADER="/*
 * Copyright 2024 SAGE Flow Team
 *
 * Licensed under the Apache License, Version 2.0 (the \"License\");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an \"AS IS\" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
"

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 检查文件是否已有版权信息
has_copyright() {
    local file="$1"
    # 检查文件开头是否包含版权相关关键词
    head -n 20 "$file" | grep -q -i "copyright\|license\|apache" || return 1
}

# 为文件添加版权信息
add_copyright_to_file() {
    local file="$1"

    if has_copyright "$file"; then
        log_info "文件 $file 已有版权信息，跳过"
        return 0
    fi

    log_info "为文件 $file 添加版权信息"

    # 创建临时文件
    local temp_file=$(mktemp)

    # 添加版权信息和原有内容
    echo "$COPYRIGHT_HEADER" > "$temp_file"
    echo "" >> "$temp_file"
    cat "$file" >> "$temp_file"

    # 替换原文件
    mv "$temp_file" "$file"

    log_success "已为 $file 添加版权信息"
}

# 主函数
main() {
    log_info "开始批量添加版权信息..."
    log_info "项目根目录: $PROJECT_ROOT"

    # 查找所有 C++ 文件
    local cpp_files=($(find "$PROJECT_ROOT/src" "$PROJECT_ROOT/include" \
        -name "*.cpp" -o -name "*.hpp" -o -name "*.h" | \
        grep -v build/ | grep -v _deps/))

    local total_files=${#cpp_files[@]}
    local processed_files=0

    log_info "找到 $total_files 个 C++ 文件待处理"

    for file in "${cpp_files[@]}"; do
        if add_copyright_to_file "$file"; then
            ((processed_files++))
        fi
    done

    log_success "处理完成: $processed_files / $total_files 个文件已添加版权信息"
}

# 执行主函数
main "$@"