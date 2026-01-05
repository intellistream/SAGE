#!/bin/bash
# reorganize_test_files.sh
# 重组测试文件：重命名 *_test.py 为 test_*.py，并将 sage-studio 测试分类到 unit/integration

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

echo "=========================================="
echo "测试文件重组脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 统计变量
total_renamed=0
total_moved=0
errors=0

# ============================================
# 第1步：重命名 *_test.py 为 test_*.py
# ============================================
echo -e "${YELLOW}步骤 1/4: 重命名 *_test.py 文件为 test_*.py${NC}"
echo ""

declare -a files_to_rename=(
    "packages/sage-kernel/tests/unit/core/function/join_test.py:test_join.py"
    "packages/sage-kernel/tests/unit/core/function/connected_keyby_test.py:test_connected_keyby.py"
    "packages/sage-kernel/tests/unit/core/function/keyby_test.py:test_keyby.py"
    "packages/sage-kernel/tests/unit/core/function/flatmap_test.py:test_flatmap.py"
    "packages/sage-kernel/tests/unit/core/function/comap_test.py:test_comap.py"
    "packages/sage-kernel/tests/unit/core/function/filter_test.py:test_filter.py"
    "packages/sage-kernel/tests/unit/kernel/simple_task_context_routing_test.py:test_simple_task_context_routing.py"
    "packages/sage-middleware/tests/operators/tools/nature_news_fetcher_test.py:test_nature_news_fetcher.py"
    "packages/sage-middleware/tests/operators/tools/arxiv_paper_searcher_test.py:test_arxiv_paper_searcher.py"
    "packages/sage-middleware/tests/operators/tools/image_captioner_test.py:test_image_captioner.py"
    "packages/sage-middleware/tests/operators/tools/url_text_extractor_test.py:test_url_text_extractor.py"
    "packages/sage-middleware/tests/operators/tools/text_detector_test.py:test_text_detector.py"
    "packages/sage-libs/tests/lib/io/sink_test.py:test_sink.py"
)

for entry in "${files_to_rename[@]}"; do
    old_path="${entry%%:*}"
    new_name="${entry##*:}"

    if [[ -f "$old_path" ]]; then
        dir_path="$(dirname "$old_path")"
        new_path="$dir_path/$new_name"

        echo -n "  重命名: $old_path -> $new_name ... "
        if git mv "$old_path" "$new_path" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            ((total_renamed++))
        else
            echo -e "${RED}✗${NC}"
            ((errors++))
        fi
    else
        echo -e "  ${YELLOW}跳过: $old_path (文件不存在)${NC}"
    fi
done

echo ""
echo -e "重命名完成: ${GREEN}$total_renamed${NC} 个文件"
echo ""

# ============================================
# 第2步：创建 sage-studio 测试目录结构
# ============================================
echo -e "${YELLOW}步骤 2/4: 创建 sage-studio/tests/ 子目录${NC}"
echo ""

studio_tests_dir="packages/sage-studio/tests"

if [[ -d "$studio_tests_dir" ]]; then
    mkdir -p "$studio_tests_dir/unit"
    mkdir -p "$studio_tests_dir/integration"
    echo -e "  ${GREEN}✓${NC} 创建 $studio_tests_dir/unit/"
    echo -e "  ${GREEN}✓${NC} 创建 $studio_tests_dir/integration/"
else
    echo -e "  ${RED}✗${NC} sage-studio/tests/ 目录不存在"
    ((errors++))
fi

echo ""

# ============================================
# 第3步：移动测试文件到 unit/integration
# ============================================
echo -e "${YELLOW}步骤 3/4: 移动 sage-studio 测试文件${NC}"
echo ""

# 移动到 integration/
declare -a integration_files=(
    "test_e2e_integration.py"
    "test_agent_step.py"
    "test_studio_cli.py"
)

echo "移动到 integration/:"
for file in "${integration_files[@]}"; do
    src="$studio_tests_dir/$file"
    dst="$studio_tests_dir/integration/$file"

    if [[ -f "$src" ]]; then
        echo -n "  $file ... "
        if git mv "$src" "$dst" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            ((total_moved++))
        else
            echo -e "${RED}✗${NC}"
            ((errors++))
        fi
    else
        echo -e "  ${YELLOW}跳过: $file (文件不存在)${NC}"
    fi
done

echo ""

# 移动到 unit/
declare -a unit_files=(
    "test_models.py"
    "test_pipeline_builder.py"
    "test_node_registry.py"
)

echo "移动到 unit/:"
for file in "${unit_files[@]}"; do
    src="$studio_tests_dir/$file"
    dst="$studio_tests_dir/unit/$file"

    if [[ -f "$src" ]]; then
        echo -n "  $file ... "
        if git mv "$src" "$dst" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
            ((total_moved++))
        else
            echo -e "${RED}✗${NC}"
            ((errors++))
        fi
    else
        echo -e "  ${YELLOW}跳过: $file (文件不存在)${NC}"
    fi
done

echo ""

# ============================================
# 第4步：检查并报告 services/ 和 tools/ 子目录
# ============================================
echo -e "${YELLOW}步骤 4/4: 检查 sage-studio/tests/ 子目录${NC}"
echo ""

if [[ -d "$studio_tests_dir/services" ]]; then
    service_count=$(find "$studio_tests_dir/services" -name "test_*.py" | wc -l)
    echo -e "  ${YELLOW}注意:${NC} services/ 目录包含 $service_count 个测试文件"
    echo "       建议根据测试类型移动到 unit/ 或 integration/"
fi

if [[ -d "$studio_tests_dir/tools" ]]; then
    tools_count=$(find "$studio_tests_dir/tools" -name "test_*.py" | wc -l)
    echo -e "  ${YELLOW}注意:${NC} tools/ 目录包含 $tools_count 个测试文件"
    echo "       建议根据测试类型移动到 unit/ 或 integration/"
fi

if [[ -d "$studio_tests_dir/config" ]]; then
    config_count=$(find "$studio_tests_dir/config" -name "test_*.py" | wc -l)
    echo -e "  ${YELLOW}注意:${NC} config/ 目录包含 $config_count 个测试文件"
    echo "       建议根据测试类型移动到 unit/ 或 integration/"
fi

if [[ -d "$studio_tests_dir/utils" ]]; then
    utils_count=$(find "$studio_tests_dir/utils" -name "test_*.py" | wc -l)
    echo -e "  ${YELLOW}注意:${NC} utils/ 目录包含 $utils_count 个测试文件"
    echo "       建议根据测试类型移动到 unit/ 或 integration/"
fi

echo ""

# ============================================
# 总结
# ============================================
echo "=========================================="
echo "重组完成"
echo "=========================================="
echo ""
echo -e "统计:"
echo -e "  重命名文件: ${GREEN}$total_renamed${NC}"
echo -e "  移动文件:   ${GREEN}$total_moved${NC}"
if [[ $errors -gt 0 ]]; then
    echo -e "  错误:       ${RED}$errors${NC}"
fi
echo ""

if [[ $errors -eq 0 ]]; then
    echo -e "${GREEN}✓ 所有操作成功完成！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 运行测试验证: sage-dev project test"
    echo "  2. 检查 sage-studio/tests/services, tools, config, utils 目录"
    echo "  3. 提交更改: git commit -m 'refactor(tests): reorganize test files naming and structure'"
    exit 0
else
    echo -e "${RED}✗ 部分操作失败，请检查错误信息${NC}"
    exit 1
fi
