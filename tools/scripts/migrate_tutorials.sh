#!/bin/bash
# migrate_tutorials.sh - 将 tutorials 打散迁移到各包
#
# 用法: ./tools/scripts/migrate_tutorials.sh [--dry-run]

set -e

SAGE_ROOT="${SAGE_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
DRY_RUN=false

if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 Dry run mode - no changes will be made"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║           Tutorials 迁移脚本 - 打散到各包                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# 定义迁移映射
declare -A MIGRATION_MAP=(
    ["tutorials/L1-common"]="packages/sage-common/src/sage/common/tutorials"
    ["tutorials/L2-platform"]="packages/sage-platform/src/sage/platform/tutorials"
    ["tutorials/L3-kernel"]="packages/sage-kernel/src/sage/kernel/tutorials"
    ["tutorials/L3-libs"]="packages/sage-libs/src/sage/libs/tutorials"
    ["tutorials/L4-middleware"]="packages/sage-middleware/src/sage/middleware/tutorials"
)

# Control Plane 相关教程迁移到 sage-llm-core
LLM_CORE_TUTORIALS="packages/sage-llm-core/src/sage/llm/tutorials"

# 入门示例迁移到 sage-common
COMMON_TUTORIALS="packages/sage-common/src/sage/common/tutorials"

cd "$SAGE_ROOT"

echo "📊 当前 tutorials 文件统计:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for src in "${!MIGRATION_MAP[@]}"; do
    if [[ -d "$src" ]]; then
        count=$(find "$src" -name "*.py" -type f 2>/dev/null | wc -l)
        echo "  $src: $count 个 Python 文件"
    fi
done
echo ""

# 函数：创建目录并移动文件
migrate_directory() {
    local src="$1"
    local dst="$2"

    if [[ ! -d "$src" ]]; then
        echo "  ⚠️  源目录不存在: $src"
        return
    fi

    local count=$(find "$src" -name "*.py" -type f 2>/dev/null | wc -l)
    if [[ "$count" -eq 0 ]]; then
        echo "  ⏭️  跳过空目录: $src"
        return
    fi

    echo "  📁 $src → $dst ($count 个文件)"

    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$dst"

        # 复制所有内容（保持目录结构）
        cp -r "$src"/* "$dst"/ 2>/dev/null || true

        # 创建 __init__.py
        if [[ ! -f "$dst/__init__.py" ]]; then
            cat > "$dst/__init__.py" << 'INITPY'
"""SAGE Tutorials - 教程和示例代码.

这个模块包含了可运行的教程和示例，随 PyPI 包一起分发。

用法:
    # 作为模块运行
    python -m sage.<package>.tutorials.<tutorial_name>

    # 或导入使用
    from sage.<package>.tutorials import <tutorial_name>
"""
INITPY
        fi

        # 为子目录创建 __init__.py (使用 bash 兼容语法)
        find "$dst" -type d | while read dir; do
            if [ ! -f "$dir/__init__.py" ]; then
                touch "$dir/__init__.py"
            fi
        done
    fi
}

echo "🚀 开始迁移..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 迁移各层 tutorials
for src in "${!MIGRATION_MAP[@]}"; do
    dst="${MIGRATION_MAP[$src]}"
    migrate_directory "$src" "$dst"
done

# 迁移根目录的索引与文档到 sage-common
echo ""
echo "📁 迁移根目录索引与文档..."
if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$COMMON_TUTORIALS"

    # 移动根目录的 Python 索引文件
    if [[ -f "tutorials/__init__.py" ]]; then
        cp "tutorials/__init__.py" "$COMMON_TUTORIALS/"
        echo "  ✅ __init__.py → sage-common/tutorials/"
    fi

    # 移动 README 和 QUICK_START
    for file in tutorials/README.md tutorials/QUICK_START.md tutorials/INSTALLATION_GUIDE.md; do
        if [[ -f "$file" ]]; then
            cp "$file" "$COMMON_TUTORIALS/"
            echo "  ✅ $(basename $file) → sage-common/tutorials/"
        fi
    done
fi

# 迁移 Control Plane 相关教程到 sage-llm-core
echo ""
echo "📁 迁移 Control Plane 教程..."
if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$LLM_CORE_TUTORIALS"

    for file in tutorials/L3-libs/llm/vllm_control_plane_tutorial.py tutorials/L5-apps/benchmark_control_plane_demo.py; do
        if [[ -f "$file" ]]; then
            cp "$file" "$LLM_CORE_TUTORIALS/"
            echo "  ✅ $(basename $file) → sage-llm-core/tutorials/"
        fi
    done

    # 移动 markdown 文件
    if [[ -f "tutorials/L3-libs/llm/vllm_control_plane_config_examples.md" ]]; then
        cp "tutorials/L3-libs/llm/vllm_control_plane_config_examples.md" "$LLM_CORE_TUTORIALS/"
        echo "  ✅ vllm_control_plane_config_examples.md → sage-llm-core/tutorials/"
    fi

    # 创建 __init__.py
    if [[ ! -f "$LLM_CORE_TUTORIALS/__init__.py" ]]; then
        cat > "$LLM_CORE_TUTORIALS/__init__.py" << 'INITPY'
"""SAGE LLM Core Tutorials - Control Plane 教程和示例.

这个模块包含了 Control Plane 相关的教程和示例。
"""
INITPY
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ "$DRY_RUN" == "true" ]]; then
    echo "🔍 Dry run 完成 - 未做任何更改"
else
    echo "✅ 迁移完成"
    echo ""
    echo "📊 迁移后文件统计:"
    for dst in "${MIGRATION_MAP[@]}" "$COMMON_TUTORIALS" "$LLM_CORE_TUTORIALS"; do
        if [[ -d "$dst" ]]; then
            count=$(find "$dst" -name "*.py" -type f 2>/dev/null | wc -l)
            echo "  $dst: $count 个 Python 文件"
        fi
    done
fi

echo ""
echo "🎯 下一步操作:"
echo "  1. 检查迁移结果: find packages/*/src/sage/*/tutorials -name '*.py' | head -20"
echo "  2. 删除旧目录: rm -rf tutorials/"
echo "  3. 提交更改: git add . && git commit -m 'refactor: migrate tutorials to packages'"
echo ""
