#!/bin/bash
# migrate_studio_subdirs.sh
# 将 sage-studio/tests 子目录中的测试移到 unit/integration 目录

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

echo "=========================================="
echo "sage-studio 子目录测试迁移脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

studio_tests_dir="packages/sage-studio/tests"

# ============================================
# services/ 目录 - 大部分是单元测试
# ============================================
echo -e "${YELLOW}迁移 services/ 测试到 unit/services/${NC}"
echo ""

mkdir -p "$studio_tests_dir/unit/services"

declare -a service_files=(
    "test_auth_service.py"
    "test_vector_store.py"
    "test_file_upload_service.py"
    "test_stream_handler.py"
    "test_knowledge_manager.py"
    "test_docs_processor.py"
    "test_workflow_generator.py"
    "test_agent_orchestrator.py"
    "test_researcher_agent.py"
    "test_finetune_manager.py"
)

# 检查是否有 integration 类型的服务测试
declare -a service_integration_files=(
    "test_chat_routes.py"  # 可能涉及路由集成
)

for file in "${service_files[@]}"; do
    src="$studio_tests_dir/services/$file"
    dst="$studio_tests_dir/unit/services/$file"

    if [[ -f "$src" ]]; then
        echo -n "  $file -> unit/services/ ... "
        if git mv "$src" "$dst" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
done

# 可能需要单独处理的集成测试
for file in "${service_integration_files[@]}"; do
    src="$studio_tests_dir/services/$file"
    if [[ -f "$src" ]]; then
        echo -e "  ${YELLOW}注意: $file 可能是集成测试，需要手动检查${NC}"
    fi
done

echo ""

# ============================================
# config/ 目录 - 单元测试
# ============================================
echo -e "${YELLOW}迁移 config/ 测试到 unit/config/${NC}"
echo ""

mkdir -p "$studio_tests_dir/unit/config"

declare -a config_files=(
    "test_api_uploads.py"
    "test_backend_api.py"
)

for file in "${config_files[@]}"; do
    src="$studio_tests_dir/config/$file"
    dst="$studio_tests_dir/unit/config/$file"

    if [[ -f "$src" ]]; then
        echo -n "  $file -> unit/config/ ... "
        if git mv "$src" "$dst" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
done

echo ""

# ============================================
# tools/ 目录 - 单元测试
# ============================================
echo -e "${YELLOW}迁移 tools/ 测试到 unit/tools/${NC}"
echo ""

mkdir -p "$studio_tests_dir/unit/tools"

declare -a tools_files=(
    "test_api_docs.py"
    "test_arxiv_search.py"
    "test_base.py"
    "test_knowledge_search.py"
)

for file in "${tools_files[@]}"; do
    src="$studio_tests_dir/tools/$file"
    dst="$studio_tests_dir/unit/tools/$file"

    if [[ -f "$src" ]]; then
        echo -n "  $file -> unit/tools/ ... "
        if git mv "$src" "$dst" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
done

echo ""

# ============================================
# utils/ 目录 - 单元测试
# ============================================
echo -e "${YELLOW}迁移 utils/ 测试到 unit/utils/${NC}"
echo ""

mkdir -p "$studio_tests_dir/unit/utils"

declare -a utils_files=(
    "test_gpu_check.py"
)

for file in "${utils_files[@]}"; do
    src="$studio_tests_dir/utils/$file"
    dst="$studio_tests_dir/unit/utils/$file"

    if [[ -f "$src" ]]; then
        echo -n "  $file -> unit/utils/ ... "
        if git mv "$src" "$dst" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗${NC}"
        fi
    fi
done

echo ""

# ============================================
# 清理空目录
# ============================================
echo -e "${YELLOW}清理空目录${NC}"
echo ""

for dir in services config tools utils; do
    full_dir="$studio_tests_dir/$dir"
    if [[ -d "$full_dir" ]]; then
        # 检查是否为空（排除 __pycache__ 和 __init__.py）
        remaining=$(find "$full_dir" -type f ! -name "__init__.py" ! -path "*/__pycache__/*" | wc -l)
        if [[ $remaining -eq 0 ]]; then
            echo -e "  移除空目录: $dir/"
            rm -rf "$full_dir"
        else
            echo -e "  ${YELLOW}保留 $dir/ (还有 $remaining 个文件)${NC}"
        fi
    fi
done

echo ""

# ============================================
# 创建 __init__.py 文件
# ============================================
echo -e "${YELLOW}创建 __init__.py 文件${NC}"
echo ""

for subdir in unit/services unit/config unit/tools unit/utils; do
    init_file="$studio_tests_dir/$subdir/__init__.py"
    if [[ ! -f "$init_file" ]]; then
        echo '"""Tests for sage-studio."""' > "$init_file"
        git add "$init_file"
        echo -e "  ${GREEN}✓${NC} 创建 $subdir/__init__.py"
    fi
done

echo ""
echo "=========================================="
echo "迁移完成"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 手动检查 services/test_chat_routes.py 是否应该移到 integration/"
echo "  2. 运行测试: sage-dev project test"
echo "  3. 提交更改"
