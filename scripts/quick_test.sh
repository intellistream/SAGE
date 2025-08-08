#!/bin/bash
#
# SAGE Framework 快速测试脚本
# Quick Test Script for SAGE Framework
#
# 快速测试主要包，适用于日常开发验证
# Quick test for main packages, suitable for daily development verification

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}🚀 SAGE Framework 快速测试${NC}"
echo -e "=============================="
echo ""

# 主要包列表 (有测试的包)
MAIN_PACKAGES=(
    "sage-frontend"
    "sage-core" 
    "sage-kernel"
)

# 使用全功能脚本进行快速测试
exec "$SCRIPT_DIR/test_all_packages.sh" \
    --continue-on-error \
    --jobs 3 \
    --timeout 120 \
    "${MAIN_PACKAGES[@]}" \
    "$@"
