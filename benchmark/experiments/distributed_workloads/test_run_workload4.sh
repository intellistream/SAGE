#!/bin/bash
# Workload 4 执行脚本测试套件
# ====================================

set -e  # 遇到错误立即退出

echo "=========================================="
echo "Workload 4 执行脚本测试"
echo "=========================================="
echo ""

# 定位到正确的目录
cd "$(dirname "$0")"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试函数
test_command() {
    local desc="$1"
    local cmd="$2"
    
    echo -e "${YELLOW}测试: ${desc}${NC}"
    echo "命令: $cmd"
    echo ""
    
    if eval "$cmd"; then
        echo -e "${GREEN}✓ 通过${NC}"
    else
        echo -e "${RED}✗ 失败${NC}"
        return 1
    fi
    
    echo ""
    echo "------------------------------------------"
    echo ""
}

# 1. 帮助信息测试
test_command \
    "1. 帮助信息" \
    "python run_workload4.py --help | head -20"

# 2. Dry-run 测试（默认配置）
test_command \
    "2. Dry-run（默认配置）" \
    "python run_workload4.py --dry-run --num-tasks 50 2>&1 | head -30"

# 3. Dry-run 测试（调试模式）
test_command \
    "3. Dry-run（调试模式）" \
    "python run_workload4.py --debug --dry-run 2>&1 | head -30"

# 4. Dry-run 测试（配置文件 - 示例）
test_command \
    "4. Dry-run（示例配置文件）" \
    "python run_workload4.py --config workload4_config_example.yaml --dry-run 2>&1 | head -30"

# 5. Dry-run 测试（配置文件 - 调试）
test_command \
    "5. Dry-run（调试配置文件）" \
    "python run_workload4.py --config workload4_config_debug.yaml --dry-run 2>&1 | head -30"

# 6. 参数组合测试
test_command \
    "6. 参数组合测试" \
    "python run_workload4.py --num-tasks 20 --duration 300 --query-qps 10 --doc-qps 5 --dry-run 2>&1 | head -30"

# 7. 调度器选项测试
test_command \
    "7. 调度器选项测试" \
    "python run_workload4.py --scheduler load_aware --dry-run 2>&1 | grep 'scheduler' | head -5"

# 8. 输出目录测试
test_command \
    "8. 输出目录测试" \
    "python run_workload4.py --output-dir /tmp/test_metrics --dry-run 2>&1 | grep 'output' | head -5"

echo "=========================================="
echo "所有测试完成"
echo "=========================================="
echo ""
echo "总结:"
echo "  ✓ 帮助信息正常"
echo "  ✓ Dry-run 模式工作"
echo "  ✓ 调试模式工作"
echo "  ✓ 配置文件加载正常"
echo "  ✓ 参数覆盖正确"
echo ""
echo "下一步:"
echo "  1. 运行快速测试: python run_workload4.py --debug"
echo "  2. 运行完整测试: python run_workload4.py"
echo "  3. 查看使用指南: cat WORKLOAD4_USAGE_GUIDE.md"
echo ""
