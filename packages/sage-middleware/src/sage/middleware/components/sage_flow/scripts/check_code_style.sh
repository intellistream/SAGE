#!/bin/bash

# SAGE Flow 代码风格检查脚本
# 使用 cpplint 检查 Google C++ 风格指南合规性

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

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_FILE="$PROJECT_ROOT/code_style_report.txt"

# 检查 cpplint 是否安装
check_cpplint() {
    log_info "检查 cpplint 工具..."

    if ! command -v cpplint &> /dev/null; then
        log_error "cpplint 未安装或不在 PATH 中"
        log_info "请安装 cpplint: pip install cpplint"
        echo "ERROR: cpplint 未安装" >> "$REPORT_FILE"
        return 1
    fi

    local version=$(cpplint --version 2>&1 | head -n1 || echo "版本未知")
    log_success "cpplint 已安装: $version"
    echo "SUCCESS: cpplint 已安装: $version" >> "$REPORT_FILE"
    return 0
}

# 运行代码风格检查
run_style_check() {
    log_info "运行代码风格检查..."

    # 创建报告文件
    cat > "$REPORT_FILE" << EOF
SAGE Flow 代码风格检查报告
========================
生成时间: $(date)
项目根目录: $PROJECT_ROOT

EOF

    # 查找所有 C++ 文件
    local cpp_files=($(find "$PROJECT_ROOT" -name "*.cpp" -o -name "*.hpp" -o -name "*.h" | grep -v build/ | grep -v _deps/))

    echo "检查的文件数量: ${#cpp_files[@]}" >> "$REPORT_FILE"
    echo "文件列表:" >> "$REPORT_FILE"
    printf '  %s\n' "${cpp_files[@]}" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"

    log_info "找到 ${#cpp_files[@]} 个 C++ 文件待检查"

    # 运行 cpplint
    local start_time=$(date +%s)

    echo "代码风格检查结果:" >> "$REPORT_FILE"
    echo "==================" >> "$REPORT_FILE"

    local error_count=0
    local total_files=${#cpp_files[@]}

    for file in "${cpp_files[@]}"; do
        log_info "检查文件: $(basename "$file")"

        # 运行 cpplint 并捕获输出
        local output=$(cpplint "$file" 2>&1 || true)
        local file_error_count=$(echo "$output" | grep -c "error\|warning" || echo "0")

        if [[ -n "$output" ]]; then
            echo "文件: $file" >> "$REPORT_FILE"
            echo "错误数量: $file_error_count" >> "$REPORT_FILE"
            echo "$output" >> "$REPORT_FILE"
            echo "---" >> "$REPORT_FILE"

            error_count=$((error_count + file_error_count))
            log_warning "$(basename "$file"): $file_error_count 个问题"
        else
            log_success "$(basename "$file"): 无问题"
        fi
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "" >> "$REPORT_FILE"
    echo "检查总结:" >> "$REPORT_FILE"
    echo "==========" >> "$REPORT_FILE"
    echo "总文件数: $total_files" >> "$REPORT_FILE"
    echo "总错误数: $error_count" >> "$REPORT_FILE"
    echo "检查耗时: ${duration}秒" >> "$REPORT_FILE"
    echo "平均每文件错误数: $((error_count / total_files))" >> "$REPORT_FILE"

    log_info "检查完成，耗时: ${duration}秒"
    log_info "总错误数: $error_count"

    if [[ $error_count -gt 0 ]]; then
        log_warning "发现 $error_count 个代码风格问题"
        return 1
    else
        log_success "所有文件符合代码风格要求"
        return 0
    fi
}

# 生成问题统计
generate_statistics() {
    log_info "生成问题统计..."

    if [[ ! -f "$REPORT_FILE" ]]; then
        log_error "报告文件不存在"
        return 1
    fi

    echo "" >> "$REPORT_FILE"
    echo "问题类型统计:" >> "$REPORT_FILE"
    echo "==============" >> "$REPORT_FILE"

    # 统计不同类型的问题
    local categories=(
        "whitespace/line_length:行长度超过80字符"
        "whitespace/indent:缩进问题"
        "whitespace/end_of_line:行尾空格"
        "whitespace/comments:注释格式"
        "build/include_subdir:包含目录命名"
        "build/include_order:包含顺序"
        "readability/casting:C风格转换"
        "build/namespaces:命名空间使用"
        "whitespace/ending_newline:文件末尾换行"
        "legal/copyright:版权信息"
    )

    for category_info in "${categories[@]}"; do
        local category="${category_info%%:*}"
        local desc="${category_info#*:}"

        local count=$(grep -c "$category" "$REPORT_FILE" || echo "0")
        if [[ $count -gt 0 ]]; then
            echo "  $desc: $count" >> "$REPORT_FILE"
        fi
    done

    log_success "统计信息已添加到报告"
}

# 主函数
main() {
    log_info "开始 SAGE Flow 代码风格检查..."
    log_info "报告文件: $REPORT_FILE"

    # 检查依赖
    check_cpplint || exit 1

    # 运行检查
    if run_style_check; then
        log_success "代码风格检查通过"
    else
        log_warning "代码风格检查发现问题"
        generate_statistics
    fi

    log_info "详细报告请查看: $REPORT_FILE"
}

# 执行主函数
main "$@"