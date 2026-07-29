"""Pipeline-as-Service 基础设施

这个模块提供了将 Pipeline 包装为 Service 的通用组件，
实现了 Pipeline-as-Service 模式的完整基础设施。

【核心组件】：
- PipelineBridge: 连接 Service 调用方和 Pipeline 实现的桥梁
- PipelineServiceSource: 从 Bridge 拉取请求的通用 Source
- PipelineServiceSink: 将结果返回到 Bridge 的通用 Sink
- PipelineService: 将 Pipeline 包装为 Service 的通用包装器

【使用示例】：

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.service.pipeline_service import (
    PipelineBridge,
    PipelineServiceSource,
    PipelineServiceSink,
    PipelineService,
)

# 创建环境
env = LocalEnvironment('demo')

# 创建 Bridge
bridge = PipelineBridge()

# 注册 Pipeline Service
env.register_service('my_pipeline', PipelineService, bridge)

# 创建服务 Pipeline（实际处理逻辑）
env.from_source(PipelineServiceSource, bridge) \\
   .map(YourCustomMapFunction) \\
   .sink(PipelineServiceSink)

# 主 Pipeline 可以通过 call_service() 调用
# result = self.call_service('my_pipeline', data)
```

【特性】：
- 自动背压控制：调用方会阻塞直到 Pipeline 完成
- 优雅关闭：通过 StopSignal 自动停止 Pipeline
- 双向通信：通过 response_queue 实现异步返回
- 高复用性：适用于任何需要 Pipeline-as-Service 的场景
"""

from .pipeline_bridge import PipelineBridge, PipelineRequest
from .pipeline_service import PipelineService
from .pipeline_sink import PipelineServiceSink
from .pipeline_source import PipelineServiceSource

__all__ = [
    "PipelineBridge",
    "PipelineRequest",
    "PipelineService",
    "PipelineServiceSource",
    "PipelineServiceSink",
]
