#!/bin/bash
# ============================================================================
# Fix Remaining Documentation Violations
# ============================================================================
# Purpose: Move the remaining 11 scattered documentation files to proper locations
#
# Categories:
# 1. benchmark/experiment/mem_docs/*.md (5 files)
# 2. amms/INSTALLATION_GUIDE.md (1 file)
# 3. sage-middleware GRAPH_MEMORY_IMPLEMENTATION.md (1 file)
# 4. tools/install/fixes/*.md (2 files)
# 5. tools/scripts/*.md (2 files)
# ============================================================================

set -e

SAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SAGE_ROOT"

DRY_RUN=${DRY_RUN:-true}

function move_file() {
    local src="$1"
    local dst="$2"

    if [ ! -f "$src" ]; then
        echo "⚠️  Source not found: $src"
        return 1
    fi

    echo "📄 $src"
    echo "   → $dst"

    if [ "$DRY_RUN" = "false" ]; then
        mkdir -p "$(dirname "$dst")"
        git mv "$src" "$dst"
    fi
}

echo "================================================================================================"
echo "📋 Fixing Remaining Documentation Violations"
echo "================================================================================================"
echo ""

if [ "$DRY_RUN" = "true" ]; then
    echo "🔍 DRY RUN MODE - No files will be moved"
    echo "   Set DRY_RUN=false to execute moves"
    echo ""
fi

# ============================================================================
# Category 1: benchmark/experiment/mem_docs/*.md (5 files)
# ============================================================================
echo "📦 Category 1: Benchmark Memory Experiment Documentation"
echo ""

move_file \
    "packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/MEMORY_SERVICE_NAMING_DISCUSSION.md" \
    "packages/sage-benchmark/docs/benchmark_memory/experiment_design/MEMORY_SERVICE_NAMING_DISCUSSION.md"

move_file \
    "packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/Memory_Combinatorial_Experiment_Design.md" \
    "packages/sage-benchmark/docs/benchmark_memory/experiment_design/Memory_Combinatorial_Experiment_Design.md"

move_file \
    "packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/Memory_Pipeline_Dev_Archive.md" \
    "packages/sage-benchmark/docs/benchmark_memory/experiment_design/Memory_Pipeline_Dev_Archive.md"

move_file \
    "packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/Memory_Systems_Comparison.md" \
    "packages/sage-benchmark/docs/benchmark_memory/experiment_design/Memory_Systems_Comparison.md"

move_file \
    "packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/mem_docs/README.md" \
    "packages/sage-benchmark/docs/benchmark_memory/experiment_design/README.md"

echo ""

# ============================================================================
# Category 2: amms/INSTALLATION_GUIDE.md (1 file)
# ============================================================================
echo "📦 Category 2: AMMS Installation Guide"
echo ""

move_file \
    "packages/sage-libs/src/sage/libs/amms/INSTALLATION_GUIDE.md" \
    "packages/sage-libs/docs/amms/INSTALLATION_GUIDE.md"

echo ""

# ============================================================================
# Category 3: sage-middleware GRAPH_MEMORY_IMPLEMENTATION.md (1 file)
# ============================================================================
echo "📦 Category 3: Sage Middleware Documentation"
echo ""

move_file \
    "packages/sage-middleware/src/sage/middleware/components/sage_mem/GRAPH_MEMORY_IMPLEMENTATION.md" \
    "packages/sage-middleware/docs/sage_mem/GRAPH_MEMORY_IMPLEMENTATION.md"

echo ""

# ============================================================================
# Category 4: tools/install/fixes/*.md (2 files)
# ============================================================================
echo "📦 Category 4: Tools Install Fixes Documentation"
echo ""

move_file \
    "tools/install/fixes/FIX_SUMMARY.md" \
    "tools/docs/install/fixes/FIX_SUMMARY.md"

move_file \
    "tools/install/fixes/UNBOUND_VARIABLE_FIX.md" \
    "tools/docs/install/fixes/UNBOUND_VARIABLE_FIX.md"

echo ""

# ============================================================================
# Category 5: tools/scripts/*.md (2 files)
# ============================================================================
echo "📦 Category 5: Tools Scripts Documentation"
echo ""

move_file \
    "tools/scripts/LIBAMM_MIGRATION_QUICKREF.md" \
    "tools/docs/scripts/LIBAMM_MIGRATION_QUICKREF.md"

move_file \
    "tools/scripts/README_CLUSTER_SETUP.md" \
    "tools/docs/scripts/README_CLUSTER_SETUP.md"

echo ""
echo "================================================================================================"

if [ "$DRY_RUN" = "true" ]; then
    echo "✅ Dry run completed - 11 files ready to move"
    echo "   Run: DRY_RUN=false $0"
else
    echo "✅ All 11 files moved successfully"
    echo "   Run: git status"
fi

echo "================================================================================================"
