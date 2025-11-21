# DyFlow 项目架构分析文档

## 目录

1. [项目概述](#%E9%A1%B9%E7%9B%AE%E6%A6%82%E8%BF%B0)
1. [核心架构设计](#%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1)
1. [关键模块详解](#%E5%85%B3%E9%94%AE%E6%A8%A1%E5%9D%97%E8%AF%A6%E8%A7%A3)
1. [数据流与执行流程](#%E6%95%B0%E6%8D%AE%E6%B5%81%E4%B8%8E%E6%89%A7%E8%A1%8C%E6%B5%81%E7%A8%8B)
1. [使用示例](#%E4%BD%BF%E7%94%A8%E7%A4%BA%E4%BE%8B)

______________________________________________________________________

## 项目概述

### 项目简介

DyFlow 是一个动态工作流框架，用于 AI Agent 的推理任务。它采用**双层 Designer-Executor 架构**，能够根据中间反馈动态调整推理过程和子目标。

### 核心特性

- **执行自适应工作流**：根据中间反馈动态调整推理流程
- **两级架构**：
  - **Designer（设计器）**：执行高层任务分解和规划
  - **Executor（执行器）**：执行底层任务和工具调用
- **跨域评估**：支持数学推理、代码生成、医疗推理、因果推理等多个领域

### 技术栈

- **语言**：Python 3.8+
- **LLM 集成**：OpenAI、Anthropic、DeepInfra、vLLM（本地部署）
- **核心依赖**：tiktoken（token计数）、pandas、numpy

______________________________________________________________________

## 核心架构设计

### 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户输入问题                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  WorkflowExecutor                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  1. 初始化 State（问题状态管理）                        │  │
│  │  2. Designer LLM 动态设计下一阶段                       │  │
│  │  3. Executor LLM 执行阶段中的操作                       │  │
│  │  4. 根据执行结果决定继续/终止                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    ┌───────┐   ┌─────────┐   ┌──────────┐
    │ State │   │Designer │   │ Executor │
    │(状态) │   │  LLM    │   │   LLM    │
    └───────┘   └─────────┘   └──────────┘
```

### 2. 核心组件关系

```
dyflow/
├── core/                        # 核心工作流组件
│   ├── state.py                 # State: 状态管理
│   ├── workflow.py              # WorkflowExecutor: 工作流执行器
│   └── operator.py              # Operators: 操作符（执行具体任务）
├── llms/                        # LLM 客户端封装
│   └── clients.py               # Designer & Executor LLM 客户端
└── model_service/               # 模型服务层
    ├── model_service.py         # ModelService: 统一模型接口
    ├── clients.py               # 底层 API 客户端
    ├── config.py                # 模型配置
    ├── pricing.py               # 计费管理
    └── token_counter.py         # Token 统计
```

______________________________________________________________________

## 关键模块详解

### 模块 1: State（状态管理）

**文件位置**: `dyflow/core/state.py`

#### 核心职责

State 是整个工作流的**中央知识库**，存储和管理所有执行过程中的数据。

#### 关键数据结构

```python
class State:
    # 核心数据
    original_problem: str              # 原始问题描述
    final_answer: Optional[Any]        # 最终答案
    final_status: Status               # 最终状态

    # 主要数据容器
    stages: Dict[str, Dict]            # 阶段信息 {stage_id: {description, status}}
    actions: Dict[str, Dict]           # 所有动作 {action_id: {content, type, status, ...}}

    # 日志与历史
    workflow_log: List[Dict]           # 操作执行日志
    stage_history: List[Dict]          # 阶段历史
    error_log: List[Dict]              # 错误日志

    # 增量摘要
    summarized_stages: List[str]       # 已摘要的阶段
    _summarized_stage_ids: List[str]   # 已处理的阶段ID
```

#### 核心方法

##### 1. `get_data_by_path(path: str) -> Any`

**功能**：通过点分隔路径字符串获取状态数据

**参数**：

- `path`: 点分隔的路径字符串（如 `"actions.act_0.content"`）
- `default`: 路径无效时返回的默认值

**返回**：路径对应的数据或默认值

**示例**：

```python
# 获取原始问题
problem = state.get_data_by_path("original_problem")

# 获取某个动作的内容
content = state.get_data_by_path("actions.act_0.content")

# 获取执行结果
result = state.get_data_by_path("actions.act_1.execution_result.status")
```

##### 2. `set_data_by_path(path: str, value: Any) -> bool`

**功能**：通过路径设置状态数据，自动创建缺失的中间字典

**参数**：

- `path`: 数据路径
- `value`: 要设置的值

**返回**：成功返回 True，失败返回 False

**示例**：

```python
# 设置动作内容
state.set_data_by_path("actions.act_0.content", "Solution text...")

# 设置嵌套数据
state.set_data_by_path("actions.act_1.execution_result.status", "Success")
```

##### 3. `get_state_summary_for_designer() -> str`

**功能**：为 Designer LLM 生成增量状态摘要，只摘要新阶段

**工作原理**：

1. 识别未摘要的新阶段
1. 使用 LLM 为每个新阶段生成简洁摘要
1. 提取关键信息：
   - 阶段目标
   - 执行的动作及其 action_id
   - 审查判定（如果有）
   - 代码执行结果（如果有）
   - 最终答案（如果有）
1. 将新摘要添加到历史摘要中

**返回**：所有阶段的完整摘要字符串

**关键特性**：

- **增量式**：只处理新阶段，避免重复计算
- **LLM 驱动**：使用 gpt-4o-mini 生成简洁摘要
- **结构化输出**：包含 action_id、指令类型、判定等关键信息

______________________________________________________________________

### 模块 2: WorkflowExecutor（工作流执行器）

**文件位置**: `dyflow/core/workflow.py`

#### 核心职责

WorkflowExecutor 是整个工作流的**协调中心**，负责：

1. 使用 Designer LLM 动态设计阶段
1. 执行每个阶段的操作符
1. 根据信号决定继续或终止

#### 初始化方法

```python
def __init__(
    self,
    problem_description: str,           # 要解决的问题
    designer_service: ModelService,     # Designer LLM 服务
    executor_service: ModelService,     # Executor LLM 服务
    save_design_history: bool = False   # 是否保存设计历史
)
```

**参数说明**：

- `problem_description`: 原始问题文本
- `designer_service`: 用于阶段设计的 LLM 服务（推荐 GPT-4o 或本地 DyPlanner）
- `executor_service`: 用于执行具体任务的 LLM 服务（推荐 GPT-4o-mini 或 Phi-4）
- `save_design_history`: 如果为 True，设计历史存储在内存中供后续获取

#### 核心方法

##### 1. `execute() -> Any`

**功能**：执行整个工作流直到完成

**工作流程**：

```
1. 初始化：设置状态、LLM 客户端
2. 循环执行（最多 8 次迭代）：
   a. 调用 _design_next_stage() 设计下一阶段
   b. 调用 _execute_stage() 执行阶段
   c. 检查终止信号
   d. 检测循环模式（如重复审查）
3. 返回最终答案
```

**返回**：最终答案（直接返回内容，不包装在字典中）

**示例**：

```python
executor = WorkflowExecutor(
    problem_description="解决数学问题...",
    designer_service=ModelService.gpt4o(),
    executor_service=ModelService(model='phi-4')
)
final_answer = executor.execute()
print(final_answer)
```

##### 2. `_design_next_stage() -> Dict[str, Any]`

**功能**：使用 Designer LLM 设计下一个阶段

**工作原理**：

1. 从 State 获取当前状态摘要
1. 构建设计提示（包含：原始问题、执行摘要、可用操作符、设计规则）
1. 调用 Designer LLM 生成阶段设计
1. 解析 JSON 响应，提取阶段信息
1. 将阶段添加到 State

**返回**：阶段设计字典，包含：

```python
{
    "stage_id": "stage_N",
    "stage_description": "阶段描述",
    "operators": [
        {
            "operator_id": "op_N_1",
            "operator_description": "操作符描述",
            "params": {
                "instruction_type": "GENERATE_ANSWER",
                "input_keys": ["original_problem"],
                "output_key": "act_0",
                "input_usage": "如何使用输入数据"
            }
        },
        ...
    ]
}
```

**支持的指令类型**：

- `DECOMPOSE_PROBLEM`: 分解问题为子目标
- `GENERATE_PLAN`: 生成解决计划
- `GENERATE_ANSWER`: 生成完整解决方案
- `REFINE_ANSWER`: 基于反馈改进答案
- `SELF_CONSISTENCY_ENSEMBLE`: 生成多个解决方案并投票
- `REVIEW_SOLUTION`: 评审解决方案
- `TEST_CODE`: 提取并执行代码
- `ORGANIZE_SOLUTION`: 格式化最终答案并终止工作流

##### 3. `_execute_stage(stage: Dict) -> Tuple[bool, Optional[str], Optional[Any]]`

**功能**：执行单个阶段的所有操作符

**参数**：

- `stage`: 阶段设计字典

**返回**：`(should_continue, termination_reason, final_answer)`

- `should_continue`: 是否继续执行（False 表示终止）
- `termination_reason`: 终止原因（如果终止）
- `final_answer`: 最终答案（如果有）

**工作流程**：

1. 遍历阶段中的每个操作符
1. 获取或创建操作符实例
1. 执行操作符，获取信号
1. 处理信号：
   - `"terminate"`: 返回 False，终止工作流
   - `"error"`: 记录错误，继续下一个操作符
   - `"end_stage"`: 跳过当前阶段剩余操作符
   - `"next"`: 继续执行

##### 4. `get_design_history() -> List[Dict]`

**功能**：获取设计历史（仅当 `save_design_history=True` 时可用）

**返回**：设计历史列表，每个元素包含：

```python
{
    "input": "发送给 Designer LLM 的完整提示",
    "output": "Designer LLM 的原始响应"
}
```

**用途**：用于训练数据生成、调试、分析

______________________________________________________________________

### 模块 3: InstructExecutorOperator（指令执行操作符）

**文件位置**: `dyflow/core/operator.py`

#### 核心职责

InstructExecutorOperator 是工作流的**执行单元**，负责：

1. 根据指令类型选择提示模板
1. 从 State 获取上下文数据
1. 调用 Executor LLM 生成响应
1. 处理和存储输出
1. 特殊处理（如代码执行、集成投票）

#### 初始化方法

```python
def __init__(
    self,
    operator_id: str,              # 操作符唯一标识
    operator_description: str,     # 操作符描述
    llm_client: Any                # LLM 客户端（必须有 generate 方法）
)
```

#### 核心方法

##### 1. `execute(state: State, params: Dict[str, Any]) -> ExecuteSignal`

**功能**：执行 LLM 指令任务

**必需参数**：

```python
params = {
    "instruction_type": str,      # 指令类型（如 "GENERATE_ANSWER"）
    "input_keys": List[str],      # State 中的数据路径列表
    "output_key": str,            # 存储输出的路径
    "input_usage": str,           # （可选）如何使用输入数据的指导
    "target_stage_id": str        # 目标阶段 ID
}
```

**返回**：执行信号

- `"next"`: 成功执行，继续下一个操作符
- `"terminate"`: 工作流终止
- `"error"`: 执行失败
- `"end_stage"`: 结束当前阶段

**执行流程**：

```
1. 参数验证
2. 特殊指令处理：
   - TERMINATE: 终止工作流
   - TEST_CODE: 直接执行代码（不调用 LLM）
   - SELF_CONSISTENCY_ENSEMBLE: 并行生成多个解决方案
3. 标准指令处理：
   a. 从 State 获取上下文数据
   b. 选择提示模板
   c. 构建最终提示
   d. 调用 Executor LLM
   e. 处理输出
   f. 存储到 State
4. 更新动作记录
5. 日志记录
```

**示例**：

```python
operator = InstructExecutorOperator(
    operator_id="op_1_1",
    operator_description="生成初始解决方案",
    llm_client=executor_llm
)

params = {
    "instruction_type": "GENERATE_ANSWER",
    "input_keys": ["original_problem"],
    "output_key": "act_0",
    "input_usage": "使用问题描述生成解决方案",
    "target_stage_id": "stage_1"
}

signal = operator.execute(state, params)
```

##### 2. `_execute_code(code: str) -> Tuple[str, str, Optional[Dict]]`

**功能**：在沙箱环境中执行 Python 代码

**参数**：

- `code`: 要执行的 Python 代码

**返回**：`(status, result, execution_details)`

- `status`: "Success" 或 "Error"
- `result`: 执行结果或错误消息
- `execution_details`: 执行元数据（变量、函数名、导入等）

**安全限制**：

- 禁止导入：os, sys, subprocess, multiprocessing
- 禁止图形库：matplotlib, seaborn, plotly 等

**执行逻辑**：

1. 检查禁止的导入
1. 在新的全局命名空间中执行代码
1. 如果定义了 `solve()` 函数，调用它获取结果
1. 捕获异常并返回完整的堆栈跟踪

##### 3. `_process_output(llm_output: str, instruction_type: str) -> Dict[str, str]`

**功能**：根据指令类型处理 LLM 输出

**参数**：

- `llm_output`: LLM 的原始输出
- `instruction_type`: 指令类型

**返回**：处理后的输出字典

- 通用：`{'content': str}`
- REVIEW_SOLUTION：`{'content': str}` （完整审查内容，判定由摘要 LLM 提取）

**指令类型处理**：

- `REVIEW_SOLUTION`: 返回完整审查内容
- `GENERATE_PLAN`: 提取计划步骤
- 其他: 返回原始内容

#### 提示模板系统

工作流使用预定义的提示模板（存储在 `PROMPT_TEMPLATES` 字典中）：

```python
PROMPT_TEMPLATES = {
    "GENERATE_ANSWER": "...",      # 生成答案
    "REVIEW_SOLUTION": "...",       # 审查解决方案
    "DECOMPOSE_PROBLEM": "...",     # 分解问题
    "GENERATE_PLAN": "...",         # 生成计划
    "REFINE_ANSWER": "...",         # 改进答案
    "ORGANIZE_SOLUTION": "...",     # 组织最终解决方案
    "SELF_CONSISTENCY_ENSEMBLE": "...",  # 集成投票
    "DEFAULT": "..."                # 默认模板
}
```

每个模板接受两个占位符：

- `{context}`: 从 State 获取的上下文数据
- `{guidance}`: 使用指导（来自 `input_usage` 参数）

______________________________________________________________________

### 模块 4: ModelService（模型服务）

**文件位置**: `dyflow/model_service/model_service.py`

#### 核心职责

ModelService 提供**统一的模型接口**，支持多种 LLM 提供商：

- OpenAI（GPT-4o, GPT-4o-mini 等）
- Anthropic（Claude 3.5 Sonnet 等）
- DeepInfra
- 本地 vLLM 服务器

#### 初始化方法

```python
def __init__(
    self,
    model: str = 'chatgpt-4o-latest',  # 模型名称
    temperature: float = 0.01,          # 默认温度
    lock: threading.Lock = None         # 本地模型的线程锁
)
```

**支持的模型**：

- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-4.1-mini` 等
- Anthropic: `claude-3.5-sonnet`, `claude-3.5-haiku` 等
- 本地: `local`, `phi-4`, `dyplanner` 等

#### 核心方法

##### 1. `generate(prompt: str, temperature: float = None, max_tokens: int = 2048, msg: list = None) -> Dict[str, Any]`

**功能**：生成 LLM 响应

**参数**：

- `prompt`: 输入提示
- `temperature`: 采样温度（None 使用默认值）
- `max_tokens`: 最大生成 token 数
- `msg`: 可选的消息格式（用于聊天模型）

**返回**：

```python
{
    "response": str,              # 模型响应
    "model": str,                 # 使用的模型
    "usage": {                    # Token 使用统计
        "input_tokens": int,
        "output_tokens": int,
        "total_tokens": int
    },
    "price": float                # 本次请求的成本（美元）
}
```

**示例**：

```python
service = ModelService(model='gpt-4o-mini')
result = service.generate(
    prompt="解决这个问题：1+1=?",
    temperature=0.1
)
print(result['response'])
print(f"成本: ${result['price']:.4f}")
```

##### 2. 工厂方法

**`ModelService.gpt4o(temperature: float = 0.01) -> ModelService`**

- 创建 GPT-4o 实例

**`ModelService.claude(temperature: float = 0.01) -> ModelService`**

- 创建 Claude 3.5 Sonnet 实例

**`ModelService.local(temperature: float = 0.01, lock: threading.Lock = None) -> ModelService`**

- 创建本地 vLLM 服务器实例

**示例**：

```python
# 使用工厂方法
designer = ModelService.gpt4o()
executor = ModelService.local()
```

##### 3. `get_usage_stats() -> Dict[str, Any]`

**功能**：获取所有模型的使用统计

**返回**：

```python
{
    "gpt-4o": {
        "input_total": int,        # 总输入 tokens
        "output_total": int,       # 总输出 tokens
        "call_count": int,         # 调用次数
        "cost": float              # 总成本
    },
    ...
}
```

##### 4. `switch_model(model: str) -> None`

**功能**：切换到不同的模型

**参数**：

- `model`: 新模型名称

**示例**：

```python
service = ModelService(model='gpt-4o-mini')
# 后来切换到更强大的模型
service.switch_model('gpt-4o')
```

#### 成本管理

ModelService 自动跟踪和计算每次 API 调用的成本：

- 使用 `TokenTracker` 跟踪 token 使用量
- 使用 `pricing.py` 中的定价信息计算成本
- 支持不同模型的不同定价（输入/输出 token 分开计费）

______________________________________________________________________

### 模块 5: LLM 客户端封装

**文件位置**: `dyflow/llms/clients.py`

#### ExecutorLLMClient

**功能**：Executor LLM 的客户端封装

```python
class ExecutorLLMClient:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.service = ModelService(model=model_name)

    def generate(self, prompt: str, temperature: float = 0.001) -> str:
        """调用 executor LLM"""
        return self.service.generate(prompt=prompt, temperature=temperature)
```

#### DesignerLLMClient

**功能**：Designer LLM 的客户端封装

```python
class DesignerLLMClient:
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.service = ModelService(model=model_name)

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """调用 designer LLM"""
        return self.service.generate(prompt=prompt, temperature=temperature)
```

______________________________________________________________________

## 数据流与执行流程

### 1. 完整执行流程

```
开始
  │
  ├─→ [1] 初始化 WorkflowExecutor
  │        │
  │        ├─ 创建 State(original_problem)
  │        ├─ 初始化 Designer LLM
  │        └─ 初始化 Executor LLM
  │
  ├─→ [2] 执行循环（最多 8 次迭代）
  │        │
  │        ├─→ [2.1] 设计阶段 (_design_next_stage)
  │        │         │
  │        │         ├─ 从 State 获取增量摘要
  │        │         ├─ 构建设计提示（问题+摘要+规则）
  │        │         ├─ 调用 Designer LLM
  │        │         ├─ 解析 JSON 响应
  │        │         └─ 添加阶段到 State
  │        │
  │        ├─→ [2.2] 执行阶段 (_execute_stage)
  │        │         │
  │        │         └─ 对每个操作符：
  │        │               │
  │        │               ├─ 创建 InstructExecutorOperator
  │        │               ├─ 从 State 获取输入数据
  │        │               ├─ 选择提示模板
  │        │               ├─ 调用 Executor LLM
  │        │               ├─ 处理输出
  │        │               ├─ 存储到 State
  │        │               └─ 检查信号（next/terminate/error）
  │        │
  │        ├─→ [2.3] 检查终止条件
  │        │         ├─ 收到 terminate 信号？
  │        │         ├─ 达到最大迭代次数？
  │        │         └─ 检测循环模式？
  │        │
  │        └─ 如果未终止，返回步骤 2.1
  │
  └─→ [3] 返回最终答案
```

### 2. 数据在组件间的流动

```
┌─────────────┐
│   State     │  ← 中央数据存储
└──────┬──────┘
       │
       ├─→ [读取] WorkflowExecutor._design_next_stage()
       │          ├─ 调用 state.get_state_summary_for_designer()
       │          └─ 获取增量摘要
       │
       ├─→ [读取] InstructExecutorOperator.execute()
       │          ├─ 调用 state.get_data_by_path(input_keys)
       │          └─ 获取操作符的输入数据
       │
       ├─→ [写入] InstructExecutorOperator.execute()
       │          ├─ 调用 state.set_data_by_path(output_key, llm_output)
       │          ├─ 更新 state.actions[action_id]
       │          └─ 添加到 stage history
       │
       └─→ [写入] WorkflowExecutor._design_next_stage()
                  └─ 调用 state.add_stage(stage_description)
```

### 3. 典型工作流示例

以数学问题为例：

```
迭代 1: 初始解决
┌──────────────────────────────────────────────────┐
│ Stage 1: 生成初始解决方案                          │
├──────────────────────────────────────────────────┤
│ op_1_1: GENERATE_ANSWER                          │
│   - input: original_problem                      │
│   - output: act_0 (初始解决方案)                  │
└──────────────────────────────────────────────────┘

迭代 2: 审查与改进
┌──────────────────────────────────────────────────┐
│ Stage 2: 审查解决方案                             │
├──────────────────────────────────────────────────┤
│ op_2_1: REVIEW_SOLUTION                          │
│   - input: original_problem, act_0               │
│   - output: act_1 (审查意见)                      │
│                                                  │
│ op_2_2: REFINE_ANSWER                            │
│   - input: act_0, act_1                          │
│   - output: act_2 (改进的解决方案)                │
└──────────────────────────────────────────────────┘

迭代 3: 最终审查与终止
┌──────────────────────────────────────────────────┐
│ Stage 3: 最终审查并组织答案                        │
├──────────────────────────────────────────────────┤
│ op_3_1: REVIEW_SOLUTION                          │
│   - input: original_problem, act_2               │
│   - output: act_3 (最终审查: accept)              │
└──────────────────────────────────────────────────┘

迭代 4: 组织最终答案（自动终止）
┌──────────────────────────────────────────────────┐
│ Stage 4: 组织最终解决方案                          │
├──────────────────────────────────────────────────┤
│ op_4_1: ORGANIZE_SOLUTION                        │
│   - input: act_2                                 │
│   - output: act_4 (格式化的最终答案)              │
│   - signal: TERMINATE                            │
└──────────────────────────────────────────────────┘

工作流终止，返回 act_4 的内容
```

### 4. 特殊指令处理

#### TEST_CODE 指令流程

```
1. 从 State 获取包含代码的解决方案
2. 使用正则表达式提取 Python 代码块
3. 调用 _execute_code() 在沙箱中执行
4. 捕获执行结果（成功/失败）
5. 格式化输出（代码 + 执行结果）
6. 存储到 State，包括 execution_result 字段
```

#### SELF_CONSISTENCY_ENSEMBLE 指令流程

```
1. 并行生成 N 个独立解决方案（默认 5 个）
2. 使用 ThreadPoolExecutor 并发执行
3. 收集所有解决方案
4. 使用选择器 LLM 进行多数投票：
   - 识别达成多数共识的解决方案
   - 从多数组中选择推理最清晰的
5. 存储选中的解决方案和集成元数据：
   - all_solutions: 所有解决方案列表
   - selected_index: 选中的索引
   - selection_method: 选择方法
   - confidence: 置信度
```

______________________________________________________________________

## 使用示例

### 示例 1: 基本使用（单个问题）

```python
from dyflow import WorkflowExecutor, ModelService

# 定义问题
problem = """
解决以下数学问题：
一个农场有 12 只鸡和 8 只兔子。
每只鸡有 2 条腿，每只兔子有 4 条腿。
所有动物总共有多少条腿？
请提供逐步解决方案。
"""

# 创建模型服务
designer = ModelService.gpt4o()          # Designer 使用 GPT-4o
executor = ModelService(model='phi-4')   # Executor 使用 Phi-4

# 创建工作流执行器
workflow = WorkflowExecutor(
    problem_description=problem,
    designer_service=designer,
    executor_service=executor
)

# 执行工作流
final_answer = workflow.execute()

# 输出结果
print("=" * 60)
print("最终答案:")
print(final_answer)
print("=" * 60)

# 获取使用统计
stats = executor.get_usage_stats()
print("\nToken 使用统计:")
print(stats)
```

### 示例 2: 代码生成任务

````python
from dyflow import WorkflowExecutor, ModelService

# 代码问题
problem = """
编写一个 Python 函数 `is_palindrome(s: str) -> bool`，
判断字符串是否为回文（忽略大小写和非字母数字字符）。

示例：
- is_palindrome("A man a plan a canal Panama") → True
- is_palindrome("race a car") → False
"""

# 使用本地 DyPlanner 作为 Designer
designer = ModelService.local()
executor = ModelService(model='gpt-4o-mini')

workflow = WorkflowExecutor(
    problem_description=problem,
    designer_service=designer,
    executor_service=executor
)

final_answer = workflow.execute()

# 提取代码
import re
code_match = re.search(r'```python\n(.*?)\n```', final_answer, re.DOTALL)
if code_match:
    code = code_match.group(1)
    print("生成的代码:")
    print(code)
````

### 示例 3: 批量评估（Benchmark）

```python
from benchmarks import MathBenchmark
from dyflow import ModelService

# 配置模型
designer = ModelService(model='gpt-4o')
executor = ModelService(model='phi-4')
judge = ModelService(model='gpt-4o-mini')

# 创建 Benchmark
benchmark = MathBenchmark(
    execution_model='phi-4',
    baseline='DyFlow',
    mode='test'
)

# 定义解决函数
def solve_with_dyflow(question: str):
    from dyflow import WorkflowExecutor

    workflow = WorkflowExecutor(
        problem_description=question + "\n\n请逐步解决问题，并将答案放在 \\boxed{} 中。",
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )

    answer = workflow.execute()
    design_history = workflow.get_design_history()
    return answer, design_history

# 运行评估
benchmark.run(
    generate_service=designer,
    judge_service=judge,
    function=solve_with_dyflow,
    size=10,            # 评估 10 个问题
    max_workers=5       # 5 个并行 worker
)

# 计算指标
metrics = benchmark.calculate_metrics()
print("评估结果:")
print(metrics)
```

### 示例 4: 保存设计历史用于训练

```python
import json
from dyflow import WorkflowExecutor, ModelService

problems = [
    "问题 1...",
    "问题 2...",
    "问题 3..."
]

designer = ModelService.local()  # 使用本地 DyPlanner
executor = ModelService(model='phi-4')

training_data = []

for problem in problems:
    workflow = WorkflowExecutor(
        problem_description=problem,
        designer_service=designer,
        executor_service=executor,
        save_design_history=True  # 启用历史保存
    )

    answer = workflow.execute()
    history = workflow.get_design_history()

    # 保存训练数据
    training_data.append({
        "problem": problem,
        "answer": answer,
        "design_history": history
    })

# 保存到文件
with open("training_data.jsonl", "w") as f:
    for item in training_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
```

### 示例 5: 自定义模型配置

```python
from dyflow import ModelService

# 方法 1: 使用工厂方法
service1 = ModelService.gpt4o(temperature=0.7)
service2 = ModelService.claude(temperature=0.1)
service3 = ModelService.local()

# 方法 2: 直接初始化
service4 = ModelService(
    model='gpt-4o-mini',
    temperature=0.01
)

# 方法 3: 动态切换模型
service = ModelService(model='gpt-4o-mini')
response1 = service.generate("简单问题")

# 切换到更强大的模型处理复杂问题
service.switch_model('gpt-4o')
response2 = service.generate("复杂问题")

# 获取统计信息
stats = service.get_usage_stats()
print(f"GPT-4o-mini 成本: ${stats['gpt-4o-mini']['cost']:.4f}")
print(f"GPT-4o 成本: ${stats['gpt-4o']['cost']:.4f}")
```

______________________________________________________________________

## 关键设计思想

### 1. 动态适应性

- **设计时适应**：Designer 根据执行历史动态规划下一阶段
- **执行时适应**：Executor 根据中间结果调整策略
- **反馈循环**：审查 → 改进 → 再审查

### 2. 分离关注点

- **Designer**：负责"做什么"（What）- 高层规划
- **Executor**：负责"怎么做"（How）- 具体执行
- **State**：负责"记住什么"（Memory）- 状态管理

### 3. 增量摘要

- 只摘要新阶段，避免重复计算
- 使用 LLM 生成简洁、结构化的摘要
- 保持 Designer 提示长度可控

### 4. 可扩展性

- **模块化操作符**：易于添加新指令类型
- **统一模型接口**：支持多种 LLM 提供商
- **灵活的 State 系统**：支持任意数据结构

### 5. 成本意识

- 自动跟踪 token 使用和成本
- 支持混合模型策略（Designer 用强模型，Executor 用弱模型）
- 增量摘要减少重复处理

### 6. 安全性

- 代码执行沙箱（禁止危险导入）
- 最大迭代次数限制（防止无限循环）
- 循环检测（识别重复审查模式）

______________________________________________________________________

## 总结

DyFlow 通过**双层架构**和**动态适应**机制，实现了灵活、鲁棒的 AI Agent 推理框架：

1. **State** 作为中央知识库，存储和管理所有执行数据
1. **WorkflowExecutor** 协调整个工作流，使用 Designer 动态规划阶段
1. **InstructExecutorOperator** 执行具体任务，支持多种指令类型
1. **ModelService** 提供统一的 LLM 接口，支持多种模型
1. **增量摘要**机制确保 Designer 能高效处理长执行历史

这种设计使得 DyFlow 能够：

- ✅ 适应不同领域的任务（数学、代码、医疗、因果推理等）
- ✅ 根据中间反馈动态调整策略
- ✅ 支持复杂的推理模式（分解、集成投票、审查改进等）
- ✅ 可扩展到新的操作符和模型
- ✅ 生成训练数据用于模型改进

______________________________________________________________________

## Benchmark 评估模块

### 概述

DyFlow 提供了完整的 Benchmark 评估框架，支持多个领域的任务评估：

| Benchmark      | 领域     | 任务类型        | 评估指标         |
| -------------- | -------- | --------------- | ---------------- |
| **MATH**       | 数学推理 | 解决数学问题    | Accuracy, Pass@k |
| **HumanEval**  | 代码生成 | Python 函数实现 | Pass@k           |
| **LiveBench**  | 因果推理 | 多轮对话推理    | Accuracy, Pass@k |
| **PubMedQA**   | 医疗推理 | 生物医学问答    | Accuracy, Pass@k |
| **SocialMaze** | 社交推理 | 社交场景推理    | Accuracy, Pass@k |

### 架构设计

```
benchmarks/
├── __init__.py              # 导出所有 Benchmark 类
├── framework.py             # BaseBenchmark 基类
├── math.py                  # MATHBenchmark
├── humaneval.py             # HumanEvalBenchmark
├── livebench.py             # LiveBenchBenchmark
├── pubmedqa.py              # PubMedQABenchmark
└── socialmaze.py            # SocialMazeBenchmark
```

### BaseBenchmark（基类）

**文件位置**: `benchmarks/framework.py`

#### 核心职责

提供所有 Benchmark 的通用接口和工具方法。

#### 抽象方法

```python
class BaseBenchmark(ABC):
    def __init__(self, execution_model: str, baseline: str, mode: str):
        """
        Args:
            execution_model: 执行模型名称（如 'phi-4'）
            baseline: 基线方法名称（如 'DyFlow', 'CoT'）
            mode: 评估模式（'test' 或 'train'）
        """

    @abstractmethod
    def evaluate_problem(self, problem: dict, function: Callable, judge_service=None) -> dict:
        """评估单个问题"""
        pass

    @abstractmethod
    def evaluate_all_problems(self, function: Callable, size: int = None,
                             judge_service=None, max_workers: int = 10):
        """评估所有问题"""
        pass

    @abstractmethod
    def calculate_metrics(self) -> Tuple[Any, ...]:
        """计算评估指标"""
        pass
```

#### 通用工具方法

##### 1. `extract_judge_result(output: str) -> bool`

**功能**：从 Judge LLM 的输出中提取布尔结果

**输入格式**：包含 `[[True]]` 或 `[[False]]` 的文本

**返回**：True 表示正确，False 表示错误

**示例**：

```python
output = "分析后，我认为答案是正确的。[[True]]"
result = benchmark.extract_judge_result(output)  # True
```

##### 2. `write_results(results: List[dict], output_path: str)`

**功能**：保存评估结果到 JSON 文件

##### 3. `load_json(dataset_path: str) -> List[dict]`

**功能**：加载数据集

______________________________________________________________________

### MATHBenchmark（数学推理）

**文件位置**: `benchmarks/math.py`

#### 数据集

- **来源**：MATH 数据集（高难度数学问题）
- **问题数量**：~12,500 题（test set）
- **难度等级**：5 级（Level 1-5）
- **主题**：代数、几何、数论、概率等

#### 初始化参数

```python
MATHBenchmark(
    execution_model: str,           # 执行模型名称
    baseline: str = "DyFlow",       # 基线方法
    mode: str = "test",             # 'test' 或 'train'
    samples_per_task: int = 1       # 每题生成的解决方案数量
)
```

#### 核心方法

##### 1. `judge_prompt(problem: str, solution: str, ground_truth: str) -> str`

**功能**：生成 Judge 提示，让 Judge LLM 评估答案是否等价于正确答案

**判定规则**：

- 只考虑最终答案，忽略中间步骤
- 接受不同但逻辑等价的表达
- 数学表达式需要在数值上相等

##### 2. `evaluate_problem(problem: dict, function: Callable, judge_service) -> dict`

**功能**：评估单个数学问题

**工作流程**：

```
1. 并行生成 N 个解决方案（N = samples_per_task）
2. 并行调用 Judge LLM 评估每个解决方案
3. 计算正确解决方案数量 (c)
4. 计算 pass@k 指标（k=1,3,5）
5. 返回评估结果
```

**返回结果**：

```python
{
    "problem": "原始问题",
    "solution": "正确答案",
    "generated_solutions": ["方案1", "方案2", ...],
    "design_histories": [历史1, 历史2, ...],
    "judge_results": [True, False, True, ...],
    "correct": 2,                    # 正确数量
    "total": 3,                      # 总数量
    "pass@1": 0.67,                  # Pass@1 分数
    "pass@3": 0.97,                  # Pass@3 分数
    "pass@5": 0.99                   # Pass@5 分数
}
```

##### 3. `compute_pass_at_k(n: int, c: int, k: int) -> float`

**功能**：计算 pass@k 指标

**公式**： $$ \\text{pass@k} = 1 - \\prod\_{i=0}^{k-1} \\frac{n-c-i}{n-i} $$

其中：

- `n`: 生成的样本总数
- `c`: 正确的样本数
- `k`: 考虑的样本数

**含义**：在 n 个样本中随机选择 k 个，至少有一个正确的概率

##### 4. `run(generate_service, judge_service, function, size, max_workers, pass_k)`

**功能**：运行完整的评估流程

**参数**：

- `generate_service`: 用于生成解决方案的模型服务
- `judge_service`: 用于评判答案的模型服务
- `function`: 解决函数（如 DyFlow workflow）
- `size`: 评估问题数量（None = 全部）
- `max_workers`: 并行 worker 数量
- `pass_k`: 最大 k 值（如 pass_k=5 则计算 pass@1 到 pass@5）

**特性**：

- **增量保存**：每完成一题保存一次，支持断点续传
- **成本跟踪**：自动记录 token 使用和成本
- **并行评估**：多线程并行处理

______________________________________________________________________

### HumanEvalBenchmark（代码生成）

**文件位置**: `benchmarks/humaneval.py`

#### 数据集

- **来源**：HumanEval（OpenAI 代码生成基准）
- **问题数量**：164 题
- **任务**：实现 Python 函数
- **评估方式**：通过单元测试

#### 核心特性

##### 1. 代码提取：`filter_code(completion: str) -> str`

**功能**：从模型输出中提取 Python 代码

**支持格式**：

````python
# 格式 1: 带语言标识的代码块
```python
def solution():
    return 42
````

# 格式 2: 纯代码块

```
def solution():
    return 42
```

# 格式 3: 原始代码（以 def/import/class 开头）

def solution(): return 42

```

##### 2. 代码执行：`check_correctness(problem: Dict, completion: str, timeout: float) -> Dict`
**功能**：在隔离环境中执行代码并验证正确性

**安全机制**：
- **进程隔离**：使用独立进程执行代码
- **时间限制**：默认 10 秒超时
- **临时目录**：在独立临时目录中执行
- **资源限制**：限制内存和 CPU 使用

**执行流程**：
```

1. 创建临时工作目录
1. 导入常用库（math, numpy, re 等）
1. 执行生成的代码
1. 执行测试用例（problem["test"]）
1. 调用 check(entry_point) 验证
1. 清理临时目录
1. 返回结果（passed/failed/timed out）

````

**返回结果**：
```python
{
    "task_id": "HumanEval/0",
    "completion": "生成的代码",
    "result": "passed"  # 或 "failed: TypeError: ..." 或 "timed out"
}
````

##### 3. Pass@k 计算

**支持的 k 值**：1, 3, 5, 10（根据 samples_per_task 自动调整）

**示例**：

```python
benchmark = HumanEvalBenchmark(
    execution_model='phi-4',
    baseline='DyFlow',
    mode='test',
    samples_per_task=10  # 每题生成 10 个解决方案
)

# 自动计算 pass@1, pass@3, pass@5, pass@10
metrics = benchmark.calculate_metrics()
```

______________________________________________________________________

### LiveBenchBenchmark（因果推理）

**文件位置**: `benchmarks/livebench.py`

#### 数据集

- **来源**：LiveBench（动态更新的因果推理基准）
- **任务类型**：多轮对话、因果关系判断
- **特点**：避免数据泄露（定期更新题目）

#### Judge 提示

```python
def judge_prompt(self, question: str, solution: str, ground_truth: str) -> str:
    """
    评判规则：
    1. 忽略空格和格式差异
    2. 接受不同但逻辑等价的表达
    3. 明确答案需要精确匹配
    """
```

#### 分类评估

LiveBench 支持按类别评估性能：

```python
category_metrics = {
    "causal_reasoning": {"total": 50, "correct": 35},
    "temporal_reasoning": {"total": 40, "correct": 28},
    ...
}
```

______________________________________________________________________

### PubMedQABenchmark（医疗推理）

**文件位置**: `benchmarks/pubmedqa.py`

#### 数据集

- **来源**：PubMedQA（生物医学问答）
- **问题类型**：基于医学文献的是非判断
- **答案格式**：yes / no / maybe

#### 特殊设计

##### 1. 无需 Judge LLM

PubMedQA 使用正则表达式直接提取答案，不需要 Judge 模型：

```python
def judge_solution(self, solution, ground_truth):
    """
    直接从解决方案中提取 yes/no/maybe

    支持格式：
    - [[yes]], [[no]], [[maybe]]
    - 文本中的 yes/no/maybe 关键词
    """
    # 正则表达式匹配
    yes_pattern = r'\[\[yes\]\]|(?<!\w)yes(?!\w)'
    no_pattern = r'\[\[no\]\]|(?<!\w)no(?!\w)'
    maybe_pattern = r'\[\[maybe\]\]|(?<!\w)maybe(?!\w)'

    # 提取答案并与 ground_truth 比较
    return extracted_answer == ground_truth
```

##### 2. 提示格式

```python
prompt = f"""Question: {question}

Context: {contexts}

Answer the question based on the context.
Output your final decision in the format of [[yes]] or [[no]] or [[maybe]].
"""
```

______________________________________________________________________

### SocialMazeBenchmark（社交推理）

**文件位置**: `benchmarks/socialmaze.py`

#### 数据集

- **来源**：SocialMaze（社交场景推理）
- **任务**：推理犯罪者身份和自己的角色
- **角色类型**：Investigator（调查员）、Rumormonger（造谣者）、Lunatic（疯子）、Criminal（罪犯）

#### 评判标准

```python
def judge_prompt(self, problem: str, solution: str, ground_truth: str) -> str:
    """
    判定规则：
    1. 必须同时正确推断出 Final Criminal 和 My role
    2. Final Criminal 编号必须与正确答案一致
    3. My role 必须完全匹配（不同角色视为错误）
    4. 任何 unknown 答案都判定为错误

    输出格式要求：
    'Final Criminal: <number>, My role: <role>'
    """
```

**示例**：

```python
# 正确答案
ground_truth = "Final Criminal: 3, My role: Investigator"

# 解决方案
solution = """
经过推理...
Final Criminal: 3, My role: Investigator
"""

# 判定：[[True]]
```

______________________________________________________________________

### 通用特性

#### 1. 增量保存与断点续传

所有 Benchmark 都支持增量保存：

```python
# 临时文件路径
temp_file = f"temp_{mode}_{benchmark}_results.json"
temp_cost_file = f"temp_{mode}_{benchmark}_cost.json"

# 自动保存机制
def save_intermediate_results():
    """每完成一题保存一次"""
    with open(temp_file, 'w') as f:
        json.dump(results, f, indent=4)

# 恢复机制
if os.path.exists(temp_file):
    results = json.load(temp_file)
    # 过滤已完成的问题
    problems = filter_completed(problems, results)
```

**优势**：

- 防止长时间运行中断导致数据丢失
- 支持随时中断和恢复评估
- 适合大规模评估任务

#### 2. 成本跟踪

自动记录三类成本：

```python
{
    "generate_cost": {          # Designer/生成模型成本
        "gpt-4o": {
            "input_total": 150000,
            "output_total": 50000,
            "cost": 3.50
        }
    },
    "judge_cost": {             # Judge 模型成本
        "gpt-4o-mini": {
            "input_total": 80000,
            "output_total": 20000,
            "cost": 0.30
        }
    },
    "executor_cost": {          # Executor 模型成本
        "phi-4": {
            "input_total": 200000,
            "output_total": 100000,
            "cost": 0.00  # 本地模型
        }
    }
}
```

#### 3. Pass@k 支持

所有 Benchmark 都支持 pass@k 评估：

**使用方法**：

```python
# 方法 1: 在初始化时设置
benchmark = MATHBenchmark(
    execution_model='phi-4',
    baseline='DyFlow',
    mode='test',
    samples_per_task=5  # 每题生成 5 个解决方案
)

# 方法 2: 在 run 时设置
benchmark.run(
    generate_service=designer,
    judge_service=judge,
    function=solve_fn,
    pass_k=5  # 计算 pass@1 到 pass@5
)
```

**自动调整**：

- 如果 `pass_k > samples_per_task`，自动增加 `samples_per_task`
- k_list 自动生成：`[1, 3, 5, ...]`（不超过 samples_per_task）

#### 4. 并行评估

使用 `ThreadPoolExecutor` 实现多级并行：

```python
# 级别 1: 问题级并行
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [
        executor.submit(evaluate_problem, problem, function)
        for problem in problems
    ]

# 级别 2: 样本级并行（每个问题内部）
with ThreadPoolExecutor(max_workers=samples_per_task) as executor:
    futures = [
        executor.submit(function, question)
        for _ in range(samples_per_task)
    ]

# 级别 3: 判定级并行（判定每个样本）
with ThreadPoolExecutor(max_workers=len(solutions)) as executor:
    futures = [
        executor.submit(judge_service.generate, judge_prompt)
        for solution in solutions
    ]
```

**性能优化**：

- 最大化 GPU/CPU 利用率
- 减少总评估时间
- 支持大规模批量评估

______________________________________________________________________

### 使用示例

#### 示例 1: 评估数学推理（MATH）

```python
from benchmarks import MathBenchmark
from dyflow import WorkflowExecutor, ModelService

# 配置模型
designer = ModelService.gpt4o()
executor = ModelService(model='phi-4')
judge = ModelService(model='gpt-4o-mini')

# 创建 Benchmark
benchmark = MathBenchmark(
    execution_model='phi-4',
    baseline='DyFlow',
    mode='test',
    samples_per_task=5  # 每题 5 个样本用于 pass@k
)

# 定义解决函数
def solve_math(question: str):
    workflow = WorkflowExecutor(
        problem_description=question + "\n\n请逐步解决，答案用 \\boxed{} 包裹。",
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )
    answer = workflow.execute()
    history = workflow.get_design_history()
    return answer, history

# 运行评估
benchmark.run(
    generate_service=designer,
    judge_service=judge,
    function=solve_math,
    size=100,           # 评估 100 题
    max_workers=10,     # 10 个并行 worker
    pass_k=5            # 计算 pass@1 到 pass@5
)

# 查看结果
metrics = benchmark.calculate_metrics()
print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"Pass@1: {metrics[1]:.4f}")
print(f"Pass@3: {metrics[3]:.4f}")
print(f"Pass@5: {metrics[5]:.4f}")
```

#### 示例 2: 评估代码生成（HumanEval）

```python
from benchmarks import HumanEvalBenchmark
from dyflow import WorkflowExecutor, ModelService

designer = ModelService.local()  # 本地 DyPlanner
executor = ModelService(model='phi-4')
judge = ModelService(model='gpt-4o-mini')

benchmark = HumanEvalBenchmark(
    execution_model='phi-4',
    baseline='DyFlow',
    mode='test',
    samples_per_task=10  # 代码任务推荐更多样本
)

def solve_code(prompt: str):
    workflow = WorkflowExecutor(
        problem_description=prompt + "\n\n返回完整函数实现，不要包含测试代码。",
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )
    code = workflow.execute()
    history = workflow.get_design_history()
    return code, history

benchmark.run(
    solve_fn=solve_code,
    generate_service=designer,
    executor_service=executor,
    judge_service=judge,
    size=164,           # 全部 164 题
    max_workers=4,      # HumanEval 推荐 4 个 worker
    pass_k=10           # 计算 pass@1 到 pass@10
)

metrics = benchmark.calculate_metrics()
print(f"Pass@1: {metrics[1]:.4f}")
print(f"Pass@5: {metrics[5]:.4f}")
print(f"Pass@10: {metrics[10]:.4f}")
```

#### 示例 3: 批量评估所有 Benchmark

```python
from benchmarks import *
from dyflow import ModelService

# 配置模型
designer = ModelService(model='gpt-4o')
executor = ModelService(model='phi-4')
judge = ModelService(model='gpt-4o-mini')

# 定义所有评估任务
evaluations = {
    'math': MathBenchmark(execution_model='phi-4', baseline='DyFlow', mode='test'),
    'code': HumanEvalBenchmark(execution_model='phi-4', baseline='DyFlow', mode='test'),
    'causal': LiveBenchBenchmark(execution_model='phi-4', baseline='DyFlow', mode='test'),
    'medical': PubMedQABenchmark(execution_model='phi-4', baseline='DyFlow', mode='test'),
    'social': SocialMazeBenchmark(execution_model='phi-4', baseline='DyFlow', mode='test')
}

# 批量运行
results = {}
for name, benchmark in evaluations.items():
    print(f"\n{'='*60}")
    print(f"Running {name} evaluation...")
    print(f"{'='*60}")

    benchmark.run(
        generate_service=designer,
        judge_service=judge,
        function=get_solve_function(name),  # 根据任务类型选择函数
        size=50,  # 每个任务 50 题
        max_workers=10
    )

    metrics = benchmark.calculate_metrics()
    results[name] = metrics

# 汇总报告
print("\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
for name, metrics in results.items():
    print(f"\n{name.upper()}")
    print(f"  Accuracy: {metrics.get('accuracy', 'N/A')}")
    if 1 in metrics:
        print(f"  Pass@1: {metrics[1]:.4f}")
```

#### 示例 4: 断点续传

```python
# 第一次运行（假设在第 30 题时中断）
benchmark = MathBenchmark(execution_model='phi-4', baseline='DyFlow', mode='test')

try:
    benchmark.run(
        generate_service=designer,
        judge_service=judge,
        function=solve_fn,
        size=100,
        max_workers=10
    )
except KeyboardInterrupt:
    print("评估被中断，进度已保存")

# 第二次运行（自动从第 31 题继续）
benchmark = MathBenchmark(execution_model='phi-4', baseline='DyFlow', mode='test')

# 自动加载已完成的 30 题，继续评估剩余 70 题
benchmark.run(
    generate_service=designer,
    judge_service=judge,
    function=solve_fn,
    size=100,
    max_workers=10
)
```

______________________________________________________________________

### 最佳实践

#### 1. 选择合适的 max_workers

- **CPU 密集型**（如 HumanEval）：4-8 workers
- **IO 密集型**（如 MATH, LiveBench）：10-50 workers
- **GPU 限制**：根据 GPU 数量调整

#### 2. 合理设置 samples_per_task

- **探索性评估**：1-3 个样本
- **标准 pass@k**：5-10 个样本
- **高精度 pass@k**：20+ 个样本

#### 3. 成本优化策略

- **Designer**: 使用本地 DyPlanner（免费）
- **Executor**: 使用较弱的模型（phi-4, gpt-4o-mini）
- **Judge**: 使用 gpt-4o-mini（便宜且准确）

#### 4. 调试技巧

```python
# 先用小规模测试
benchmark.run(..., size=5)  # 只测试 5 题

# 检查单个问题
problem = benchmark.load_json(dataset_path)[0]
result = benchmark.evaluate_problem(problem, solve_fn, judge)
print(result)

# 查看中间结果
import json
with open('temp_results.json') as f:
    temp_results = json.load(f)
```

______________________________________________________________________

## 本地运行 Benchmark 完整指南

### 前置准备

#### 1. 环境配置

**必需软件**：

```bash
# Python 3.8+
python --version  # 检查版本

# Git（用于克隆项目）
git --version
```

**硬件要求**：

- **CPU**: 4 核心以上（用于并行评估）
- **内存**: 8GB 以上
- **GPU**: 可选（如果使用本地 vLLM 模型）
- **磁盘**: 10GB 以上（用于数据集和结果）

#### 2. 克隆项目

```bash
# 克隆项目
git clone https://github.com/wyf23187/DyFlow.git
cd DyFlow

# 查看项目结构
ls -la
```

#### 3. 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或使用 conda 环境
conda create -n dyflow python=3.10
conda activate dyflow
pip install -r requirements.txt
```

**依赖列表**：

```
openai              # OpenAI API 客户端
anthropic           # Anthropic API 客户端
python-dotenv       # 环境变量管理
tiktoken            # Token 计数
vllm                # 本地模型部署（可选）
numpy               # 数值计算
pandas              # 数据处理
requests            # HTTP 请求
tqdm                # 进度条
```

#### 4. 配置 API 密钥

在项目根目录创建 `.env` 文件：

```bash
# 创建 .env 文件
touch .env

# 编辑 .env 文件
nano .env  # 或使用其他编辑器
```

**添加 API 密钥**：

```bash
# OpenAI API（必需）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Anthropic API（可选）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# DeepInfra API（可选）
DEEPINFRA_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 代理设置（可选，国内用户可能需要）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

**获取 API 密钥方法**：

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **DeepInfra**: https://deepinfra.com/

#### 5. 下载数据集

数据集应该已经包含在项目中的 `benchmarks/data/` 目录：

```bash
# 检查数据集
ls -la benchmarks/data/

# 应该看到：
# MATH/
# humaneval/
# livebench/
# PubMedQA/
# socialmaze/
```

**如果数据集缺失**，请确保克隆了完整的仓库（包括 Git LFS 文件）。

______________________________________________________________________

### 快速开始：运行第一个 Benchmark

#### 方式 1: 使用云端模型（推荐新手）

这是最简单的方式，不需要本地部署模型。

**步骤 1：创建测试脚本**

创建文件 `test_benchmark.py`：

```python
#!/usr/bin/env python3
"""
快速测试 DyFlow Benchmark
使用云端 API，无需本地模型
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from benchmarks import MathBenchmark
from dyflow import WorkflowExecutor, ModelService

def solve_math_problem(question: str):
    """使用 DyFlow 解决数学问题"""
    # 使用 GPT-4o 作为 Designer
    designer = ModelService(model='gpt-4o', temperature=0.1)

    # 使用 GPT-4o-mini 作为 Executor（更便宜）
    executor = ModelService(model='gpt-4o-mini', temperature=0.01)

    # 创建工作流
    workflow = WorkflowExecutor(
        problem_description=question + "\n\n请逐步解决问题，将最终答案放在 \\boxed{} 中。",
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )

    # 执行工作流
    answer = workflow.execute()
    design_history = workflow.get_design_history()

    return answer, design_history

def main():
    # 创建 Benchmark
    benchmark = MathBenchmark(
        execution_model='gpt-4o-mini',
        baseline='DyFlow',
        mode='test',
        samples_per_task=1  # 先测试 1 个样本
    )

    # 配置 Judge 模型
    judge_service = ModelService(model='gpt-4o-mini')
    designer_service = ModelService(model='gpt-4o')

    # 运行评估（只测试 5 题）
    print("=" * 60)
    print("开始运行 MATH Benchmark（测试模式：5 题）")
    print("=" * 60)

    benchmark.run(
        generate_service=designer_service,
        judge_service=judge_service,
        function=solve_math_problem,
        size=5,              # 只测试 5 题
        max_workers=2,       # 2 个并行 worker
        pass_k=1             # 只计算 pass@1
    )

    # 查看结果
    metrics = benchmark.calculate_metrics()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"准确率: {metrics['accuracy']:.2%}")
    print(f"Pass@1: {metrics.get(1, 0):.2%}")

    # 查看成本
    designer_stats = designer_service.get_usage_stats()
    judge_stats = judge_service.get_usage_stats()

    total_cost = sum(
        stats.get('cost', 0)
        for model_stats in [designer_stats, judge_stats]
        for stats in model_stats.values()
    )

    print(f"\n总成本: ${total_cost:.4f}")

if __name__ == "__main__":
    main()
```

**步骤 2：运行测试**

```bash
# 确保在项目根目录
cd /path/to/DyFlow

# 运行测试脚本
python test_benchmark.py
```

**预期输出**：

```
============================================================
开始运行 MATH Benchmark（测试模式：5 题）
============================================================

========== Stage stage_0 ==========
Stage Description: 生成初始解决方案
Operators: [...]
========================================================

Evaluating test MATH problems: 100%|████████| 5/5 [02:30<00:00, 30.2s/problem]

Evaluation complete. Total MATH problems evaluated: 5

============================================================
测试完成！
============================================================
准确率: 80.00%
Pass@1: 80.00%

总成本: $0.1234
```

______________________________________________________________________

#### 方式 2: 使用本地模型（推荐高级用户）

使用本地 DyPlanner 模型可以：

- ✅ **免费运行** Designer（不消耗 API 配额）
- ✅ **更快速度**（无网络延迟）
- ✅ **隐私保护**（数据不离开本地）

**步骤 1：部署 DyPlanner 模型**

```bash
# 安装 vLLM（如果还没安装）
pip install vllm

# 下载并部署 DyPlanner 模型
vllm serve wyf23187/DyPlanner \
    --port 8000 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 8192

# 保持这个终端运行，在新终端中继续
```

**GPU 要求**：

- DyPlanner: 需要约 20-30GB GPU 显存
- 如果显存不足，可以添加参数：
  ```bash
  --tensor-parallel-size 2  # 使用 2 个 GPU
  --quantization awq        # 使用量化（减少显存）
  ```

**步骤 2：测试本地模型连接**

```python
# test_local_model.py
from dyflow import ModelService

# 连接到本地 vLLM 服务器
local_service = ModelService.local(temperature=0.1)

# 测试生成
response = local_service.generate(
    prompt="解决这个问题：1 + 1 = ?",
    max_tokens=100
)

print("模型响应:", response['response'])
print("连接成功！")
```

```bash
# 运行测试
python test_local_model.py
```

**步骤 3：使用本地模型运行 Benchmark**

创建 `test_benchmark_local.py`：

```python
#!/usr/bin/env python3
"""
使用本地 DyPlanner 运行 Benchmark
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from benchmarks import MathBenchmark
from dyflow import WorkflowExecutor, ModelService

def solve_math_problem(question: str):
    """使用本地 DyPlanner + 云端 Executor"""
    # 使用本地 DyPlanner 作为 Designer（免费）
    designer = ModelService.local(temperature=0.1)

    # 使用云端模型作为 Executor
    executor = ModelService(model='gpt-4o-mini', temperature=0.01)

    workflow = WorkflowExecutor(
        problem_description=question + "\n\n请逐步解决问题，将最终答案放在 \\boxed{} 中。",
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )

    answer = workflow.execute()
    design_history = workflow.get_design_history()

    return answer, design_history

def main():
    benchmark = MathBenchmark(
        execution_model='gpt-4o-mini',
        baseline='DyFlow_Local',
        mode='test',
        samples_per_task=1
    )

    judge_service = ModelService(model='gpt-4o-mini')
    designer_service = ModelService.local()

    print("使用本地 DyPlanner 模型运行 Benchmark")

    benchmark.run(
        generate_service=designer_service,
        judge_service=judge_service,
        function=solve_math_problem,
        size=10,             # 测试 10 题
        max_workers=3,
        pass_k=1
    )

    metrics = benchmark.calculate_metrics()
    print(f"\n准确率: {metrics['accuracy']:.2%}")

if __name__ == "__main__":
    main()
```

```bash
# 运行（确保 vLLM 服务器在另一个终端运行）
python test_benchmark_local.py
```

______________________________________________________________________

### 运行所有 Benchmark

#### 完整评估脚本

创建 `run_all_benchmarks.py`：

```python
#!/usr/bin/env python3
"""
运行所有 DyFlow Benchmarks
可配置模型和评估规模
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.abspath('.'))

from benchmarks import (
    MathBenchmark,
    HumanEvalBenchmark,
    LiveBenchBenchmark,
    PubMedQABenchmark,
    SocialMazeBenchmark
)
from dyflow import WorkflowExecutor, ModelService

# 配置
USE_LOCAL_DESIGNER = True  # 是否使用本地 DyPlanner
EXECUTOR_MODEL = 'gpt-4o-mini'
JUDGE_MODEL = 'gpt-4o-mini'

def solve_reasoning_problem(question: str):
    """通用推理问题解决函数"""
    if USE_LOCAL_DESIGNER:
        designer = ModelService.local()
    else:
        designer = ModelService(model='gpt-4o')

    executor = ModelService(model=EXECUTOR_MODEL)

    workflow = WorkflowExecutor(
        problem_description=question,
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )

    answer = workflow.execute()
    history = workflow.get_design_history()
    return answer, history

def solve_code_problem(prompt: str):
    """代码生成问题解决函数"""
    if USE_LOCAL_DESIGNER:
        designer = ModelService.local()
    else:
        designer = ModelService(model='gpt-4o')

    executor = ModelService(model=EXECUTOR_MODEL)

    workflow = WorkflowExecutor(
        problem_description=prompt + "\n\n返回完整的函数实现，包含所有必要的导入。不要包含测试代码。",
        designer_service=designer,
        executor_service=executor,
        save_design_history=True
    )

    code = workflow.execute()
    history = workflow.get_design_history()
    return code, history

def run_benchmark(benchmark_name: str, size: int = None, max_workers: int = 5):
    """运行指定的 Benchmark"""

    # 配置服务
    if USE_LOCAL_DESIGNER:
        designer_service = ModelService.local()
    else:
        designer_service = ModelService(model='gpt-4o')

    judge_service = ModelService(model=JUDGE_MODEL)

    print("\n" + "=" * 70)
    print(f"运行 {benchmark_name.upper()} Benchmark")
    print("=" * 70)

    if benchmark_name == 'math':
        benchmark = MathBenchmark(
            execution_model=EXECUTOR_MODEL,
            baseline='DyFlow',
            mode='test',
            samples_per_task=1
        )
        benchmark.run(
            generate_service=designer_service,
            judge_service=judge_service,
            function=lambda q: solve_reasoning_problem(q + "\n\n请逐步解决，答案用 \\boxed{} 包裹。"),
            size=size,
            max_workers=max_workers,
            pass_k=1
        )

    elif benchmark_name == 'humaneval':
        benchmark = HumanEvalBenchmark(
            execution_model=EXECUTOR_MODEL,
            baseline='DyFlow',
            mode='test',
            samples_per_task=1
        )
        benchmark.run(
            solve_fn=solve_code_problem,
            generate_service=designer_service,
            judge_service=judge_service,
            size=size,
            max_workers=min(max_workers, 4),  # HumanEval 推荐最多 4 workers
            pass_k=1
        )

    elif benchmark_name == 'livebench':
        benchmark = LiveBenchBenchmark(
            execution_model=EXECUTOR_MODEL,
            baseline='DyFlow',
            mode='test'
        )
        benchmark.run(
            generate_service=designer_service,
            judge_service=judge_service,
            function=lambda q: solve_reasoning_problem(q + "\n\n请逐步分析并给出答案。"),
            size=size,
            max_workers=max_workers,
            pass_k=1
        )

    elif benchmark_name == 'pubmedqa':
        benchmark = PubMedQABenchmark(
            execution_model=EXECUTOR_MODEL,
            baseline='DyFlow',
            mode='test'
        )
        benchmark.run(
            generate_service=designer_service,
            judge_service=judge_service,
            function=solve_reasoning_problem,
            size=size,
            max_workers=max_workers,
            pass_k=1
        )

    elif benchmark_name == 'socialmaze':
        benchmark = SocialMazeBenchmark(
            execution_model=EXECUTOR_MODEL,
            baseline='DyFlow',
            mode='test'
        )
        benchmark.run(
            generate_service=designer_service,
            judge_service=judge_service,
            function=solve_reasoning_problem,
            size=size,
            max_workers=max_workers,
            pass_k=1
        )

    else:
        print(f"未知的 benchmark: {benchmark_name}")
        return

    # 计算并显示结果
    metrics = benchmark.calculate_metrics()

    print("\n" + "=" * 70)
    print(f"{benchmark_name.upper()} 结果")
    print("=" * 70)
    print(f"准确率: {metrics.get('accuracy', 0):.2%}")
    if 1 in metrics:
        print(f"Pass@1: {metrics[1]:.2%}")

    # 显示成本
    designer_stats = designer_service.get_usage_stats()
    judge_stats = judge_service.get_usage_stats()

    total_cost = sum(
        stats.get('cost', 0)
        for model_stats in [designer_stats, judge_stats]
        for stats in model_stats.values()
    )
    print(f"成本: ${total_cost:.4f}")

def main():
    parser = argparse.ArgumentParser(description='运行 DyFlow Benchmarks')
    parser.add_argument(
        '--benchmarks',
        nargs='+',
        choices=['math', 'humaneval', 'livebench', 'pubmedqa', 'socialmaze', 'all'],
        default=['all'],
        help='要运行的 benchmarks（默认：all）'
    )
    parser.add_argument(
        '--size',
        type=int,
        default=10,
        help='每个 benchmark 评估的问题数量（默认：10）'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=5,
        help='最大并行 worker 数量（默认：5）'
    )
    parser.add_argument(
        '--use-cloud-designer',
        action='store_true',
        help='使用云端 Designer 而不是本地模型'
    )

    args = parser.parse_args()

    # 设置全局配置
    global USE_LOCAL_DESIGNER
    USE_LOCAL_DESIGNER = not args.use_cloud_designer

    print("=" * 70)
    print("DyFlow Benchmark 评估")
    print("=" * 70)
    print(f"Designer: {'本地 DyPlanner' if USE_LOCAL_DESIGNER else 'GPT-4o'}")
    print(f"Executor: {EXECUTOR_MODEL}")
    print(f"Judge: {JUDGE_MODEL}")
    print(f"每个任务评估: {args.size} 题")
    print(f"最大并行数: {args.max_workers}")
    print("=" * 70)

    # 确定要运行的 benchmarks
    if 'all' in args.benchmarks:
        benchmarks_to_run = ['math', 'humaneval', 'livebench', 'pubmedqa', 'socialmaze']
    else:
        benchmarks_to_run = args.benchmarks

    # 运行所有 benchmarks
    results = {}
    for benchmark_name in benchmarks_to_run:
        try:
            run_benchmark(benchmark_name, size=args.size, max_workers=args.max_workers)
        except KeyboardInterrupt:
            print(f"\n{benchmark_name} 评估被中断")
            break
        except Exception as e:
            print(f"\n错误: {benchmark_name} 评估失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("所有评估完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()
```

#### 使用示例

```bash
# 1. 快速测试（每个 benchmark 10 题）
python run_all_benchmarks.py --size 10

# 2. 只运行数学和代码
python run_all_benchmarks.py --benchmarks math humaneval --size 20

# 3. 使用云端 Designer（不需要本地模型）
python run_all_benchmarks.py --use-cloud-designer --size 5

# 4. 完整评估（所有题目，高并行）
python run_all_benchmarks.py --benchmarks all --size 100 --max-workers 10

# 5. 单个 benchmark 深度评估
python run_all_benchmarks.py --benchmarks math --size 500 --max-workers 20
```

______________________________________________________________________

### 查看和分析结果

#### 结果文件位置

```bash
# 评估结果保存在 benchmarks/results/ 目录
cd benchmarks/results

# 查看目录结构
tree .
# 输出：
# results/
# ├── MATH/
# │   └── test/
# │       ├── DyFlow_gpt-4o-mini.json          # 评估结果
# │       └── DyFlow_gpt-4o-mini_cost.json     # 成本统计
# ├── humaneval/
# │   └── test/
# │       ├── DyFlow_gpt-4o-mini.json
# │       └── DyFlow_gpt-4o-mini_cost.json
# ...
```

#### 分析结果脚本

创建 `analyze_results.py`：

```python
#!/usr/bin/env python3
"""
分析 Benchmark 结果
"""

import json
import os
from pathlib import Path

def analyze_benchmark_results(benchmark_name: str, baseline: str, model: str):
    """分析单个 benchmark 的结果"""

    results_path = f"benchmarks/results/{benchmark_name}/test/{baseline}_{model}.json"
    cost_path = f"benchmarks/results/{benchmark_name}/test/{baseline}_{model}_cost.json"

    if not os.path.exists(results_path):
        print(f"未找到结果文件: {results_path}")
        return

    # 加载结果
    with open(results_path, 'r') as f:
        results = json.load(f)

    # 加载成本（如果存在）
    cost_data = None
    if os.path.exists(cost_path):
        with open(cost_path, 'r') as f:
            cost_data = json.load(f)

    # 分析结果
    print(f"\n{'='*60}")
    print(f"{benchmark_name.upper()} - {baseline} ({model})")
    print(f"{'='*60}")

    total = len(results)
    correct = sum(1 for r in results if r.get('judge_result', False))

    print(f"总题数: {total}")
    print(f"正确数: {correct}")
    print(f"准确率: {correct/total:.2%}")

    # Pass@k 分析
    pass_at_k = {}
    for result in results:
        for key, value in result.items():
            if key.startswith('pass@'):
                if key not in pass_at_k:
                    pass_at_k[key] = []
                pass_at_k[key].append(value)

    if pass_at_k:
        print("\nPass@k 指标:")
        for k in sorted(pass_at_k.keys()):
            avg = sum(pass_at_k[k]) / len(pass_at_k[k])
            print(f"  {k}: {avg:.2%}")

    # 成本分析
    if cost_data:
        print("\n成本统计:")
        total_cost = 0

        for service_name in ['generate_cost', 'judge_cost', 'executor_cost']:
            service_costs = cost_data.get(service_name, {})
            for model_name, stats in service_costs.items():
                cost = stats.get('cost', 0)
                total_cost += cost
                print(f"  {model_name}: ${cost:.4f}")

        print(f"  总成本: ${total_cost:.4f}")
        print(f"  平均每题: ${total_cost/total:.4f}")

    # 错误分析
    errors = [r for r in results if r.get('error')]
    if errors:
        print(f"\n错误数量: {len(errors)}")
        print("错误类型:")
        error_types = {}
        for r in errors:
            error = r.get('error', 'Unknown')
            error_types[error] = error_types.get(error, 0) + 1
        for error, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"  {error}: {count}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='分析 Benchmark 结果')
    parser.add_argument(
        '--benchmark',
        choices=['MATH', 'humaneval', 'livebench', 'PubMedQA', 'socialmaze', 'all'],
        default='all',
        help='要分析的 benchmark'
    )
    parser.add_argument(
        '--baseline',
        default='DyFlow',
        help='基线名称'
    )
    parser.add_argument(
        '--model',
        default='gpt-4o-mini',
        help='模型名称'
    )

    args = parser.parse_args()

    if args.benchmark == 'all':
        benchmarks = ['MATH', 'humaneval', 'livebench', 'PubMedQA', 'socialmaze']
    else:
        benchmarks = [args.benchmark]

    for benchmark in benchmarks:
        try:
            analyze_benchmark_results(benchmark, args.baseline, args.model)
        except Exception as e:
            print(f"分析 {benchmark} 失败: {e}")

if __name__ == "__main__":
    main()
```

```bash
# 分析所有结果
python analyze_results.py

# 分析特定 benchmark
python analyze_results.py --benchmark MATH

# 分析特定配置
python analyze_results.py --benchmark humaneval --baseline DyFlow --model phi-4
```

______________________________________________________________________

### 常见问题与解决方案

#### 问题 1: API 密钥错误

**症状**：

```
Error: Incorrect API key provided
```

**解决方案**：

```bash
# 1. 检查 .env 文件是否存在
ls -la .env

# 2. 检查 API 密钥格式
cat .env | grep API_KEY

# 3. 确保没有多余的空格或引号
# 正确格式：
OPENAI_API_KEY=sk-xxxxx
# 错误格式：
OPENAI_API_KEY="sk-xxxxx"  # 不要加引号
OPENAI_API_KEY = sk-xxxxx   # 等号两边不要有空格
```

#### 问题 2: 数据集未找到

**症状**：

```
FileNotFoundError: [Errno 2] No such file or directory: 'benchmarks/data/MATH/MATH_test.json'
```

**解决方案**：

```bash
# 1. 检查数据集目录
ls -la benchmarks/data/

# 2. 确保在项目根目录运行脚本
pwd  # 应该显示 .../DyFlow

# 3. 如果数据集缺失，重新克隆项目
git clone --recursive https://github.com/wyf23187/DyFlow.git
```

#### 问题 3: 本地模型连接失败

**症状**：

```
ConnectionError: Failed to connect to local model server at http://localhost:8000
```

**解决方案**：

```bash
# 1. 检查 vLLM 服务器是否运行
curl http://localhost:8000/health

# 2. 查看 vLLM 日志
# 在运行 vLLM 的终端查看输出

# 3. 重启 vLLM 服务器
# 按 Ctrl+C 停止，然后重新运行：
vllm serve wyf23187/DyPlanner --port 8000

# 4. 检查端口占用
lsof -i :8000
```

#### 问题 4: GPU 显存不足

**症状**：

```
OutOfMemoryError: CUDA out of memory
```

**解决方案**：

```bash
# 方案 1: 使用量化模型
vllm serve wyf23187/DyPlanner \
    --port 8000 \
    --quantization awq \
    --gpu-memory-utilization 0.8

# 方案 2: 使用多 GPU
vllm serve wyf23187/DyPlanner \
    --port 8000 \
    --tensor-parallel-size 2  # 使用 2 个 GPU

# 方案 3: 减少上下文长度
vllm serve wyf23187/DyPlanner \
    --port 8000 \
    --max-model-len 4096  # 减少到 4K

# 方案 4: 使用云端模型代替
# 在脚本中设置 USE_LOCAL_DESIGNER = False
```

#### 问题 5: 并行评估错误

**症状**：

```
RuntimeError: Too many open files
```

**解决方案**：

```bash
# 方案 1: 减少并行 worker 数量
python run_all_benchmarks.py --max-workers 3

# 方案 2: 增加系统文件描述符限制
ulimit -n 4096

# 方案 3: 在脚本中修改
# 找到 max_workers 参数并减小值
```

#### 问题 6: 评估速度慢

**优化建议**：

```python
# 1. 增加并行度（如果硬件允许）
--max-workers 10

# 2. 使用本地 Designer
USE_LOCAL_DESIGNER = True

# 3. 使用更快的 Executor
EXECUTOR_MODEL = 'gpt-4o-mini'  # 而不是 gpt-4o

# 4. 减少每题的样本数
samples_per_task = 1  # 而不是 5

# 5. 启用结果缓存（断点续传会自动跳过已完成的题目）
```

______________________________________________________________________

### 进阶技巧

#### 1. 自定义 Baseline

```python
# custom_baseline.py
from dyflow import WorkflowExecutor, ModelService

def custom_solve_function(question: str):
    """自定义解决方案"""

    # 使用不同的模型组合
    designer = ModelService(model='claude-3.5-sonnet')
    executor = ModelService(model='gpt-4o')

    # 自定义提示
    custom_prompt = f"""
    请使用以下方法解决问题：
    1. 仔细阅读问题
    2. 识别关键信息
    3. 制定解决策略
    4. 逐步计算
    5. 验证答案

    问题：{question}
    """

    workflow = WorkflowExecutor(
        problem_description=custom_prompt,
        designer_service=designer,
        executor_service=executor
    )

    return workflow.execute()

# 在 benchmark 中使用
benchmark.run(
    function=custom_solve_function,
    baseline='CustomMethod',  # 自定义名称
    ...
)
```

#### 2. 批量实验

```python
# batch_experiments.py
"""运行多个配置的实验"""

configurations = [
    {
        'designer': 'gpt-4o',
        'executor': 'gpt-4o-mini',
        'baseline': 'DyFlow_GPT4o'
    },
    {
        'designer': 'claude-3.5-sonnet',
        'executor': 'gpt-4o-mini',
        'baseline': 'DyFlow_Claude'
    },
    {
        'designer': 'local',
        'executor': 'phi-4',
        'baseline': 'DyFlow_Local'
    }
]

for config in configurations:
    print(f"\n运行配置: {config['baseline']}")

    designer = ModelService.local() if config['designer'] == 'local' else ModelService(model=config['designer'])
    executor = ModelService(model=config['executor'])

    benchmark = MathBenchmark(
        execution_model=config['executor'],
        baseline=config['baseline'],
        mode='test'
    )

    benchmark.run(
        generate_service=designer,
        judge_service=judge,
        function=solve_function,
        size=50
    )
```

#### 3. 实时监控

```python
# monitor.py
"""实时监控评估进度和成本"""

import time
import json
from pathlib import Path

def monitor_progress(benchmark_name: str, baseline: str, model: str):
    """监控评估进度"""

    temp_file = f"benchmarks/results/{benchmark_name}/test/temp_results.json"
    cost_file = f"benchmarks/results/{benchmark_name}/test/temp_cost.json"

    print("开始监控...")

    while True:
        try:
            if os.path.exists(temp_file):
                with open(temp_file) as f:
                    results = json.load(f)

                correct = sum(1 for r in results if r.get('judge_result', False))
                total = len(results)

                print(f"\r进度: {total} 题 | 正确: {correct} | 准确率: {correct/total:.2%}", end='')

            if os.path.exists(cost_file):
                with open(cost_file) as f:
                    cost_data = json.load(f)

                # 计算总成本
                # ...

            time.sleep(5)  # 每 5 秒更新一次

        except KeyboardInterrupt:
            print("\n监控停止")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            time.sleep(5)

# 使用
monitor_progress('MATH', 'DyFlow', 'gpt-4o-mini')
```

______________________________________________________________________
