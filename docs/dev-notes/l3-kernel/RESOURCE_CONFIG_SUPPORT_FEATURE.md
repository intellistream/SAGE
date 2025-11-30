# 添加算子级别的资源配置支持

**Date**: 2025-11-04  
**Author**: SAGE Team  
**Summary**: 为 Kernel 算子（map/filter等）添加细粒度资源配置支持（CPU、GPU、内存），提升分布式场景下的资源利用效率

## 问题描述

当前 SAGE Kernel 的 `map()`、`filter()` 等算子方法仅支持 `parallelism` 参数来控制并行度，但不支持细粒度的资源分配（如 CPU、内存、GPU 数量）。

在分布式场景下，不同算子可能有不同的资源需求：

- CPU 密集型算子需要更多 CPU 核心
- GPU 推理算子需要 GPU 资源
- 内存密集型算子需要更大内存

## 期望行为

希望能够为每个算子实例指定资源需求：

```python
from sage.kernel.api import RemoteEnvironment

env = RemoteEnvironment(name="my_app", host="127.0.0.1", port=19001)

stream = (
    env.from_source(source)
    .map(
        HeavyComputeOperator(),
        parallelism=4,
        resources={
            "num_cpus": 4,      # 每个实例分配 4 个 CPU 核心
            "memory": "8GB"      # 每个实例分配 8GB 内存
        }
    )
    .map(
        GPUInferenceOperator(),
        parallelism=2,
        resources={
            "num_gpus": 1,      # 每个实例分配 1 个 GPU
            "num_cpus": 2       # 每个实例分配 2 个 CPU 核心
        }
    )
    .sink(sink)
)

env.execute()
```

## 当前行为

当前只能设置 `parallelism`：

```python
stream = (
    env.from_source(source)
    .map(HeavyComputeOperator(), parallelism=4)   # ✅ 支持
    .map(GPUInferenceOperator(), parallelism=2)   # ✅ 支持
    .sink(sink)
)
```

## 实现建议

### 1. 修改 API 签名

**文件**: `packages/sage-kernel/src/sage/kernel/api/datastream.py`

```python
def map(
    self,
    function: type[BaseFunction] | Callable,
    *args,
    parallelism: int | None = None,
    resources: dict | None = None,  # 新增参数
    **kwargs,
) -> DataStream:
    # ...
```

### 2. 更新 Transformation 类

**文件**: `packages/sage-kernel/src/sage/kernel/api/transformation/base_transformation.py`

```python
class BaseTransformation:
    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        name: str | None = None,
        parallelism: int = 1,
        resources: dict | None = None,  # 新增参数
        **kwargs,
    ):
        # ...
        self.parallelism = parallelism
        self.resources = resources or {}  # 存储资源配置
```

### 3. 传递资源配置到 Ray

在创建 Ray 任务时使用资源配置：

```python
# 在 Operator 或 Runtime 中
@ray.remote(**self.resources)  # 使用配置的资源
class ParallelTask:
    # ...
```

### 4. 支持的资源类型

参考 Ray 的资源规范：

```python
resources = {
    "num_cpus": int,           # CPU 核心数
    "num_gpus": int,           # GPU 数量
    "memory": str,             # 内存大小 (如 "8GB")
    "object_store_memory": str, # 对象存储内存
    "resources": dict,         # 自定义资源
}
```

## 相关文件

需要修改的文件：

1. `packages/sage-kernel/src/sage/kernel/api/datastream.py` - 添加 resources 参数
1. `packages/sage-kernel/src/sage/kernel/api/transformation/base_transformation.py` - 存储资源配置
1. `packages/sage-kernel/src/sage/kernel/runtime/` - 在运行时应用资源配置

## 优先级

**Medium** - 这是分布式场景下的重要功能，但当前可以通过调整集群整体资源和并行度来暂时解决。

## 标签

- `enhancement`
- `kernel`
- `distributed`
- `ray`

## 相关文档

- 文档位置: `docs-public/docs_src/tutorials/advanced/distributed-pipeline.md`
- Ray 资源文档: https://docs.ray.io/en/latest/ray-core/scheduling/resources.html
