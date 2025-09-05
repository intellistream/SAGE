#!/bin/bash

# SAGE Flow 综合代码质量检查脚本
# 结合多种静态分析工具进行全面的质量检查

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
REPORT_DIR="$PROJECT_ROOT/reports"
QUALITY_REPORT="$REPORT_DIR/code_quality_report_$(date +%Y%m%d_%H%M%S).txt"

# 创建报告目录
mkdir -p "$REPORT_DIR"

# 检查工具是否安装
check_tools() {
    log_info "检查代码质量检查工具..."

    local tools=("cpplint" "clang-tidy" "cppcheck" "include-what-you-use")
    local missing_tools=()

    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            local version=$("$tool" --version 2>&1 | head -n1 || echo "版本未知")
            log_success "$tool 已安装: $version"
        else
            missing_tools+=("$tool")
            log_warning "$tool 未安装"
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_info "建议安装以下工具以获得最佳检查效果:"
        for tool in "${missing_tools[@]}"; do
            case $tool in
                "cpplint")
                    echo "  pip install cpplint"
                    ;;
                "clang-tidy")
                    echo "  apt install clang-tidy (Ubuntu/Debian)"
                    ;;
                "cppcheck")
                    echo "  apt install cppcheck (Ubuntu/Debian)"
                    ;;
                "include-what-you-use")
                    echo "  apt install iwyu (Ubuntu/Debian)"
                    ;;
            esac
        done
    fi
}

# 运行 cpplint 检查
run_cpplint() {
    log_info "运行 cpplint 代码风格检查..."

    local cpp_files=($(find "$PROJECT_ROOT" -name "*.cpp" -o -name "*.hpp" -o -name "*.h" | grep -v build/ | grep -v _deps/))

    if [[ ${#cpp_files[@]} -eq 0 ]]; then
        log_warning "未找到 C++ 文件"
        return 0
    fi

    local error_count=0
    local start_time=$(date +%s)

    echo "=== cpplint 结果 ===" >> "$QUALITY_REPORT"

    for file in "${cpp_files[@]}"; do
        log_info "检查: $(basename "$file")"

        if command -v cpplint &> /dev/null; then
            local output=$(cpplint --quiet "$file" 2>&1 || true)
            local file_errors=$(echo "$output" | grep -c "error\|warning" || echo "0")

            if [[ $file_errors -gt 0 ]]; then
                echo "文件: $file ($file_errors 个问题)" >> "$QUALITY_REPORT"
                echo "$output" >> "$QUALITY_REPORT"
                echo "---" >> "$QUALITY_REPORT"
                error_count=$((error_count + file_errors))
            fi
        fi
    done

    local end_time=$(date +%s)
    echo "cpplint 检查完成: $error_count 个问题, 耗时 $((end_time - start_time)) 秒" >> "$QUALITY_REPORT"
    log_info "cpplint 完成: $error_count 个问题"
}

# 运行 clang-tidy 检查
run_clang_tidy() {
    log_info "运行 clang-tidy 静态分析..."

    local cpp_files=($(find "$PROJECT_ROOT" -name "*.cpp" | grep -v build/ | grep -v _deps/))

    if [[ ${#cpp_files[@]} -eq 0 ]]; then
        log_warning "未找到 C++ 源文件"
        return 0
    fi

    local error_count=0
    local start_time=$(date +%s)

    echo "=== clang-tidy 结果 ===" >> "$QUALITY_REPORT"

    for file in "${cpp_files[@]}"; do
        log_info "分析: $(basename "$file")"

        if command -v clang-tidy &> /dev/null && [[ -f ".clang-tidy" ]]; then
            local output=$(clang-tidy "$file" --quiet 2>&1 || true)
            local file_errors=$(echo "$output" | grep -c "error\|warning" || echo "0")

            if [[ $file_errors -gt 0 ]]; then
                echo "文件: $file ($file_errors 个问题)" >> "$QUALITY_REPORT"
                echo "$output" >> "$QUALITY_REPORT"
                echo "---" >> "$QUALITY_REPORT"
                error_count=$((error_count + file_errors))
            fi
        fi
    done

    local end_time=$(date +%s)
    echo "clang-tidy 分析完成: $error_count 个问题, 耗时 $((end_time - start_time)) 秒" >> "$QUALITY_REPORT"
    log_info "clang-tidy 完成: $error_count 个问题"
}

# 运行 cppcheck 检查
run_cppcheck() {
    log_info "运行 cppcheck 静态分析..."

    if ! command -v cppcheck &> /dev/null; then
        log_warning "cppcheck 未安装，跳过"
        return 0
    fi

    local start_time=$(date +%s)

    echo "=== cppcheck 结果 ===" >> "$QUALITY_REPORT"

    local output=$(cppcheck --enable=all --std=c++17 --language=c++ \
                          --suppress=missingIncludeSystem \
                          --suppress=unusedFunction \
                          --inline-suppr \
                          --xml \
                          "$PROJECT_ROOT/src" "$PROJECT_ROOT/include" 2>&1 || true)

    local error_count=$(echo "$output" | grep -c "<error" || echo "0")

    if [[ $error_count -gt 0 ]]; then
        echo "$output" >> "$QUALITY_REPORT"
    fi

    local end_time=$(date +%s)
    echo "cppcheck 分析完成: $error_count 个问题, 耗时 $((end_time - start_time)) 秒" >> "$QUALITY_REPORT"
    log_info "cppcheck 完成: $error_count 个问题"
}

# 检查内存泄漏风险
check_memory_leaks() {
    log_info "检查内存泄漏风险..."

    echo "=== 内存管理检查 ===" >> "$QUALITY_REPORT"

    local cpp_files=($(find "$PROJECT_ROOT" -name "*.cpp" -o -name "*.hpp" | grep -v build/ | grep -v _deps/))

    local raw_pointers=0
    local missing_deletes=0
    local new_without_delete=0

    for file in "${cpp_files[@]}"; do
        # 检查原始指针使用
        local ptr_count=$(grep -c "new \|delete \|malloc\|free" "$file" 2>/dev/null || echo "0")
        if [[ "$ptr_count" -gt 0 ]]; then
            echo "文件 $file 包含手动内存管理 ($ptr_count 处)" >> "$QUALITY_REPORT"
            raw_pointers=$((raw_pointers + ptr_count))
        fi

        # 检查 new 没有对应的 delete
        local new_count=$(grep -c "\bnew\b" "$file" 2>/dev/null || echo "0")
        local delete_count=$(grep -c "\bdelete\b" "$file" 2>/dev/null || echo "0")
        if [[ "$new_count" -gt "$delete_count" ]]; then
            echo "文件 $file 可能存在内存泄漏 (new: $new_count, delete: $delete_count)" >> "$QUALITY_REPORT"
            missing_deletes=$((missing_deletes + (new_count - delete_count)))
        fi
    done

    echo "内存管理统计:" >> "$QUALITY_REPORT"
    echo "  手动内存操作: $raw_pointers" >> "$QUALITY_REPORT"
    echo "  可能的内存泄漏: $missing_deletes" >> "$QUALITY_REPORT"

    log_info "内存检查完成: $raw_pointers 处手动内存操作, $missing_deletes 处可能的泄漏"
}

# 生成质量评分
generate_quality_score() {
    log_info "生成代码质量评分..."

    echo "=== 代码质量评分 ===" >> "$QUALITY_REPORT"

    # 计算各种指标的分数 (0-100)
    local style_score=100
    local static_analysis_score=100
    local memory_score=100

    # 基于检查结果调整分数
    if [[ -f "$QUALITY_REPORT" ]]; then
        local cpplint_errors=$(grep -c "cpplint.*问题" "$QUALITY_REPORT" 2>/dev/null || echo "0")
        local clang_errors=$(grep -c "clang-tidy.*问题" "$QUALITY_REPORT" 2>/dev/null || echo "0")
        local cppcheck_errors=$(grep -c "cppcheck.*问题" "$QUALITY_REPORT" 2>/dev/null || echo "0")
        local memory_issues=$(grep -c "内存泄漏\|手动内存" "$QUALITY_REPORT" 2>/dev/null || echo "0")

        # 扣分逻辑
        ((style_score -= cpplint_errors * 2))
        ((static_analysis_score -= clang_errors + cppcheck_errors))
        ((memory_score -= memory_issues * 5))

        # 确保分数不低于0
        ((style_score = style_score < 0 ? 0 : style_score))
        ((static_analysis_score = static_analysis_score < 0 ? 0 : static_analysis_score))
        ((memory_score = memory_score < 0 ? 0 : memory_score))
    fi

    local overall_score=$(((style_score + static_analysis_score + memory_score) / 3))

    echo "代码风格得分: $style_score/100" >> "$QUALITY_REPORT"
    echo "静态分析得分: $static_analysis_score/100" >> "$QUALITY_REPORT"
    echo "内存管理得分: $memory_score/100" >> "$QUALITY_REPORT"
    echo "综合质量得分: $overall_score/100" >> "$QUALITY_REPORT"

    # 评分等级
    if [[ $overall_score -ge 90 ]]; then
        echo "质量等级: A (优秀)" >> "$QUALITY_REPORT"
    elif [[ $overall_score -ge 80 ]]; then
        echo "质量等级: B (良好)" >> "$QUALITY_REPORT"
    elif [[ $overall_score -ge 70 ]]; then
        echo "质量等级: C (一般)" >> "$QUALITY_REPORT"
    elif [[ $overall_score -ge 60 ]]; then
        echo "质量等级: D (需改进)" >> "$QUALITY_REPORT"
    else
        echo "质量等级: F (严重问题)" >> "$QUALITY_REPORT"
    fi

    log_success "质量评分: $overall_score/100"
}

# 主函数
main() {
    log_info "开始 SAGE Flow 综合代码质量检查..."
    log_info "报告文件: $QUALITY_REPORT"

    # 创建报告文件
    cat > "$QUALITY_REPORT" << EOF
SAGE Flow 综合代码质量检查报告
===============================
生成时间: $(date)
项目根目录: $PROJECT_ROOT

EOF

    # 检查工具
    check_tools

    # 运行各种检查
    run_cpplint
    run_clang_tidy
    run_cppcheck
    check_memory_leaks

    # 生成评分
    generate_quality_score

    echo "" >> "$QUALITY_REPORT"
    echo "检查完成时间: $(date)" >> "$QUALITY_REPORT"

    log_success "代码质量检查完成"
    log_info "详细报告: $QUALITY_REPORT"

    # 返回适当的退出码
    local total_issues=$(grep -c "问题\|error\|warning\|泄漏" "$QUALITY_REPORT" || echo "0")
    if [[ $total_issues -gt 0 ]]; then
        log_warning "发现 $total_issues 个潜在问题"
        exit 1
    else
        log_success "代码质量检查通过"
        exit 0
    fi
}

# 执行主函数
main "$@"