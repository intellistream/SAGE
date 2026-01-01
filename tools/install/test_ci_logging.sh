#!/bin/bash
# 测试 CI 环境下的日志输出

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 加载日志工具
source "$SCRIPT_DIR/display_tools/logging.sh"
source "$SCRIPT_DIR/display_tools/progress_bar.sh"

echo "=========================================="
echo "测试 1: 交互环境（默认）"
echo "=========================================="
unset CI GITHUB_ACTIONS CONTINUOUS_INTEGRATION

echo "Testing start_spinner..."
start_spinner "测试安装"
sleep 2
stop_spinner
echo "完成"

echo ""
echo "Testing show_spinner..."
for i in {1..10}; do
    show_spinner "处理中 $i/10"
    sleep 0.2
done
stop_spinner
echo "完成"

echo ""
echo "Testing show_progress_bar..."
for i in {1..10}; do
    show_progress_bar $i 10 "安装进度"
    sleep 0.2
done
finish_progress_bar

echo ""
echo "=========================================="
echo "测试 2: CI 环境"
echo "=========================================="
export CI=true

echo "Testing start_spinner in CI..."
start_spinner "测试安装"
sleep 1
stop_spinner
echo "完成"

echo ""
echo "Testing show_spinner in CI..."
for i in {1..10}; do
    show_spinner "处理中 $i/10"
    sleep 0.1
done
stop_spinner
echo "完成"

echo ""
echo "Testing show_progress_bar in CI..."
for i in {1..10}; do
    show_progress_bar $i 10 "安装进度"
    sleep 0.1
done
finish_progress_bar

echo ""
echo "=========================================="
echo "测试完成！"
echo "=========================================="
echo ""
echo "CI 环境下应该看到："
echo "  - start_spinner: 仅一行 '测试安装...'"
echo "  - show_spinner: 无输出"
echo "  - show_progress_bar: 仅在 0%, 10%, 20%, ... 100% 输出"
echo ""
echo "交互环境下应该看到："
echo "  - start_spinner: 旋转动画"
echo "  - show_spinner: 旋转动画"
echo "  - show_progress_bar: 覆盖式进度条"
