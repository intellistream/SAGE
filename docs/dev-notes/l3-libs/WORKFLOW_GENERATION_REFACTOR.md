# Workflow Generation 重构总结

## 🎯 重构目标

将分散在各处的工作流生成代码统一到 `sage-libs` 中，形成完整的**生成 + 优化**研究框架。

## ✅ 已完成的工作

### 1. 创建统一的生成框架 (sage-libs)

**位置**: `packages/sage-libs/src/sage/libs/agentic/workflow/generators/`

**新增文件**:

```
generators/
├── __init__.py                    # 模块导出
├── base.py                        # 基类和数据结构
│   ├── GenerationStrategy (枚举)
│   ├── GenerationContext (输入)
│   ├── GenerationResult (输出)
│   └── BaseWorkflowGenerator (基类)
│
├── rule_based_generator.py        # 规则生成器
│   └── RuleBasedWorkflowGenerator
│       - 关键词匹配
│       - 意图识别
│       - 预定义模板
│
├── llm_generator.py               # LLM 生成器
│   └── LLMWorkflowGenerator
│       - 集成 Pipeline Builder
│       - RAG 增强
│       - 智能理解
│
├── examples.py                    # 使用示例
└── README.md                      # 完整文档
```

**核心设计**:

```python
# 统一的接口
class BaseWorkflowGenerator(ABC):
    @abstractmethod
    def generate(self, context: GenerationContext) -> GenerationResult:
        pass

# 标准的输入输出
@dataclass
class GenerationContext:
    user_input: str
    conversation_history: list[dict]
    constraints: dict
    preferences: dict

@dataclass
class GenerationResult:
    success: bool
    visual_pipeline: dict  # Studio 格式
    raw_plan: dict         # Kernel 格式
    confidence: float
    detected_intents: list[str]
    explanation: str
    ...
```

### 2. 更新 workflow 模块导出

**文件**: `packages/sage-libs/src/sage/libs/agentic/workflow/__init__.py`

**变更**:

```python
# 新增 Generation 相关导出
from .generators import (
    BaseWorkflowGenerator,
    GenerationContext,
    GenerationResult,
    GenerationStrategy,
    LLMWorkflowGenerator,
    RuleBasedWorkflowGenerator,
)

__all__ = [
    # === Workflow Generation ===
    "BaseWorkflowGenerator",
    "GenerationContext",
    "GenerationResult",
    # ...

    # === Workflow Optimization ===  (保持原有)
    "WorkflowGraph",
    "BaseOptimizer",
    # ...
]
```

### 3. 简化 Studio 集成

**文件**: `packages/sage-studio/src/sage/studio/services/workflow_generator.py`

**重构前**: 300+ 行，包含大量生成逻辑
**重构后**: 200 行，仅作为 sage-libs 的包装器

```python
class WorkflowGenerator:
    """Studio 包装器 - 调用 sage-libs 生成器"""

    def generate(self, request):
        # 构建 GenerationContext
        context = GenerationContext(...)

        # 调用 sage-libs 生成器
        if request.use_llm:
            result = LLMWorkflowGenerator().generate(context)
        else:
            result = RuleBasedWorkflowGenerator().generate(context)

        # 转换为 Studio 格式
        return self._convert_result(result)
```

### 4. 更新 API 端点

**文件**: `packages/sage-studio/src/sage/studio/config/backend/api.py`

**新增端点**:

```python
@app.post("/api/chat/generate-workflow")
async def generate_workflow_advanced(request: WorkflowGenerateRequest):
    """使用 LLM 生成工作流（高级版）"""
    result = generate_workflow_from_chat(
        user_input=request.user_input,
        session_messages=session_messages,
        enable_optimization=request.enable_optimization,
    )
    return result
```

## 📊 代码迁移对比

### 之前的分散状态

```
sage-gateway/rag_pipeline.py
├── _detect_workflow_intent()      # 意图检测
├── _generate_workflow()           # 工作流生成
└── _convert_to_visual_pipeline()  # 格式转换

sage-studio/chat_pipeline_recommender.py
├── _detect_intents()              # 意图检测（重复）
├── _build_graph()                 # 构建图（重复）
└── generate_pipeline_recommendation()

sage-cli/pipeline.py
└── PipelinePlanGenerator          # LLM 生成（分离）

问题:
- 代码重复
- 逻辑分散
- 难以扩展
- 不利于研究
```

### 现在的统一状态

```
sage-libs/workflow/generators/
├── base.py                        # 统一接口
├── rule_based_generator.py        # 规则生成
├── llm_generator.py               # LLM 生成
└── (未来) template_generator.py   # 模板生成
    (未来) hybrid_generator.py      # 混合生成
    (未来) learning_generator.py    # 学习生成

sage-studio/workflow_generator.py  # 简单包装
sage-gateway/rag_pipeline.py       # 可以调用 sage-libs

优势:
✅ 代码集中
✅ 接口统一
✅ 易于扩展
✅ 便于研究
```

## 🔬 研究价值

### 现在可以轻松研究：

1. **不同生成策略对比**
   ```python
   rule_gen = RuleBasedWorkflowGenerator()
   llm_gen = LLMWorkflowGenerator()

   # 同一输入，比较结果
   rule_result = rule_gen.generate(context)
   llm_result = llm_gen.generate(context)

   compare_metrics(rule_result, llm_result)
   ```

2. **新生成算法开发**
   ```python
   class TemplateWorkflowGenerator(BaseWorkflowGenerator):
       def generate(self, context):
           # 实现基于模板的生成
           ...
   ```

3. **评估和基准测试**
   ```python
   from sage.libs.agentic.workflow import WorkflowEvaluator

   evaluator = WorkflowEvaluator()
   metrics = evaluator.evaluate_generation(
       generated=result.visual_pipeline,
       ground_truth=expected
   )
   ```

## 📈 下一步计划

### 短期 (1-2 周)

- [ ] 添加单元测试
- [ ] 完善文档和示例
- [ ] 集成到 Studio UI

### 中期 (1-2 月)

- [ ] 实现 TemplateWorkflowGenerator
- [ ] 实现 HybridWorkflowGenerator
- [ ] 打通 Generation → Optimization 流程
- [ ] 添加评估基准

### 长期 (3-6 月)

- [ ] 基于用户反馈的学习生成器
- [ ] 多模态输入支持（图像、语音）
- [ ] 自动化测试和验证
- [ ] 论文发表

## 🎓 使用指南

### 对于 Studio 用户

在 Chat 界面输入：
```
"帮我创建一个 RAG 工作流"
```

系统会自动：
1. 检测意图
2. 选择合适的生成器（规则或 LLM）
3. 生成工作流
4. 在画布中展示

### 对于研究人员

```python
# 1. 导入生成器
from sage.libs.agentic.workflow.generators import (
    RuleBasedWorkflowGenerator,
    LLMWorkflowGenerator
)

# 2. 创建上下文
from sage.libs.agentic.workflow import GenerationContext

context = GenerationContext(
    user_input="your requirement",
    constraints={"max_cost": 100}
)

# 3. 生成工作流
generator = LLMWorkflowGenerator()
result = generator.generate(context)

# 4. 分析结果
print(f"Confidence: {result.confidence}")
print(f"Intents: {result.detected_intents}")
print(f"Time: {result.generation_time}s")
```

### 对于开发者

```python
# 实现新的生成策略
from sage.libs.agentic.workflow.generators.base import (
    BaseWorkflowGenerator,
    GenerationStrategy
)

class MyGenerator(BaseWorkflowGenerator):
    def __init__(self):
        super().__init__(GenerationStrategy.CUSTOM)

    def generate(self, context):
        # 你的逻辑
        ...
        return GenerationResult(...)
```

## 🏆 主要优势

| 方面 | 之前 | 现在 |
|------|------|------|
| **代码位置** | 分散在 3+ 个包 | 集中在 sage-libs |
| **代码重复** | 高（多处重复逻辑） | 低（统一实现） |
| **扩展性** | 困难（需改多处） | 容易（继承基类） |
| **可测试性** | 低（耦合严重） | 高（接口清晰） |
| **研究价值** | 低（难以对比） | 高（便于实验） |
| **维护成本** | 高 | 低 |

## 📝 迁移清单

### 需要更新的文件

- [x] sage-libs/workflow/__init__.py
- [x] sage-libs/workflow/generators/__init__.py
- [x] sage-libs/workflow/generators/base.py
- [x] sage-libs/workflow/generators/rule_based_generator.py
- [x] sage-libs/workflow/generators/llm_generator.py
- [x] sage-libs/workflow/generators/examples.py
- [x] sage-libs/workflow/generators/README.md
- [x] sage-studio/services/workflow_generator.py
- [x] sage-studio/services/__init__.py
- [x] sage-studio/config/backend/api.py

### 可以考虑更新的文件（可选）

- [ ] sage-gateway/rag_pipeline.py (改为调用 sage-libs)
- [ ] sage-studio/chat_pipeline_recommender.py (改为调用 sage-libs)
- [ ] 添加集成测试
- [ ] 更新文档

## 💡 设计原则

1. **分层清晰**: L3 (libs) 提供算法，L6 (studio) 提供包装
2. **接口统一**: 所有生成器遵循相同接口
3. **易于扩展**: 新策略只需继承基类
4. **便于研究**: 标准化的评估和对比
5. **向后兼容**: 不破坏现有功能

## 🚀 示例代码

完整示例见：
- `packages/sage-libs/src/sage/libs/agentic/workflow/generators/examples.py`
- `packages/sage-libs/src/sage/libs/agentic/workflow/generators/README.md`

## 📞 联系

如有问题或建议，请联系 SAGE Team 或提交 Issue。
