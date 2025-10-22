# SAGE Studio 架构重构方案

## 问题识别

当前 sage-studio 有自己的 `FlowEngine`，这是**架构错误**：

```python
# ❌ 错误：Studio 自己实现执行引擎
class FlowEngine:
    async def execute_flow(self, flow: FlowDefinition, ...):
        # 自己的节点执行、依赖解析、调度...
```

### 问题
1. **重复造轮**：SAGE 已有完整的 DataStream 引擎
2. **功能缺失**：Studio 的简易引擎缺少容错、分布式、状态管理等核心能力
3. **维护负担**：两套执行引擎
4. **架构割裂**：Studio 与 SAGE 核心脱节

## 正确架构

### 原则
**Studio 是 SAGE 的可视化界面，不是独立的执行系统**

```
┌─────────────────────────────────────────┐
│     SAGE Studio (Web UI Layer)          │
│  - 可视化 Pipeline 编辑器                │
│  - 节点拖拽和连接                         │
│  - 参数配置界面                           │
│  - 执行监控和日志展示                     │
└─────────────┬───────────────────────────┘
              │ 直接使用
              │
┌─────────────▼───────────────────────────┐
│         SAGE Core Engine                 │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  DataStream API                    │ │
│  │  env.add_source()                  │ │
│  │     .map(Operator)                 │ │
│  │     .filter(Operator)              │ │
│  │     .sink(Sink)                    │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Execution Environment             │ │
│  │  - LocalStreamEnvironment          │ │
│  │  - DistributedEnvironment          │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  Operators                         │ │
│  │  - kernel/operators (基础)         │ │
│  │  - middleware/operators (领域)     │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

## 重构方案

### Step 1: Studio 定义数据模型（UI 层）

Studio 只负责**描述** Pipeline，不负责执行：

```python
# packages/sage-studio/src/sage/studio/models/pipeline_model.py

@dataclass
class VisualNode:
    """可视化节点模型（UI 表示）"""
    id: str
    type: str  # "rag.generator", "rag.retriever", etc.
    label: str
    position: Dict[str, float]  # UI 位置 {x, y}
    config: Dict[str, Any]  # 节点配置参数
    
@dataclass  
class VisualConnection:
    """可视化连接模型（UI 表示）"""
    source_node: str
    source_port: str
    target_node: str
    target_port: str

@dataclass
class VisualPipeline:
    """可视化 Pipeline 模型（UI 表示）"""
    id: str
    name: str
    nodes: List[VisualNode]
    connections: List[VisualConnection]
    
    def to_sage_pipeline(self) -> 'SagePipeline':
        """转换为 SAGE 可执行的 Pipeline"""
        # 将 UI 模型转换为 SAGE API 调用
        pass
```

### Step 2: 转换为 SAGE Pipeline（转换层）

```python
# packages/sage-studio/src/sage/studio/core/pipeline_builder.py

from sage.kernel.api.local_environment import LocalStreamEnvironment
from sage.middleware.operators.rag import OpenAIGenerator, ChromaRetriever
from sage.libs.io_utils.source import DataSource
from sage.libs.io_utils.sink import DataSink

class SagePipelineBuilder:
    """将 Studio 的可视化模型转换为 SAGE Pipeline"""
    
    def __init__(self):
        # 注册节点类型到算子的映射
        self.node_registry = {
            "rag.generator": OpenAIGenerator,
            "rag.retriever": ChromaRetriever,
            "llm.vllm": VLLMGenerator,
            # ...
        }
    
    def build(self, visual_pipeline: VisualPipeline) -> BaseEnvironment:
        """
        从可视化模型构建 SAGE Pipeline
        
        Returns:
            配置好的 SAGE 执行环境
        """
        env = LocalStreamEnvironment()
        
        # 1. 拓扑排序节点
        sorted_nodes = self._topological_sort(visual_pipeline)
        
        # 2. 构建 DataStream
        stream = None
        for node in sorted_nodes:
            operator_class = self.node_registry[node.type]
            
            if stream is None:
                # 第一个节点（source）
                stream = env.add_source(
                    self._create_source(node),
                    name=node.label
                )
            else:
                # 后续节点（transformation）
                stream = stream.map(
                    operator_class,
                    config=node.config
                )
        
        # 3. 添加 sink
        if stream:
            stream.sink(self._create_sink(visual_pipeline))
        
        return env
    
    def _topological_sort(self, pipeline: VisualPipeline) -> List[VisualNode]:
        """根据连接关系进行拓扑排序"""
        # TODO: 实现拓扑排序
        pass
```

### Step 3: Studio 后端使用 SAGE API（执行层）

```python
# packages/sage-studio/src/sage/studio/api/pipeline_execution.py

from sage.studio.core.pipeline_builder import SagePipelineBuilder
from sage.studio.models.pipeline_model import VisualPipeline

class PipelineExecutionService:
    """Pipeline 执行服务"""
    
    def __init__(self):
        self.builder = SagePipelineBuilder()
        self.running_jobs = {}
    
    async def execute_pipeline(self, visual_pipeline: VisualPipeline, inputs: Dict[str, Any]):
        """
        执行 Pipeline
        
        直接使用 SAGE 引擎，不需要自己的执行逻辑
        """
        # 1. 构建 SAGE Pipeline
        env = self.builder.build(visual_pipeline)
        
        # 2. 设置输入
        # TODO: 处理输入数据
        
        # 3. 执行（使用 SAGE 引擎）
        job = env.execute()
        
        # 4. 跟踪执行状态
        self.running_jobs[job.job_id] = {
            "visual_pipeline": visual_pipeline,
            "job": job,
            "status": job.status
        }
        
        return {
            "job_id": job.job_id,
            "status": job.status.value
        }
    
    def get_job_status(self, job_id: str):
        """获取 Job 状态（从 SAGE 引擎）"""
        if job_id in self.running_jobs:
            job = self.running_jobs[job_id]["job"]
            return {
                "job_id": job_id,
                "status": job.status.value,
                "progress": job.progress,
                # SAGE 引擎提供的状态信息
            }
        return None
```

### Step 4: 前端调用（不变）

```typescript
// packages/sage-studio/frontend/src/services/api.ts

export async function executePipeline(pipeline: VisualPipeline, inputs: any) {
  // 前端仍然调用 Studio API
  const response = await fetch('/api/pipelines/execute', {
    method: 'POST',
    body: JSON.stringify({ pipeline, inputs })
  });
  
  // 但底层已经是 SAGE 引擎在执行
  return response.json();
}
```

## 实现步骤

### Phase 1: 基础框架
- [ ] 删除 `FlowEngine` 
- [ ] 创建 `VisualPipeline` 数据模型
- [ ] 创建 `SagePipelineBuilder` 转换器
- [ ] 实现基本的 node → operator 映射

### Phase 2: 核心功能
- [ ] 实现拓扑排序和依赖解析
- [ ] 处理不同类型的节点（source, transformation, sink）
- [ ] 实现配置参数传递
- [ ] 处理输入输出数据映射

### Phase 3: 高级特性
- [ ] 支持分布式执行（使用 SAGE 的 DistributedEnvironment）
- [ ] 集成容错机制（使用 SAGE 的 fault tolerance）
- [ ] 状态管理和检查点（使用 SAGE 的 state management）
- [ ] 实时监控和日志（使用 SAGE 的 monitoring）

### Phase 4: 优化和增强
- [ ] Pipeline 模板和预设
- [ ] 参数验证和类型检查
- [ ] 性能分析和优化建议
- [ ] 可视化调试工具

## 架构优势

### ✅ 统一性
- Studio 只是 SAGE 的 UI，不是独立系统
- 所有执行都通过 SAGE 引擎
- 一致的行为和结果

### ✅ 功能完整
- 自动获得 SAGE 的所有能力
- 容错、分布式、状态管理等开箱即用
- 无需重复实现

### ✅ 可维护性
- Studio 专注于 UI 和用户体验
- 执行逻辑由 SAGE 核心维护
- 清晰的职责分离

### ✅ 扩展性
- 新增算子自动在 Studio 可用
- SAGE 引擎的改进自动惠及 Studio
- 易于添加新功能

## 核心原则

1. **Studio 不执行，只描述**
   - Studio 定义"要做什么"（声明式）
   - SAGE 引擎执行"怎么做"（执行式）

2. **单一执行引擎**
   - 只有 SAGE 引擎
   - Studio 是它的可视化前端

3. **薄 UI 层**
   - Studio 只处理可视化和用户交互
   - 不包含业务逻辑和执行逻辑

4. **直接集成**
   - 不需要适配器层
   - 直接调用 SAGE API

## 文件清理

需要删除或重构：
- ❌ `packages/sage-studio/src/sage/studio/core/flow_engine.py` - 删除整个 FlowEngine
- ❌ `packages/sage-studio/src/sage/studio/adapters/kernel_adapter.py` - 不需要适配器
- ✅ 创建 `packages/sage-studio/src/sage/studio/models/pipeline_model.py` - 数据模型
- ✅ 创建 `packages/sage-studio/src/sage/studio/core/pipeline_builder.py` - Pipeline 构建器
- ✅ 重构 `packages/sage-studio/src/sage/studio/api/` - 使用 SAGE API

## 总结

**正确的架构**：
```
Studio (UI) → SAGE API → SAGE Engine
     描述         调用        执行
```

**错误的架构**：
```
Studio (UI) → Studio Engine → ??? 
                  重复实现      与SAGE脱节
```

Studio 应该是 SAGE 的**前端**，不是**另一个执行系统**。
