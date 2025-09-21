#!/bin/bash
# Ray 测试快速运行脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🧪 Ray 测试快速运行脚本"
echo "================================"

# 默认参数
SKIP_RAY=false
SKIP_SLOW=false
VERBOSE=false
PARALLEL=false
TIMEOUT=120

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-ray)
            SKIP_RAY=true
            shift
            ;;
        --skip-slow)
            SKIP_SLOW=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel|-j)
            PARALLEL=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --skip-ray      跳过所有 Ray 相关测试"
            echo "  --skip-slow     跳过所有慢速测试"
            echo "  --verbose, -v   显示详细输出"
            echo "  --parallel, -j  并行运行测试"
            echo "  --timeout N     设置测试超时时间(秒)，默认120"
            echo "  --help, -h      显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --skip-ray               # 跳过Ray测试"
            echo "  $0 --skip-slow              # 跳过慢速测试"
            echo "  $0 --skip-ray --skip-slow   # 只运行快速的非Ray测试"
            echo "  $0 --verbose --parallel     # 详细输出并并行运行"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看可用选项"
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT/packages/sage-kernel"

# 构建 pytest 命令
PYTEST_CMD="/home/shuhao/miniconda3/envs/sage/bin/python3 -m pytest"
PYTEST_ARGS="-v --tb=short"

# 设置标记过滤器
MARKERS=""
if [[ "$SKIP_RAY" == "true" && "$SKIP_SLOW" == "true" ]]; then
    MARKERS="-m 'not ray and not slow'"
    echo "🏃 模式: 跳过Ray和慢速测试"
elif [[ "$SKIP_RAY" == "true" ]]; then
    MARKERS="-m 'not ray'"
    echo "⚡ 模式: 跳过Ray测试"
elif [[ "$SKIP_SLOW" == "true" ]]; then
    MARKERS="-m 'not slow'"
    echo "🚀 模式: 跳过慢速测试"
else
    echo "🔥 模式: 运行所有测试"
fi

# 添加详细输出
if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS -s -v"
    echo "📝 启用详细输出"
else
    PYTEST_ARGS="$PYTEST_ARGS --tb=line"
    echo "📝 使用简洁输出模式"
fi

# 添加并行支持
if [[ "$PARALLEL" == "true" ]]; then
    # 检查是否安装了 pytest-xdist
    if python -c "import pytest_xdist" 2>/dev/null; then
        PYTEST_ARGS="$PYTEST_ARGS -n auto"
        echo "🔄 启用并行执行"
    else
        echo "⚠️  pytest-xdist 未安装，无法并行执行"
    fi
fi

# 添加超时
PYTEST_ARGS="$PYTEST_ARGS --timeout=$TIMEOUT"
echo "⏰ 测试超时: ${TIMEOUT}秒"

# 构建完整命令
FULL_CMD="timeout 300 $PYTEST_CMD $PYTEST_ARGS $MARKERS tests/"

echo ""
echo "🧪 执行命令:"
echo "$FULL_CMD"
echo ""

# 执行测试
eval $FULL_CMD

exit_code=$?
if [[ $exit_code -eq 0 ]]; then
    echo ""
    echo "✅ 所有测试通过!"
elif [[ $exit_code -eq 124 ]]; then
    echo ""
    echo "⏰ 测试运行超时 (300秒)"
else
    echo ""
    echo "❌ 测试失败 (退出码: $exit_code)"
fi

exit $exit_code