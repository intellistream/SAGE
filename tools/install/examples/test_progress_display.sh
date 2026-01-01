#!/usr/bin/env bash
# 测试脚本 - 验证改进后的 pip 安装进度显示

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 加载必要的工具
source "$SCRIPT_DIR/display_tools/colors.sh"
source "$SCRIPT_DIR/display_tools/logging.sh"

echo "=========================================="
echo "测试 pip 安装进度显示改进"
echo "=========================================="
echo ""

# 测试1: 安装一个小包（快速）
echo "${BLUE}[测试 1]${NC} 安装小包（requests）"
echo "预期: 显示文件数量、大小和下载速度"
echo ""
log_pip_install_with_verbose_progress "TEST" "PHASE1" \
    "pip install --no-cache-dir --force-reinstall requests"

echo ""
echo "=========================================="
echo ""

# 测试2: 安装一个有依赖的包
echo "${BLUE}[测试 2]${NC} 安装有依赖的包（pandas）"
echo "预期: 显示多个文件的下载进度和速度统计"
echo ""
log_pip_install_with_verbose_progress "TEST" "PHASE2" \
    "pip install --no-cache-dir --force-reinstall pandas==2.0.0"

echo ""
echo "=========================================="
echo ""

echo "${GREEN}✓${NC} 测试完成！"
echo ""
echo "改进内容："
echo "  1. 显示每个文件的大小（MB/GB/kB）"
echo "  2. 实时显示下载速度（MB/s）"
echo "  3. 每60秒显示网络性能评估（慢速/正常/快速）"
echo "  4. 完成后显示总体统计信息"
echo "  5. 网络慢时给出优化建议"
