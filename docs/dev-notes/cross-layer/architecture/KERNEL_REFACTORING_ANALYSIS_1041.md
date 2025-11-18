# Kernel 层重构分析 - Issue #1041

**Date**: 2025-10-24  
**Author**: SAGE Team  
**Summary**: Kernel 层功能重构分析，探讨将部分功能下沉到 platform 或 common 层的可行性

> **问题**: kernel 的部分功能应该下沉到 platform 或 common 层  
> **状态**: 📋 分析中

---

## 🎯 问题陈述

### 当前架构问题

1. **sage-libs (L3) 依赖 sage-kernel (L3)** - 同层依赖不清晰
   - sage-libs 导入了 14 次 `sage.kernel.api.function.*`
   - sage-libs 需要使用基础函数接口（MapFunction, FilterFunction, SinkFunction等）
   - 这些基础接口应该在更低层

2. **kernel.api 和 BaseService 分层不一致**
   - BaseService 已在 L2 (sage-platform/service)
   - kernel.api 中的函数接口仍在 L3
   - 应该放在同一层级

### 依赖统计

#### sage-libs → sage.kernel 依赖分析

```
总计: 14 次导入

Function APIs (13次):
├── MapFunction: 7次
│   ├── agents/agent.py
│   ├── agents/runtime/agent.py
│   ├── agents/planning/llm_planner.py
│   ├── agents/profile/profile.py
│   ├── agents/action/mcp_registry.py
│   ├── workflow/base.py
│   └── filters/context_source.py (SourceFunction)
├── FilterFunction: 3次
│   ├── filters/tool_filter.py
│   ├── filters/evaluate_filter.py
│   └── rag/profiler.py
├── SinkFunction: 2次
│   ├── io/sink.py
│   └── filters/context_sink.py
├── SourceFunction: 1次
│   └── io/source.py
└── BatchFunction: 1次
    └── io/batch.py

Environment API (可选):
└── LocalEnvironment: 0次 (libs 不需要)
```

#### sage-middleware → sage.kernel 依赖分析

```
总计: 15 次导入

Operators (15次):
└── MapOperator: 15次
    ├── operators/rag/*.py (11个文件)
    ├── operators/llm/vllm_generator.py
    ├── operators/tools/searcher_tool.py
    └── components/sage_refiner/python/adapter.py

Environment API (示例代码):
└── LocalEnvironment: 1次
    └── components/sage_refiner/examples/rag_integration.py
```

---

## 🏗️ 重构方案

### 方案 1: 下沉到 L2 (sage-platform) ✅ **推荐**

创建 `sage-platform/api` 子包，包含基础函数接口。

#### 迁移内容

**从 `sage-kernel/api/function/` 迁移到 `sage-platform/api/`**:

```
packages/sage-platform/src/sage/platform/api/
├── __init__.py                  # 导出所有函数基类
├── base_function.py             # ✅ BaseFunction (所有函数基类)
├── map_function.py              # ✅ MapFunction
├── filter_function.py           # ✅ FilterFunction
├── flatmap_function.py          # ✅ FlatMapFunction
├── sink_function.py             # ✅ SinkFunction
├── source_function.py           # ✅ SourceFunction
├── batch_function.py            # ✅ BatchFunction
├── simple_batch_function.py     # ✅ SimpleBatchFunction
├── keyby_function.py            # ✅ KeyByFunction
├── join_function.py             # ✅ JoinFunction
├── comap_function.py            # ✅ CoMapFunction
├── flatmap_collector.py         # ✅ FlatMapCollector
├── lambda_function.py           # ✅ LambdaFunction
├── future_function.py           # ✅ FutureFunction (异步支持)
├── kafka_source.py              # ⚠️  KafkaSource (考虑是否迁移)
└── _internal_print_sink.py      # ⚠️  InternalPrintSink (内部实现)
```

**保留在 `sage-kernel/api/`**:

```
packages/sage-kernel/src/sage/kernel/api/
├── __init__.py                  # 导出环境和流
├── local_environment.py         # ✅ LocalEnvironment (L3 - 执行引擎)
├── remote_environment.py        # ✅ RemoteEnvironment (L3 - 分布式执行)
├── base_environment.py          # ✅ BaseEnvironment (L3 - 执行环境基类)
├── datastream.py                # ✅ DataStream (L3 - 流式API)
├── connected_streams.py         # ✅ ConnectedStreams (L3 - 多流操作)
├── operator/                    # ✅ 内部算子实现 (L3 - runtime依赖)
└── transformation/              # ✅ 转换逻辑 (L3 - runtime依赖)
```

#### 架构分层逻辑

```
L1 (sage-common)
└── 基础工具、配置、日志 (无业务逻辑)

L2 (sage-platform)
├── queue/          # 消息队列抽象
├── storage/        # KV存储后端
├── service/        # 服务基类 ✅ BaseService
└── api/            # ✅ 新增: 函数基类 (MapFunction, SinkFunction等)
    └── 职责: 定义用户自定义函数的抽象接口
    └── 特点: 不依赖执行引擎，纯接口定义

L3 (sage-kernel, sage-libs)
├── sage-kernel
│   ├── api/        # Environment + DataStream (依赖 runtime)
│   ├── runtime/    # 执行引擎 (JobManager, Dispatcher, Scheduler)
│   └── operators/  # 内部算子实现
└── sage-libs
    ├── agents/     # 使用 platform.api 中的 MapFunction
    ├── io/         # 使用 platform.api 中的 SourceFunction, SinkFunction
    └── filters/    # 使用 platform.api 中的 FilterFunction

L4 (sage-middleware)
└── operators/      # 使用 platform.api 中的 MapFunction
    └── 职责: 组合 libs + kernel 提供领域算子
```

#### 为什么放在 L2？

1. **接口定义 vs 实现分离**
   - **L2 (platform.api)**: 定义函数**接口** (MapFunction, SinkFunction等)
     - 用户继承这些类实现自己的逻辑
     - 不依赖执行引擎
   - **L3 (kernel.api)**: 提供**执行环境** (LocalEnvironment, DataStream)
     - 负责运行时调度和执行
     - 依赖 runtime 模块

2. **与 BaseService 对齐**
   - BaseService 已在 L2 (sage-platform/service)
   - 函数接口应该和服务基类在同一层
   - 都是"平台服务抽象"

3. **解决同层依赖**
   - sage-libs (L3) 可以依赖 sage-platform (L2)
   - sage-middleware (L4) 可以依赖 sage-platform (L2)
   - 避免 L3 ↔ L3 的水平依赖

4. **复用性**
   - 函数接口是通用抽象，不仅 kernel 使用
   - libs, middleware 都需要继承这些接口
   - 应该在更底层提供

---

### 方案 2: 部分下沉到 L1 (sage-common) ❌ **不推荐**

将**最基础**的函数接口下沉到 common。

#### 理由

**不推荐的原因**:

1. **common 应该"无业务"**
   - MapFunction, SinkFunction 是数据流处理的核心抽象
   - 虽然是接口，但已经是"业务概念"
   - common 应该只有通用工具（log, config, decorators）

2. **platform 更合适**
   - platform 的定位就是"平台服务抽象"
   - 函数接口属于平台API的一部分

3. **避免过度下沉**
   - 不是所有"基础"的东西都要放 L1
   - L2 存在的意义就是提供平台抽象

---

## 📋 迁移计划 (修订版)

### Phase 1: 创建 sage-common/core/functions

**目标**: 在 L1 层创建函数接口模块

```bash
# 1. 创建目录结构
mkdir -p packages/sage-common/src/sage/common/core/functions

# 2. 迁移函数基类文件 (13个文件)
# 从 kernel/api/function/ 迁移纯接口（不依赖 runtime）
cp packages/sage-kernel/src/sage/kernel/api/function/base_function.py \
   packages/sage-common/src/sage/common/core/functions/

cp packages/sage-kernel/src/sage/kernel/api/function/map_function.py \
   packages/sage-common/src/sage/common/core/functions/

# ... (其他11个文件)

# 3. 创建 __init__.py 导出
cat > packages/sage-common/src/sage/common/core/functions/__init__.py << 'EOF'
"""
SAGE Common Functions - 基础函数接口定义

Layer: L1 (Common - Core Abstractions)
Dependencies: 无

提供用户自定义函数的基础接口：
- BaseFunction: 所有函数的基类
- MapFunction: 一对一映射函数
- FilterFunction: 过滤函数
- SinkFunction: 输出函数
- SourceFunction: 数据源函数
- BatchFunction: 批处理函数
等等...

这些接口是纯抽象定义，不依赖任何执行引擎。
"""

from .base_function import BaseFunction
from .map_function import MapFunction
from .filter_function import FilterFunction
from .flatmap_function import FlatMapFunction
from .sink_function import SinkFunction
from .source_function import SourceFunction
from .batch_function import BatchFunction
from .keyby_function import KeyByFunction
from .join_function import JoinFunction
from .comap_function import CoMapFunction
from .flatmap_collector import FlatMapCollector
from .lambda_function import LambdaFunction
from .future_function import FutureFunction

__all__ = [
    "BaseFunction",
    "MapFunction",
    "FilterFunction",
    "FlatMapFunction",
    "SinkFunction",
    "SourceFunction",
    "BatchFunction",
    "KeyByFunction",
    "JoinFunction",
    "CoMapFunction",
    "FlatMapCollector",
    "LambdaFunction",
    "FutureFunction",
]
EOF

# 4. 更新 common 主 __init__.py
# 添加 functions 到导出列表
```

**预计文件变更**:
- ✅ 新增: `packages/sage-common/src/sage/common/core/functions/` (13个文件)
- ✅ 迁移: 从 kernel/api/function/ 复制文件（后续删除源文件）

---

### Phase 2: 迁移 PrintSink 到 common

**目标**: 将调试工具迁移到 common

```bash
# 1. 创建调试组件目录
mkdir -p packages/sage-common/src/sage/common/components/debug

# 2. 迁移 _internal_print_sink.py
mv packages/sage-kernel/src/sage/kernel/api/function/_internal_print_sink.py \
   packages/sage-common/src/sage/common/components/debug/print_sink.py

# 3. 更新导入路径（移除 _internal 前缀）
# 修改 print_sink.py 中的导入:
# 旧: from sage.kernel.api.function.sink_function import SinkFunction
# 新: from sage.common.core.functions import SinkFunction

# 4. 创建 __init__.py
cat > packages/sage-common/src/sage/common/components/debug/__init__.py << 'EOF'
"""
SAGE Common Debug Components - 调试工具

提供调试和开发辅助功能。
"""

from .print_sink import PrintSink

__all__ = ["PrintSink"]
EOF
```

**预计文件变更**:
- ✅ 新增: `packages/sage-common/src/sage/common/components/debug/print_sink.py`
- ✅ 删除: `packages/sage-kernel/src/sage/kernel/api/function/_internal_print_sink.py`

---

### Phase 3: 删除 kafka_source.py

**目标**: 移除 kernel 中的重复实现

```bash
# 1. 删除 kernel 中的 KafkaSourceFunction
rm packages/sage-kernel/src/sage/kernel/api/function/kafka_source.py

# 2. 更新 base_environment.py
# 修改 from_kafka_source() 方法：
# 旧: from sage.kernel.api.function.kafka_source import KafkaSourceFunction
# 新: from sage.libs.foundation.io import KafkaSource as KafkaSourceFunction

# 3. 改进 libs 中的 KafkaSource 实现
# 将 kernel 中的完整实现代码迁移到 libs.io.source.KafkaSource
```

**预计文件变更**:
- ❌ 删除: `packages/sage-kernel/src/sage/kernel/api/function/kafka_source.py`
- 🔧 更新: `packages/sage-kernel/src/sage/kernel/api/base_environment.py`
- ✨ 改进: `packages/sage-libs/src/sage/libs/io/source.py` (KafkaSource)

---

### Phase 4: 更新 sage-kernel 兼容层

**目标**: 在 kernel 中保留向后兼容的导出

```python
# packages/sage-kernel/src/sage/kernel/api/function/__init__.py
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
    JoinFunction,
    CoMapFunction,
    FlatMapCollector,
    LambdaFunction,
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
    "JoinFunction",
    "CoMapFunction",
    "FlatMapCollector",
    "LambdaFunction",
    "FutureFunction",
]
```

```python
# packages/sage-kernel/src/sage/kernel/operators/__init__.py
"""
SAGE Kernel Operators - 基础算子 (向后兼容层)

⚠️ Deprecated: 算子基类已迁移到 sage.common.core.functions
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
```

**预计文件变更**:
- 🔧 修改: `packages/sage-kernel/src/sage/kernel/api/function/__init__.py`
- 🔧 修改: `packages/sage-kernel/src/sage/kernel/operators/__init__.py`
- 🔧 修改: `packages/sage-kernel/src/sage/kernel/api/datastream.py` (PrintSink导入)

---

### Phase 5: 更新 sage-libs 导入路径

**目标**: 将 sage-libs 的导入从 kernel 改为 common

```bash
# 需要更新的文件 (14个)
packages/sage-libs/src/sage/libs/
├── agents/agent.py
├── agents/runtime/agent.py
├── agents/planning/llm_planner.py
├── agents/profile/profile.py
├── agents/action/mcp_registry.py
├── filters/tool_filter.py
├── filters/evaluate_filter.py
├── filters/context_sink.py
├── filters/context_source.py
├── io/sink.py
├── io/source.py
├── io/batch.py
├── rag/profiler.py
└── workflow/base.py
```

**批量替换命令**:
```bash
cd packages/sage-libs/src

# 替换所有函数接口导入
find . -name "*.py" -type f -exec sed -i \
  -e 's/from sage\.kernel\.api\.function\.map_function import MapFunction/from sage.common.core.functions import MapFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.filter_function import FilterFunction/from sage.common.core.functions import FilterFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.sink_function import SinkFunction/from sage.common.core.functions import SinkFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.source_function import SourceFunction/from sage.common.core.functions import SourceFunction/g' \
  -e 's/from sage\.kernel\.api\.function\.batch_function import BatchFunction/from sage.common.core.functions import BatchFunction/g' \
  {} \;
```

**预计文件变更**:
- 🔧 修改: 14 个 sage-libs 文件

---

### Phase 6: 更新 sage-middleware 导入路径

**目标**: 将 middleware 的导入改为从 common

```bash
# 需要更新的文件 (15个)
packages/sage-middleware/src/sage/middleware/
├── operators/rag/*.py (11个)
├── operators/llm/vllm_generator.py
├── operators/tools/searcher_tool.py
└── components/sage_refiner/python/adapter.py
```

**两种选择**:

**选项 1**: 直接从 common 导入
```python
# 旧导入
from sage.kernel.operators import MapOperator

# 新导入
from sage.common.core.functions import MapFunction as MapOperator
```

**选项 2**: 通过 kernel 兼容层（推荐）
```python
# 保持不变，kernel.operators 会自动重定向到 common
from sage.kernel.operators import MapOperator
```

**预计文件变更**:
- ✅ 选项1: 15 个 middleware 文件
- ✅ 选项2: 0 个文件（通过兼容层）

---

### Phase 7: 更新 pyproject.toml 依赖

**目标**: 调整包依赖关系

#### sage-libs

```toml
# packages/sage-libs/pyproject.toml

# 修改前
dependencies = [
    "isage-kernel>=0.1.0",  # ❌ 依赖 L3 kernel
    ...
]

# 修改后
dependencies = [
    "isage-common>=0.1.0",  # ✅ 只依赖 L1 common
    # 移除 kernel 依赖
    ...
]

[project.optional-dependencies]
examples = [
    "isage-kernel>=0.1.0",  # 仅示例代码需要执行环境
]
```

#### sage-middleware

```toml
# packages/sage-middleware/pyproject.toml

# 如果使用选项2（kernel兼容层），保持不变
dependencies = [
    "isage-common>=0.1.0",
    "isage-kernel>=0.1.0",  # 通过兼容层使用函数接口
    ...
]

# 如果使用选项1（直接导入common），可以考虑移除kernel
dependencies = [
    "isage-common>=0.1.0",
    "isage-platform>=0.1.0",
    # kernel 作为可选依赖
    ...
]
```

**预计文件变更**:
- 🔧 修改: `packages/sage-libs/pyproject.toml`
- 🔧 修改: `packages/sage-middleware/pyproject.toml` (可选)

---

### Phase 8: 测试和验证

```bash
# 1. 运行所有测试
cd packages/sage-common && pytest tests/
cd packages/sage-kernel && pytest tests/
cd packages/sage-libs && pytest tests/
cd packages/sage-middleware && pytest tests/

# 2. 检查导入
python -c "from sage.common.core.functions import MapFunction, SinkFunction"
python -c "from sage.common.components.debug import PrintSink"
python -c "from sage.kernel.operators import MapOperator"  # 兼容层
python -c "from sage.libs.agentic.agents import LangChainAgentAdapter"
python -c "from sage.libs.foundation.io import KafkaSource"

# 3. 运行架构检查工具
sage-dev check-architecture

# 4. 检查循环依赖
python -c "
import sys
sys.path.insert(0, 'tools')
from lib.dependency_analyzer import analyze_dependencies
analyze_dependencies('packages/')
"

# 5. 测试示例代码
cd examples
python tutorials/01_quick_start.py
python tutorials/02_rag_pipeline.py
```

---

## 📊 影响分析 (修订版)

### 代码变更统计

| 包 | 变更类型 | 文件数 | 影响范围 |
|---|---------|--------|----------|
| sage-common | ✅ 新增 core/functions | ~13 | 函数接口 |
| sage-common | ✅ 新增 components/debug | ~1 | PrintSink |
| sage-kernel | ❌ 删除 kafka_source.py | -1 | 移除重复 |
| sage-kernel | 🔧 更新兼容层 | ~3 | function/, operators/, datastream.py |
| sage-libs | 📝 更新导入 | ~14 | 所有使用函数接口的文件 |
| sage-libs | ✨ 改进 KafkaSource | ~1 | 完整实现 |
| sage-middleware | 📝 更新导入(可选) | ~0-15 | 通过兼容层或直接导入 |
| **总计** | - | **~32-47** | - |

### 依赖关系变化

**修改前**:
```
L1: sage-common (基础工具)
L2: sage-platform (队列、存储、服务)
L3: sage-kernel (执行引擎 + 函数接口) ← 问题：函数接口在L3
    sage-libs → sage-kernel ❌ 同层依赖，只为了函数接口
L4: sage-middleware → sage-kernel ✅ 正常向下依赖
```

**修改后**:
```
L1: sage-common
    ├── core/functions/      ✅ 函数接口下沉到L1
    └── components/debug/    ✅ PrintSink下沉到L1

L2: sage-platform (队列、存储、服务)

L3: sage-kernel (执行引擎) ✅ 不再包含函数接口
    └── 依赖: common (函数接口), platform (队列、服务)

    sage-libs ✅ 现在只依赖 common
    └── 依赖: common (函数接口)

L4: sage-middleware
    └── 依赖: common, platform, kernel, libs
```

**关键改进**:
- ✅ sage-libs (L3) → sage-common (L1) - 清晰的向下依赖
- ✅ sage-kernel (L3) → sage-common (L1) - 使用函数接口
- ✅ 解决了 L3 ↔ L3 的水平依赖问题
- ✅ 函数接口在最底层，任何包都可以使用

### 优点

1. ✅ **彻底解决同层依赖**: sage-libs 不再依赖 sage-kernel
2. ✅ **函数接口最大复用**: 在 L1 层，所有包都可以安全使用
3. ✅ **架构更清晰**: 接口(L1) → 平台服务(L2) → 执行引擎(L3) → 领域组件(L4)
4. ✅ **简化依赖链**: libs 只需 common，不需 platform 或 kernel
5. ✅ **向后兼容**: kernel 保留兼容层，不破坏现有代码
6. ✅ **删除重复代码**: KafkaSource 只保留一个实现

### 缺点/风险

1. ⚠️  **common 包变大**: 从基础工具扩展到函数接口
   - 缓解: functions 作为 core 子模块，职责清晰
2. ⚠️  **短期工作量**: 需要更新 ~32-47 个文件
   - 缓解: 大部分是简单的导入路径替换
3. ⚠️  **测试覆盖**: 需要全面测试确保没有遗漏
   - 缓解: 保留兼容层，渐进式验证
4. ⚠️  **KafkaSource 迁移**: 需要将完整实现从 kernel 迁移到 libs
   - 缓解: 代码已经存在，只需复制粘贴

---

## ✅ 决策结果 (2025-10-24)

### 1. kafka_source.py - 删除重复实现 ✅

**决定**: 删除 `sage.kernel.api.function.kafka_source.py`

**理由**:
1. **重复实现**:
   - `sage-kernel`: KafkaSourceFunction (完整实现，202行)
   - `sage-libs`: KafkaSource (占位符，仅24行)
2. **未被使用**:
   - kernel 中的实现只在 `base_environment.from_kafka_source()` 中使用
   - libs 中的实现是占位符
3. **简化架构**:
   - Kafka 是具体功能，不是基础接口
   - 应该在应用层（libs 或 middleware）提供

**行动**:
- ❌ 删除: `packages/sage-kernel/src/sage/kernel/api/function/kafka_source.py`
- ✅ 保留/改进: `packages/sage-libs/src/sage/libs/io/source.py` 中的 KafkaSource
- 📝 更新: `base_environment.from_kafka_source()` 调用 libs 中的实现

---

### 2. _internal_print_sink.py - 下移到 L1 (common) ✅

**决定**: 迁移到 `sage-common`

**理由**:
1. **SinkFunction 应该在更低层**:
   - sage-libs 依赖 SinkFunction（io/sink.py）
   - SinkFunction 是基础接口，应该在 L1 或 L2
   - _internal_print_sink 也应该跟随 SinkFunction
2. **打破依赖链**:
   - 当前: libs → kernel (为了 SinkFunction)
   - 目标: libs → common (SinkFunction 在 common)
3. **通用性**:
   - Print sink 是通用调试工具
   - 不依赖执行引擎

**行动**:
- ✅ 迁移 SinkFunction → `sage-common/core/functions/`
- ✅ 迁移 _internal_print_sink → `sage-common/components/debug/`
- ✅ kernel 从 common 导入使用

---

### 3. 一次性迁移 ✅

**决定**: 一次性完成所有迁移（保留兼容层）

**理由**:
- 快速完成，避免长期维护中间状态
- 保留兼容层确保不破坏现有代码
- 后续可以逐步移除 deprecated warnings

---

### 4. sage-libs 完全移除对 kernel 的依赖 ✅

**决定**: 是的，libs 不应该依赖 kernel

**新的依赖关系**:
```toml
# packages/sage-libs/pyproject.toml
dependencies = [
    "isage-common>=0.1.0",    # 基础设施（包括函数接口）
    # 移除: "isage-kernel>=0.1.0"
]

[project.optional-dependencies]
examples = [
    "isage-kernel>=0.1.0",  # 仅用于运行示例
]
```

---

## 🎯 修正后的重构方案

### 核心变更

基于以上决策，重构方案调整为：

1. **函数接口 → L1 (sage-common)** ✅ 更激进的下沉
   - 所有基础函数接口迁移到 common
   - 理由: libs 需要这些接口，而 libs 应该独立于 kernel

2. **删除重复实现** ✅
   - 删除 kernel 中的 KafkaSourceFunction
   - 改进 libs 中的 KafkaSource

3. **operator/transformation 保留** ✅
   - 这些是 runtime 的内部实现
   - 依赖 Packet, TaskContext, Factory 等
   - 保留在 kernel/api/operator 和 kernel/api/transformation

### 更新后的架构分层

```
L1 (sage-common)
├── core/
│   └── functions/          # ✅ 新增: 基础函数接口
│       ├── base_function.py
│       ├── map_function.py
│       ├── filter_function.py
│       ├── sink_function.py
│       ├── source_function.py
│       └── ... (13个接口)
└── components/
    └── debug/              # ✅ 新增: 调试组件
        └── print_sink.py   # 从 _internal_print_sink 迁移

L2 (sage-platform)
├── queue/                  # 消息队列抽象
├── storage/                # KV存储后端
└── service/                # 服务基类

L3 (sage-kernel)
├── api/
│   ├── local_environment.py    # ✅ 保留
│   ├── remote_environment.py   # ✅ 保留
│   ├── datastream.py           # ✅ 保留
│   ├── operator/               # ✅ 保留（内部实现）
│   └── transformation/         # ✅ 保留（转换逻辑）
└── runtime/                    # ✅ 保留（执行引擎）

L3 (sage-libs)
└── io/
    └── source.py              # ✅ KafkaSource（改进实现）
```

### 为什么放在 L1 而不是 L2？

**用户反馈理解**:
> "应该把sink从sage-libs往下推到sage-common? 然后让sage-kernel去引用sage-common里面的sink算子？"

**分析**:
1. **libs 需要函数接口**:
   - sage-libs (L3) 需要继承 MapFunction, SinkFunction 等
   - 如果放 L2，libs 仍然需要依赖 platform
   - 放 L1 更彻底，libs 只依赖 common

2. **函数接口是"纯抽象"**:
   - 没有业务逻辑
   - 没有外部依赖
   - 只是定义接口契约
   - 符合 common 的"基础设施"定位

3. **kernel 也需要**:
   - kernel 的 operator 需要调用用户定义的 Function
   - 如果 Function 在 common，kernel 可以安全导入
   - 避免 L3 ↔ L3 依赖

**结论**: 函数接口放 L1 (common) 是正确的 ✅

---

## ✅ 下一步行动

### 立即行动

1. **获得共识** - 在 Issue #1041 中讨论方案
2. **回答问题** - 确定 kafka_source 和 _internal_print_sink 的处理方式
3. **创建分支** - `feature/kernel-refactoring-1041`

### 执行步骤

1. ✅ Phase 1: 创建 sage-platform/api (1-2 小时)
2. ✅ Phase 2: 更新 sage-kernel 兼容层 (0.5 小时)
3. ✅ Phase 3: 更新 sage-libs 导入 (1 小时)
4. ✅ Phase 4: 更新 sage-middleware 导入 (1 小时)
5. ✅ Phase 5: 更新 pyproject.toml (0.5 小时)
6. ✅ Phase 6: 测试和验证 (2-3 小时)
7. ✅ Phase 7: 更新文档 (1-2 小时)

**预计总时间**: 7-10 小时

---

## 📚 参考文档

- [Package Architecture](../package-architecture.md) - 当前架构文档
- [L2 Layer Analysis](../L2_LAYER_ANALYSIS.md) - L2 层分析
- [RPC Queue Refactoring](../RPC_QUEUE_REFACTORING_2025.md) - 工厂模式参考
- [Architecture Review 2025](../ARCHITECTURE_REVIEW_2025.md) - 架构评审

---

## 💬 讨论记录

### 2025-10-24 - 初始提案

**提出者**: @用户  
**问题**: kernel 的 api 和 operators 应该和 BaseService 放在同一层

**分析结果**:
- ✅ sage-libs 确实依赖了 kernel (14次导入)
- ✅ 这些导入都是函数接口（MapFunction, SinkFunction等）
- ✅ BaseService 已在 L2 (sage-platform)
- ✅ 函数接口应该也在 L2

**建议**: 将 kernel.api.function 迁移到 platform.api

---

_最后更新: 2025-10-24_
