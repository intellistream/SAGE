#!/bin/bash
# Kernel层重构 - 批量更新脚本
# Phase 4-7自动化执行

set -e

echo "=========================================="
echo "Phase 4: 更新 kernel 兼容层"
echo "=========================================="

# 更新 kernel/api/function/__init__.py
cat > packages/sage-kernel/src/sage/kernel/api/function/__init__.py << 'EOF'
"""
SAGE Kernel API Functions - 向后兼容层

⚠️ Deprecated: 这些类已迁移到 sage.common.core.functions
请使用: from sage.common.core.functions import MapFunction, SinkFunction, ...

为了向后兼容，本模块仍然提供这些导入。
"""

import warnings

warnings.warn(
    "Importing from sage.kernel.api.function is deprecated. "
    "Please use: from sage.common.core.functions import MapFunction, ...",
    DeprecationWarning,
    stacklevel=2,
)

# 从 common 重新导出
from sage.common.core.functions import (
    BaseFunction,
    MapFunction,
    FilterFunction,
    FlatMapFunction,
    SinkFunction,
    SourceFunction,
    BatchFunction,
    KeyByFunction,
    BaseJoinFunction,
    BaseCoMapFunction,
    LambdaMapFunction,
    FutureFunction,
)

__all__ = [
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
    "SinkFunction",
    "SourceFunction",
    "BatchFunction",
    "KeyByFunction",
    "BaseJoinFunction",
    "BaseCoMapFunction",
    "LambdaMapFunction",
    "FutureFunction",
]
EOF

# 更新 kernel/operators/__init__.py
cat > packages/sage-kernel/src/sage/kernel/operators/__init__.py << 'EOF'
"""
SAGE Kernel Operators - 基础算子 (向后兼容层)

⚠️ Deprecated: 算子基类已迁移到 sage.common.core.functions
请使用: from sage.common.core.functions import MapFunction, ...
"""

from sage.common.core.functions import (
    BaseFunction as BaseOperator,
    MapFunction as MapOperator,
    FilterFunction as FilterOperator,
    FlatMapFunction as FlatMapOperator,
    # 保持原名称
    BaseFunction,
    MapFunction,
    FilterFunction,
    FlatMapFunction,
)

__all__ = [
    "BaseOperator",
    "MapOperator",
    "FilterOperator",
    "FlatMapOperator",
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
]
EOF

echo "✅ Phase 4 完成"
echo ""

echo "=========================================="
echo "Phase 5: 更新 sage-libs 导入路径"
echo "=========================================="

cd packages/sage-libs/src

# 批量替换导入
find . -name "*.py" -type f -exec sed -i \
  -e 's/from sage\.kernel\.api\.function\.map_function import MapFunction/from sage.common.core.functions import MapFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.filter_function import FilterFunction/from sage.common.core.functions import FilterFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.sink_function import SinkFunction/from sage.common.core.functions import SinkFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.source_function import SourceFunction/from sage.common.core.functions import SourceFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.batch_function import BatchFunction/from sage.common.core.functions import BatchFunction/g' \
  {} \;

cd ../../..
echo "✅ Phase 5 完成"
echo ""

echo "=========================================="
echo "Phase 6: 更新 sage-middleware 导入路径 (可选)"
echo "=========================================="
echo "使用兼容层，无需修改middleware文件"
echo "✅ Phase 6 跳过（通过兼容层）"
echo ""

echo "=========================================="
echo "所有阶段完成！"
echo "=========================================="
