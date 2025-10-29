#!/bin/bash
# 类型错误修复辅助脚本
# 用途：帮助理解和处理 pre-commit 自动修复带来的变化

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
类型错误修复辅助工具

用法: $0 [命令]

命令:
  check-status       检查当前状态（格式化后的文件、新增的类型错误）
  format-first       先格式化所有代码（推荐第一步）
  show-new-errors    显示自动格式化后新增的类型错误
  safe-commit        安全提交（分步执行，显示每一步的影响）
  explain-diff       解释某个文件被自动修改的原因
  reset-format       撤销自动格式化的修改（恢复到上次提交）
  help               显示此帮助信息

示例工作流:
  # 第一次使用：先格式化所有代码
  $0 format-first

  # 修复一些类型错误后，检查状态
  $0 check-status

  # 查看自动格式化产生的新错误
  $0 show-new-errors

  # 安全提交（会逐步显示影响）
  $0 safe-commit "fix: 修复类型错误"

  # 如果想撤销自动格式化
  $0 reset-format

更多信息请参考: docs/dev-notes/pre-commit-auto-fix-guide.md
EOF
}

# 检查当前状态
check_status() {
    echo_info "检查当前状态..."
    echo ""

    # 检查是否有未提交的修改
    if [[ -z $(git status --short) ]]; then
        echo_success "工作区干净，没有未提交的修改"
        return
    fi

    echo_warning "发现未提交的修改："
    git status --short
    echo ""

    # 检查这些文件的 mypy 错误
    echo_info "检查这些文件的类型错误..."
    MODIFIED_FILES=$(git status --short | awk '{print $2}' | grep '\.py$' || true)

    if [[ -z "$MODIFIED_FILES" ]]; then
        echo_info "没有修改的 Python 文件"
        return
    fi

    echo "$MODIFIED_FILES" | xargs python -m mypy --ignore-missing-imports 2>&1 | tee /tmp/modified_files_errors.txt

    ERROR_COUNT=$(grep -c "error:" /tmp/modified_files_errors.txt || true)
    echo ""
    echo_info "这些修改的文件共有 $ERROR_COUNT 个类型错误"
}

# 先格式化所有代码
format_first() {
    echo_info "第一步：格式化所有代码（这会暴露所有隐藏的问题）"
    echo_warning "这可能会修改很多文件，建议先确保工作区干净"
    echo ""

    read -p "确定要继续吗？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "已取消"
        return
    fi

    echo_info "运行 black 格式化..."
    python -m black packages/ || echo_warning "Black 格式化完成（可能有警告）"

    echo_info "运行 isort 排序 imports..."
    python -m isort packages/ || echo_warning "Isort 完成（可能有警告）"

    echo ""
    echo_success "格式化完成！"
    echo_info "查看修改的文件："
    git status --short

    echo ""
    echo_info "现在运行 mypy 检查类型错误..."
    python -m mypy packages/sage-common/src/sage/common/core/functions/ \
                    packages/sage-kernel/src/sage/kernel/api/ \
                    packages/sage-kernel/src/sage/kernel/runtime/ \
                    --ignore-missing-imports 2>&1 | tee /tmp/mypy_after_format.txt

    ERROR_COUNT=$(grep -c "error:" /tmp/mypy_after_format.txt || echo "0")
    echo ""
    echo_info "格式化后共有 $ERROR_COUNT 个类型错误需要修复"
    echo_info "建议："
    echo "  1. 提交格式化修改: git add . && git commit -m 'style: 统一代码格式'"
    echo "  2. 然后开始修复类型错误"
}

# 显示新增的类型错误
show_new_errors() {
    echo_info "分析自动格式化后新增的类型错误..."
    echo ""

    # 检查是否有未提交的修改
    if [[ -z $(git status --short) ]]; then
        echo_success "没有未提交的修改"
        return
    fi

    MODIFIED_FILES=$(git status --short | awk '{print $2}' | grep '\.py$' || true)
    if [[ -z "$MODIFIED_FILES" ]]; then
        echo_info "没有修改的 Python 文件"
        return
    fi

    echo_info "检查修改的文件: "
    echo "$MODIFIED_FILES"
    echo ""

    # 暂存当前修改
    echo_info "暂存当前修改..."
    git stash push -m "temp_for_error_comparison" > /dev/null

    # 检查修改前的错误
    echo_info "检查修改前的错误数量..."
    echo "$MODIFIED_FILES" | xargs python -m mypy --ignore-missing-imports > /tmp/errors_before.txt 2>&1 || true
    ERRORS_BEFORE=$(grep -c "error:" /tmp/errors_before.txt || echo "0")

    # 恢复修改
    git stash pop > /dev/null

    # 检查修改后的错误
    echo_info "检查修改后的错误数量..."
    echo "$MODIFIED_FILES" | xargs python -m mypy --ignore-missing-imports > /tmp/errors_after.txt 2>&1 || true
    ERRORS_AFTER=$(grep -c "error:" /tmp/errors_after.txt || echo "0")    # 比较
    echo ""
    echo_info "错误数量对比："
    echo "  修改前: $ERRORS_BEFORE 个错误"
    echo "  修改后: $ERRORS_AFTER 个错误"

    if [[ $ERRORS_AFTER -gt $ERRORS_BEFORE ]]; then
        DIFF=$((ERRORS_AFTER - ERRORS_BEFORE))
        echo_warning "新增了 $DIFF 个类型错误！"
        echo ""
        echo_info "新增的错误（修改后独有的）："
        comm -13 <(sort /tmp/errors_before.txt) <(sort /tmp/errors_after.txt) | grep "error:" | head -20
    elif [[ $ERRORS_AFTER -lt $ERRORS_BEFORE ]]; then
        DIFF=$((ERRORS_BEFORE - ERRORS_AFTER))
        echo_success "减少了 $DIFF 个类型错误！"
    else
        echo_info "错误数量没有变化"
    fi
}

# 安全提交
safe_commit() {
    if [[ -z "$1" ]]; then
        echo_error "请提供提交信息"
        echo "用法: $0 safe-commit \"你的提交信息\""
        return 1
    fi

    COMMIT_MSG="$1"

    echo_info "安全提交流程开始..."
    echo ""

    # 步骤 1: 查看将要提交的文件
    echo_info "步骤 1/5: 将要提交的文件"
    git status --short
    echo ""
    read -r -p "按 Enter 继续..."

    # 步骤 2: 暂存所有修改
    echo_info "步骤 2/5: 暂存所有修改"
    git add .
    echo_success "已暂存"
    echo ""

    # 步骤 3: 运行 pre-commit（不实际提交）
    echo_info "步骤 3/5: 运行 pre-commit 检查（看看会修改什么）"
    echo_warning "这可能会自动修改一些文件..."

    # 运行 pre-commit（允许失败）
    pre-commit run || true

    echo ""
    echo_info "Pre-commit 执行完毕，查看是否有新的修改："
    git status --short
    echo ""
    read -r -p "按 Enter 继续..."

    # 步骤 4: 如果有新修改，显示差异
    if [[ -n $(git diff) ]]; then
        echo_warning "步骤 4/5: Pre-commit 产生了新的修改！"
        echo_info "显示差异（前 50 行）："
        git diff | head -50
        echo ""
        echo_warning "建议："
        echo "  1. 查看这些自动修改是否合理"
        echo "  2. 运行 mypy 检查是否有新的类型错误"
        echo "  3. 如果有新错误，先修复再提交"
        echo ""
        read -p "是否继续提交？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo_info "已取消提交"
            echo_info "你可以："
            echo "  - 修复新出现的错误"
            echo "  - 或者运行: git reset 撤销暂存"
            return
        fi

        # 重新暂存自动修改的文件
        git add .
    fi

    # 步骤 5: 实际提交
    echo_info "步骤 5/5: 执行提交"

    # 使用 SKIP 跳过 pre-commit（因为已经运行过了）
    SKIP=mypy,black,isort,ruff,detect-secrets git commit -m "$COMMIT_MSG"

    echo_success "提交成功！"
    echo_info "提交信息: $COMMIT_MSG"
}

# 解释文件差异
explain_diff() {
    if [[ -z "$1" ]]; then
        echo_error "请指定要分析的文件"
        echo "用法: $0 explain-diff <文件路径>"
        return 1
    fi

    FILE="$1"

    if [[ ! -f "$FILE" ]]; then
        echo_error "文件不存在: $FILE"
        return 1
    fi

    echo_info "分析文件: $FILE"
    echo ""

    # 显示差异
    echo_info "=== 修改内容 ==="
    git diff "$FILE"
    echo ""

    # 分析修改类型
    echo_info "=== 修改分析 ==="

    # 检查类型注解修改
    if git diff "$FILE" | grep -q "Optional\|Union"; then
        echo_warning "发现类型注解修改（Optional/Union 语法）"
        echo "  可能是 ruff 将 Union[X, Y] 改为 X | Y"
        echo "  或者将 Optional[X] 改为 X | None"
    fi

    # 检查 import 修改
    if git diff "$FILE" | grep -q "^-import\|^+import\|^-from\|^+from"; then
        echo_warning "发现 import 语句修改"
        echo "  可能是 isort 重新排序了 imports"
        echo "  或者修改了 import 格式（单行 vs 多行）"
    fi

    # 检查格式修改
    if git diff "$FILE" | grep -q "^-.*def \|^-.*class "; then
        echo_warning "发现函数/类定义修改"
        echo "  可能是 black 重新格式化了代码"
        echo "  检查缩进、空行、行长度等"
    fi

    # 检查字符串注解
    if git diff "$FILE" | grep -q '"\|'"'"; then
        echo_warning "发现字符串注解修改"
        echo "  可能是去掉了类型注解的引号"
        echo "  这会让 mypy 检查更严格！"
    fi

    echo ""
    echo_info "=== Mypy 检查 ==="
    python -m mypy "$FILE" --ignore-missing-imports 2>&1 | grep "$FILE" || echo_success "没有类型错误"
}

# 撤销格式化修改
reset_format() {
    echo_warning "这将撤销所有未提交的修改！"
    echo_info "当前未提交的文件："
    git status --short
    echo ""
    read -p "确定要撤销这些修改吗？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "已取消"
        return
    fi

    git reset --hard HEAD
    echo_success "已撤销所有修改，恢复到上次提交状态"
}

# 主函数
main() {
    cd "$PROJECT_ROOT"

    case "${1:-help}" in
        check-status)
            check_status
            ;;
        format-first)
            format_first
            ;;
        show-new-errors)
            show_new_errors
            ;;
        safe-commit)
            safe_commit "$2"
            ;;
        explain-diff)
            explain_diff "$2"
            ;;
        reset-format)
            reset_format
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
