# Workflow Generation & Optimization Framework

## 📋 概述

SAGE 工作流框架提供了完整的**生成 + 优化**两阶段流程，用于研究和开发智能工作流算法。

```
用户需求 → [Generation] → 初始工作流 → [Optimization] → 优化后工作流
```

## 🏗️ 架构

### 模块位置

```
sage-libs/src/sage/libs/agentic/workflow/
├── generators/              # 工作流生成算法 (NEW)
│   ├── base.py             # 生成器基类和接口
│   ├── rule_based_generator.py    # 基于规则的生成
│   ├── llm_generator.py           # 基于 LLM 的生成
│   └── examples.py         # 使用示例
│
├── optimizers/              # 工作流优化算法 (EXISTING)
│   ├── greedy.py           # 贪心优化
│   ├── parallelization.py  # 并行化优化
│   └── ...
│
├── base.py                  # WorkflowGraph 定义
├── constraints.py           # 约束检查
├── evaluator.py            # 评估工具
└── examples.py             # 完整示例
```

### 集成到 Studio

```
sage-studio/src/sage/studio/services/
└── workflow_generator.py   # Studio 包装器（调用 sage-libs）
```

## 🎯 两种算法对比

### 1. Workflow Generation（工作流生成）

**目的**: 从自然语言需求创建工作流

**输入**:

- 用户的自然语言描述
- 对话历史（可选）
- 约束条件（成本、延迟、质量）

**输出**:

- Visual Pipeline（Studio 可视化格式）
- Raw Plan（SAGE Kernel 执行格式）

**策略**:

| 策略         | 优点                     | 缺点                 | 适用场景             |
| ------------ | ------------------------ | -------------------- | -------------------- |
| **规则生成** | 快速、可预测、无需 API   | 无法理解复杂需求     | 简单、标准化的工作流 |
| **LLM 生成** | 智能、灵活、理解自然语言 | 慢、需要 API、有成本 | 复杂、创新性需求     |
| **模板生成** | 质量稳定、易维护         | 泛化能力有限         | 常见模式             |
| **混合生成** | 结合多种优点             | 复杂度高             | 生产环境             |

### 2. Workflow Optimization（工作流优化）

**目的**: 优化已有工作流的性能

**输入**:

- 现有的 WorkflowGraph
- 优化目标（降低成本、延迟、提升质量）
- 约束条件

**输出**:

- 优化后的 WorkflowGraph
- 优化指标（成本节省、延迟降低等）

**策略**:

| 策略                | 优化目标      | 方法               |
| ------------------- | ------------- | ------------------ |
| **Greedy**          | 成本优化      | 移除冗余节点       |
| **Parallelization** | 延迟优化      | 识别并行机会       |
| **Model Selection** | 成本/质量平衡 | 替换为更合适的模型 |

## 🚀 使用方法

### 方法 1: 直接使用 sage-libs

```python
from sage.libs.agentic.workflow import GenerationContext
from sage.libs.agentic.workflow.generators import RuleBasedWorkflowGenerator

# 创建生成器
generator = RuleBasedWorkflowGenerator()

# 定义需求
context = GenerationContext(
    user_input="创建一个 RAG 管道用于文档问答",
    constraints={"max_cost": 100}
)

# 生成工作流
result = generator.generate(context)

if result.success:
    visual_pipeline = result.visual_pipeline
    raw_plan = result.raw_plan
```

### 方法 2: 通过 Studio API

```bash
# 启动 Studio
sage studio start

# 调用 API
curl -X POST http://localhost:8080/api/chat/generate-workflow \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "创建一个数据处理管道",
    "session_id": "session-123",
    "enable_optimization": false
  }'
```

### 方法 3: 在 Studio Chat 中使用

在 Studio 的 Chat 界面中，直接输入：

```
"帮我创建一个 RAG 工作流"
```

系统会自动检测意图并调用工作流生成器。

## 🔬 研究方向

### 生成算法研究

1. **意图理解**

   - 如何从模糊的自然语言中准确提取意图？
   - 多意图如何组合？
   - 如何处理歧义？

1. **算子选择**

   - 给定意图，如何选择最合适的算子？
   - 如何考虑算子之间的兼容性？
   - 如何利用历史数据？

1. **参数配置**

   - 如何为算子自动配置合理的参数？
   - 如何从用户描述中提取参数信息？

1. **质量保证**

   - 如何验证生成的工作流是可执行的？
   - 如何估计生成质量？

### 优化算法研究

1. **成本优化**

   - 如何在保证质量的前提下降低 API 调用成本？
   - 缓存策略如何设计？

1. **延迟优化**

   - 如何识别并行化机会？
   - 如何平衡延迟和成本？

1. **质量优化**

   - 如何在成本约束下提升输出质量？
   - 如何选择最佳模型组合？

### 评估方法

```python
from sage.libs.agentic.workflow import WorkflowEvaluator

evaluator = WorkflowEvaluator()

# 评估生成质量
metrics = evaluator.evaluate_generation(
    generated_workflow=result.visual_pipeline,
    ground_truth=expected_workflow,
    user_feedback=user_ratings
)

# 评估优化效果
metrics = evaluator.evaluate_optimization(
    original=original_workflow,
    optimized=optimized_workflow
)
```

## 📊 性能基准

| 生成器     | 平均耗时 | API 调用 | 准确率 |
| ---------- | -------- | -------- | ------ |
| Rule-based | ~0.1s    | 0        | 70%    |
| LLM-driven | ~3s      | 1-2      | 90%    |
| Hybrid     | ~1s      | 0-1      | 85%    |

## 🛠️ 扩展开发

### 添加新的生成策略

1. 创建新的生成器类：

```python
from sage.libs.agentic.workflow.generators.base import (
    BaseWorkflowGenerator,
    GenerationContext,
    GenerationResult,
    GenerationStrategy
)

class MyCustomGenerator(BaseWorkflowGenerator):
    def __init__(self):
        super().__init__(GenerationStrategy.CUSTOM)

    def generate(self, context: GenerationContext) -> GenerationResult:
        # 实现你的生成逻辑
        ...
```

2. 在 `generators/__init__.py` 中导出
1. 添加测试和文档

### 添加新的优化策略

参考 `optimizers/` 目录中的示例。

## 📚 相关文档

- [Workflow Optimization Framework](../README.md)
- [SAGE Studio Integration](../../../../sage-studio/README.md)
- [Pipeline Builder (CLI)](../../../../sage-cli/README.md)

## 🤝 贡献

欢迎贡献新的生成和优化算法！请参考 [CONTRIBUTING.md](../../../../../../CONTRIBUTING.md)

## 📄 License

与 SAGE 主项目保持一致。
