#!/bin/bash
# ============================================================================
# Reorganize Scattered Documentation Files
# ============================================================================
# Purpose: Move scattered MD files to proper locations per documentation policy
#
# This script reorganizes documentation in phases:
#   Phase 1: Package root violations (high priority)
#   Phase 2: amms/ documentation (high priority)
#   Phase 3: anns/ documentation (medium priority)
#   Phase 4: benchmark documentation (medium priority)
#   Phase 5: tools/ documentation (low priority)
#
# Usage:
#   ./reorganize_scattered_docs.sh [--phase N] [--dry-run] [--all]
# ============================================================================

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

DRY_RUN=false
PHASE="all"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --phase)
            PHASE="$2"
            shift 2
            ;;
        --all)
            PHASE="all"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--phase N] [--dry-run] [--all]"
            exit 1
            ;;
    esac
done

echo "================================================================================================"
echo "📦 文档整理脚本"
echo "================================================================================================"
echo "模式: $([ "$DRY_RUN" = true ] && echo "演习模式 (不实际移动文件)" || echo "执行模式 (实际移动文件)")"
echo "阶段: $PHASE"
echo ""

# Helper function
move_file() {
    local src="$1"
    local dst="$2"
    local description="$3"

    if [ ! -f "$src" ]; then
        echo "⚠️  源文件不存在: $src"
        return 1
    fi

    echo "  📄 $description"
    echo "     从: $src"
    echo "     到: $dst"

    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$(dirname "$dst")"
        git mv "$src" "$dst" 2>/dev/null || mv "$src" "$dst"
        echo "     ✅ 已移动"
    else
        echo "     🔍 演习模式 - 未实际移动"
    fi
    echo ""
}

# ============================================================================
# Phase 1: Package Root Violations (HIGH PRIORITY)
# ============================================================================
reorganize_phase1() {
    echo "════════════════════════════════════════════════════════════════"
    echo "🔴 Phase 1: 包根目录违规文件 (高优先级)"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    # sage-libs root violations
    mkdir -p packages/sage-libs/docs/amms

    move_file \
        "packages/sage-libs/AMMS_PYPI_PUBLISH_GUIDE.md" \
        "packages/sage-libs/docs/amms/PYPI_PUBLISH_GUIDE.md" \
        "AMMS PyPI 发布指南"

    move_file \
        "packages/sage-libs/LIBAMM_INSTALLATION.md" \
        "packages/sage-libs/docs/amms/INSTALLATION.md" \
        "LibAMM 安装指南"

    move_file \
        "packages/sage-libs/README_LIBAMM.md" \
        "packages/sage-libs/docs/amms/LIBAMM_README.md" \
        "LibAMM 旧版 README"

    # sage-middleware root violation
    mkdir -p packages/sage-middleware/docs

    move_file \
        "packages/sage-middleware/MIGRATION_SCIKIT_BUILD.md" \
        "packages/sage-middleware/docs/MIGRATION_SCIKIT_BUILD.md" \
        "scikit-build 迁移文档"
}

# ============================================================================
# Phase 2: amms/ Documentation (HIGH PRIORITY)
# ============================================================================
reorganize_phase2() {
    echo "════════════════════════════════════════════════════════════════"
    echo "🔴 Phase 2: amms/ 散落文档 (高优先级)"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    mkdir -p packages/sage-libs/docs/amms

    local amms_src="packages/sage-libs/src/sage/libs/amms"
    local amms_dst="packages/sage-libs/docs/amms"

    move_file \
        "$amms_src/BUILD_PUBLISH.md" \
        "$amms_dst/BUILD_PUBLISH.md" \
        "AMMS 构建和发布指南"

    move_file \
        "$amms_src/CHECKLIST.md" \
        "$amms_dst/CHECKLIST.md" \
        "AMMS 发布检查清单"

    move_file \
        "$amms_src/MIGRATION.md" \
        "$amms_dst/MIGRATION.md" \
        "AMMS 迁移记录"

    move_file \
        "$amms_src/PAPI_PRECOMPILED_SOLUTION.md" \
        "$amms_dst/PAPI_PRECOMPILED_SOLUTION.md" \
        "PAPI 预编译方案"

    move_file \
        "$amms_src/PYPI_BUILD_STRATEGY.md" \
        "$amms_dst/PYPI_BUILD_STRATEGY.md" \
        "PyPI 构建策略"

    move_file \
        "$amms_src/QUICKREF.md" \
        "$amms_dst/QUICKREF.md" \
        "AMMS 快速参考"

    move_file \
        "$amms_src/REFACTORING_SUMMARY.md" \
        "$amms_dst/REFACTORING_SUMMARY.md" \
        "AMMS 重构总结"

    # Keep README.md in source (main documentation)
    echo "  ℹ️  保留: $amms_src/README.md (主文档)"
    echo ""

    move_file \
        "$amms_src/implementations/README.md" \
        "$amms_dst/implementations.md" \
        "AMMS 实现说明"
}

# ============================================================================
# Phase 3: anns/ Documentation (MEDIUM PRIORITY)
# ============================================================================
reorganize_phase3() {
    echo "════════════════════════════════════════════════════════════════"
    echo "🟡 Phase 3: anns/ 文档 (中优先级)"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    mkdir -p packages/sage-libs/docs/anns

    local anns_src="packages/sage-libs/src/sage/libs/anns"
    local anns_dst="packages/sage-libs/docs/anns"

    # Keep top-level README in source (main documentation)
    echo "  ℹ️  保留: $anns_src/README.md (主文档)"
    echo ""

    move_file \
        "$anns_src/implementations/README.md" \
        "$anns_dst/implementations.md" \
        "ANNS 实现说明"

    move_file \
        "$anns_src/implementations/README_spdlog_fix.md" \
        "$anns_dst/spdlog_fix.md" \
        "spdlog 修复说明"

    move_file \
        "$anns_src/wrappers/vsag/vsag_hnsw/PREFETCH_OPTIMIZATION.md" \
        "$anns_dst/vsag_prefetch_optimization.md" \
        "VSAG HNSW 预取优化"

    move_file \
        "$anns_src/wrappers/vsag/vsag_hnsw/README.md" \
        "$anns_dst/vsag_hnsw.md" \
        "VSAG HNSW 说明"
}

# ============================================================================
# Phase 4: benchmark Documentation (MEDIUM PRIORITY)
# ============================================================================
reorganize_phase4() {
    echo "════════════════════════════════════════════════════════════════"
    echo "🟡 Phase 4: benchmark 文档 (中优先级)"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    echo "⚠️  Benchmark 文档较复杂，建议手动整理："
    echo "   • 实验设计文档 → docs-public/docs_src/dev-notes/l5-benchmark/"
    echo "   • README 文件 → packages/sage-benchmark/docs/"
    echo "   • DATA_PATHS.md → 可能需要保留在代码目录（运行时配置）"
    echo ""
    echo "   查看详细列表: .sage/docs-location-violations-report.md"
    echo ""
}

# ============================================================================
# Phase 5: tools/ and other Documentation (LOW PRIORITY)
# ============================================================================
reorganize_phase5() {
    echo "════════════════════════════════════════════════════════════════"
    echo "🟢 Phase 5: tools/ 和其他文档 (低优先级)"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    mkdir -p tools/docs

    move_file \
        "tools/docs/SUBMODULE_DEVELOPMENT.md" \
        "docs-public/docs_src/dev-notes/cross-layer/submodule-development.md" \
        "子模块开发指南"

    move_file \
        "tools/install/fixes/FIX_SUMMARY.md" \
        "tools/docs/install-fixes-summary.md" \
        "安装修复摘要"

    move_file \
        "tools/install/fixes/UNBOUND_VARIABLE_FIX.md" \
        "tools/docs/unbound-variable-fix.md" \
        "未绑定变量修复"

    move_file \
        "tools/scripts/LIBAMM_MIGRATION_QUICKREF.md" \
        "tools/docs/libamm-migration-quickref.md" \
        "LibAMM 迁移快速参考"

    move_file \
        "tools/scripts/README_CLUSTER_SETUP.md" \
        "tools/docs/cluster-setup.md" \
        "集群设置说明"

    # Other files
    mkdir -p packages/sage-libs/docs/agentic
    mkdir -p packages/sage-llm-core/docs/control-plane
    mkdir -p packages/sage-middleware/docs

    move_file \
        "packages/sage-libs/src/sage/libs/agentic/agents/runtime/README.md" \
        "packages/sage-libs/docs/agentic/runtime.md" \
        "Agentic 运行时说明"

    move_file \
        "packages/sage-libs/src/sage/libs/agentic/workflow/generators/README.md" \
        "packages/sage-libs/docs/agentic/workflow-generators.md" \
        "Agentic 工作流生成器"

    move_file \
        "packages/sage-libs/src/sage/libs/sias/SUBMODULE.md" \
        "packages/sage-libs/docs/sias-submodule.md" \
        "SIAS 子模块说明"

    move_file \
        "packages/sage-llm-core/src/sage/llm/control_plane/examples/README.md" \
        "packages/sage-llm-core/docs/control-plane/examples.md" \
        "Control Plane 示例"

    move_file \
        "packages/sage-llm-core/src/sage/llm/control_plane/strategies/README.md" \
        "packages/sage-llm-core/docs/control-plane/strategies.md" \
        "Control Plane 策略"

    move_file \
        "packages/sage-middleware/src/sage/middleware/components/sage_mem/GRAPH_MEMORY_IMPLEMENTATION.md" \
        "packages/sage-middleware/docs/graph-memory-implementation.md" \
        "图内存实现说明"
}

# ============================================================================
# Main Execution
# ============================================================================

case $PHASE in
    1)
        reorganize_phase1
        ;;
    2)
        reorganize_phase2
        ;;
    3)
        reorganize_phase3
        ;;
    4)
        reorganize_phase4
        ;;
    5)
        reorganize_phase5
        ;;
    all)
        reorganize_phase1
        reorganize_phase2
        reorganize_phase3
        reorganize_phase4
        reorganize_phase5
        ;;
    *)
        echo "❌ 无效的阶段: $PHASE"
        echo "有效阶段: 1, 2, 3, 4, 5, all"
        exit 1
        ;;
esac

echo "================================================================================================"
echo "✅ 文档整理完成"
echo "================================================================================================"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "💡 这是演习模式，没有实际移动文件"
    echo "   要执行实际移动，请去掉 --dry-run 参数"
else
    echo "📝 下一步:"
    echo "   1. 检查移动后的文件位置是否正确"
    echo "   2. 更新任何引用这些文档的链接"
    echo "   3. 运行 pre-commit 检查: pre-commit run --all-files"
    echo "   4. 提交更改: git commit -m 'docs: reorganize scattered documentation'"
fi
echo ""
