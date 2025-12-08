# SAGE 集成 sageLLM Control Plane 建议

**Date**: 2025-11-04  
**Author**: SAGE Development Team  
**Summary**: Integration proposal for sageLLM Control Plane into SAGE main project, enabling intelligent LLM request scheduling, multi-instance management, and PD separation optimization

## 当前状态

**SAGE 主项目** 目前通过 `sage.common.components.sage_llm.VLLMService` 使用 vLLM：
- 直接调用 vLLM LLM 类进行推理
- 单实例模式，没有负载均衡
- 缺少智能调度、路由、PD 分离等高级功能

**sageLLM Control Plane** 提供的高级功能：
- ✅ 5种智能调度策略（FIFO、Priority、SLO-Aware、Cost-Optimized、Adaptive）
- ✅ PD 分离优化（+50-80% 吞吐，-50-60% 延迟）
- ✅ 多实例管理和负载均衡
- ✅ 动态并行策略选择
- ✅ 拓扑感知路由（NVLINK、NUMA）
- ✅ 完整的测试和 CI/CD 基础设施

## 集成方案

### 方案 1：创建 ControlPlaneVLLMService（推荐）

在 `sage.common.components.sage_llm` 中添加新的服务类：

```python
# sage/common/components/sage_llm/control_plane_service.py
from sage.common.service import BaseService
from sage.common.components.sage_llm.sageLLM.control_plane import (
    ControlPlaneManager,
    RequestMetadata,
    RequestPriority,
    ExecutionInstance,
)

class ControlPlaneVLLMService(BaseService):
    """使用 sageLLM Control Plane 的高级 vLLM 服务"""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self.control_plane = None

    def setup(self) -> None:
        # 初始化 Control Plane Manager
        self.control_plane = ControlPlaneManager(
            scheduling_policy=self.config.get("scheduling_policy", "adaptive"),
            enable_pd_separation=self.config.get("enable_pd_separation", True),
        )

        # 注册 vLLM 实例
        for instance_config in self.config.get("instances", []):
            instance = ExecutionInstance(
                instance_id=instance_config["instance_id"],
                host=instance_config["host"],
                port=instance_config["port"],
                model_name=instance_config["model_name"],
                tensor_parallel_size=instance_config.get("tensor_parallel_size", 1),
                # ...
            )
            self.control_plane.register_instance(instance)

    async def process(self, payload: dict[str, Any]) -> Any:
        task = payload.get("task", "generate")

        if task == "generate":
            # 转换为 RequestMetadata
            request = RequestMetadata(
                request_id=...,
                prompt=payload["inputs"],
                priority=RequestPriority[payload.get("priority", "NORMAL")],
                slo_deadline_ms=payload.get("slo_deadline_ms"),
                max_tokens=payload.get("max_tokens", 512),
            )

            # 提交到 Control Plane
            request_id = await self.control_plane.submit_request(request)
            result = await self.control_plane.wait_for_result(request_id)
            return result

        # ... 其他任务
```

### 方案 2：扩展现有 VLLMService

在现有 `VLLMService` 中添加可选的 Control Plane 模式：

```python
# sage/common/components/sage_llm/service.py

class VLLMService(BaseService):
    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = VLLMServiceConfig.from_dict(config)

        # 新增：检查是否使用 Control Plane 模式
        if self.config.use_control_plane:
            self._init_control_plane()
        else:
            self._text_engine = None
            self._embedding_engine = None

    def _init_control_plane(self):
        from sage.common.components.sage_llm.sageLLM.control_plane import (
            ControlPlaneManager
        )
        self.control_plane = ControlPlaneManager(...)
```

## 需要更新的文件

### 1. 新增文件
```
packages/sage-common/src/sage/common/components/sage_llm/
├── control_plane_service.py  # 新的 Control Plane 服务
└── __init__.py               # 更新导出
```

### 2. 更新文件
```
packages/sage-common/src/sage/common/components/sage_llm/
├── __init__.py               # 添加 ControlPlaneVLLMService 导出
└── service.py                # （可选）扩展现有服务

packages/sage-common/src/sage/common/components/__init__.py
└── 添加 ControlPlaneVLLMService 导出

docs-public/docs_src/
├── api-reference/common/index.md  # 更新 API 文档
└── guides/                        # 添加 Control Plane 使用指南
```

### 3. 配置示例

```toml
# config/services.toml
[services.llm_control_plane]
type = "ControlPlaneVLLMService"
scheduling_policy = "adaptive"     # adaptive, slo_aware, priority, fifo, cost_optimized
enable_pd_separation = true        # 启用 Prefilling/Decoding 分离
routing_strategy = "load_balanced" # load_balanced, affinity, locality, topology_aware

[[services.llm_control_plane.instances]]
instance_id = "llm-prefill-1"
host = "localhost"
port = 8000
model_name = "meta-llama/Llama-2-7b"
instance_type = "PREFILLING"
tensor_parallel_size = 4

[[services.llm_control_plane.instances]]
instance_id = "llm-decode-1"
host = "localhost"
port = 8001
model_name = "meta-llama/Llama-2-7b"
instance_type = "DECODING"
tensor_parallel_size = 1
```

## 迁移路径

### 阶段 1：并存（推荐先做这个）
- 保留现有 `VLLMService`（简单场景）
- 新增 `ControlPlaneVLLMService`（高级场景）
- 用户根据需求选择

### 阶段 2：逐步迁移
- 更新文档和示例
- 在示例应用中演示 Control Plane 用法
- 收集用户反馈

### 阶段 3：统一（可选）
- 将 `VLLMService` 标记为简化版
- 推荐新用户使用 `ControlPlaneVLLMService`

## 测试计划

1. **单元测试**：在 `packages/sage-common/tests/unit/components/sage_llm/` 添加测试
2. **集成测试**：测试与现有 SAGE 组件的集成
3. **性能测试**：验证 Control Plane 带来的性能提升
4. **向后兼容测试**：确保现有代码继续工作

## 预期收益

1. **性能提升**：
   - PD 分离：+50-80% 吞吐，-50-60% 延迟
   - 智能调度：更好的 SLO 满足率
   - 负载均衡：更高的资源利用率

2. **功能增强**：
   - 多实例支持
   - 优先级调度
   - 故障容错
   - 性能监控

3. **开发体验**：
   - 完整的测试覆盖（164+ 测试）
   - CI/CD 集成
   - 详细的文档

## 建议

**现在就做**：
1. ✅ sageLLM Control Plane 已经完成测试和文档
2. 创建 `ControlPlaneVLLMService` 作为新选项
3. 添加配置示例和文档
4. 在一个示例应用中演示用法

**不建议现在做**：
1. ❌ 不要立即替换现有 `VLLMService`
2. ❌ 不要强制所有用户迁移
3. ❌ 保持向后兼容

## 下一步

1. **Review**：团队审查这个提案
2. **Demo**：创建一个集成示例
3. **Document**：编写集成指南
4. **Implement**：实现 `ControlPlaneVLLMService`
5. **Test**：完整的测试覆盖
6. **Release**：作为新功能发布
