#!/bin/bash
# SAGE Examples 测试运行脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SAGE_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$SAGE_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${BLUE}SAGE Examples 测试工具${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -a, --analyze           只分析示例，不运行测试"
    echo "  -q, --quick             只运行快速测试"
    echo "  -c, --category CAT      指定测试类别 (tutorials,rag,memory,service,video)"
    echo "  -t, --timeout SEC       设置测试超时时间（秒）"
    echo "  -o, --output FILE       保存测试结果到文件"
    echo "  -v, --verbose           详细输出"
    echo "  --pytest               使用 pytest 运行（推荐）"
    echo "  --standalone            使用独立脚本运行"
    echo ""
    echo "示例:"
    echo "  $0 --quick                    # 运行所有快速测试"
    echo "  $0 --category tutorials       # 只测试教程示例"
    echo "  $0 --pytest --quick          # 用 pytest 运行快速测试"
    echo "  $0 --analyze                  # 只分析示例结构"
}

# 默认参数
ANALYZE_ONLY=false
QUICK_ONLY=false
CATEGORY=""
TIMEOUT=60
OUTPUT_FILE=""
VERBOSE=false
USE_PYTEST=true
STANDALONE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -a|--analyze)
            ANALYZE_ONLY=true
            shift
            ;;
        -q|--quick)
            QUICK_ONLY=true
            shift
            ;;
        -c|--category)
            CATEGORY="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --pytest)
            USE_PYTEST=true
            STANDALONE=false
            shift
            ;;
        --standalone)
            USE_PYTEST=false
            STANDALONE=true
            shift
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 检查环境
check_environment() {
    echo -e "${BLUE}🔧 检查环境...${NC}"
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 未找到${NC}"
        exit 1
    fi
    
    # 检查必要的包
    echo "检查依赖包..."
    python3 -c "import typer, rich" 2>/dev/null || {
        echo -e "${RED}❌ typer 或 rich 未安装。请运行: pip install -e packages/sage-tools[cli]${NC}"
        exit 1
    }
    
    if $USE_PYTEST; then
        python3 -c "import pytest" 2>/dev/null || {
            echo -e "${RED}❌ pytest 未安装。请运行: pip install -e packages/sage-tools[dev]${NC}"
            exit 1
        }
        python3 -c "import pytest_timeout" 2>/dev/null || {
            echo -e "${RED}❌ pytest-timeout 未安装。请运行: pip install -e packages/sage-tools[dev]${NC}"
            exit 1
        }
    fi
    
    echo -e "${GREEN}✅ 环境检查完成${NC}"
}

# 运行分析
run_analysis() {
    echo -e "${BLUE}📊 分析 Examples 目录...${NC}"
    python3 tools/tests/test_examples.py analyze
}

# 使用 pytest 运行测试
run_pytest_tests() {
    echo -e "${BLUE}🚀 使用 pytest 运行测试...${NC}"
    
    local pytest_args=("-v")
    
    # 根据配置添加标记
    if $QUICK_ONLY; then
        if [[ -n "$CATEGORY" ]]; then
            pytest_args+=("-k" "quick_examples and $CATEGORY")
        else
            pytest_args+=("-m" "quick_examples")
        fi
    elif [[ -n "$CATEGORY" ]]; then
        pytest_args+=("-k" "$CATEGORY")
    fi
    
    if $VERBOSE; then
        pytest_args+=("-s")
    fi
    
    # 运行测试
    cd tools/tests
    python3 -m pytest "${pytest_args[@]}" test_examples_pytest.py
}

# 使用独立脚本运行测试
run_standalone_tests() {
    echo -e "${BLUE}🚀 使用独立脚本运行测试...${NC}"
    
    local cmd_args=()
    
    if $QUICK_ONLY; then
        cmd_args+=("--quick")
    fi
    
    if [[ -n "$CATEGORY" ]]; then
        cmd_args+=("--category" "$CATEGORY")
    fi
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        cmd_args+=("--output" "$OUTPUT_FILE")
    fi
    
    cmd_args+=("--timeout" "$TIMEOUT")
    
    python3 tools/tests/test_examples.py test "${cmd_args[@]}"
}

# 显示测试统计
show_statistics() {
    echo -e "${BLUE}📈 生成测试报告...${NC}"
    
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo -e "${GREEN}测试结果已保存到: $OUTPUT_FILE${NC}"
        
        # 如果有 jq，显示简单统计
        if command -v jq &> /dev/null; then
            echo ""
            echo -e "${BLUE}测试统计:${NC}"
            jq '.statistics' "$OUTPUT_FILE" 2>/dev/null || echo "统计信息解析失败"
        fi
    fi
}

# 主函数
main() {
    echo -e "${GREEN}🔥 SAGE Examples 测试工具${NC}"
    echo "==============================="
    
    check_environment
    
    if $ANALYZE_ONLY; then
        run_analysis
        exit 0
    fi
    
    echo ""
    echo -e "${BLUE}配置:${NC}"
    echo "  测试模式: $(if $USE_PYTEST; then echo "pytest"; else echo "独立脚本"; fi)"
    echo "  快速模式: $(if $QUICK_ONLY; then echo "是"; else echo "否"; fi)"
    echo "  类别: ${CATEGORY:-"全部"}"
    echo "  超时: ${TIMEOUT}秒"
    if [[ -n "$OUTPUT_FILE" ]]; then
        echo "  输出文件: $OUTPUT_FILE"
    fi
    echo ""
    
    # 运行测试
    if $USE_PYTEST; then
        run_pytest_tests
    else
        run_standalone_tests
    fi
    
    # 显示统计
    if [[ -n "$OUTPUT_FILE" ]] && $STANDALONE; then
        show_statistics
    fi
    
    echo ""
    echo -e "${GREEN}✅ 测试完成!${NC}"
}

# 错误处理
trap 'echo -e "${RED}❌ 测试被中断${NC}"; exit 1' INT TERM

# 运行主函数
main "$@"