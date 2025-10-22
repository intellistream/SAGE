# SAGE 包结构重新梳理分析 - Issue #1032

**日期**: 2025-10-22
**问题**: sage-libs 下的代码结构混乱，职责划分不清
**目标**: 重新规划 SAGE 各子包的职责和依赖关系

## 核心调整要点（针对反馈）

### ✅ 解决的关键问题

1. **基础组件下沉**：
   - ❌ 旧方案：core（types, exceptions）在 sage-kernel 中
   - ✅ 新方案：`sage-kernel/core/` → `sage-common/core/`
   - **原因**：核心类型和异常是最基础的定义，被所有包使用，应该在最底层

2. **算子分层问题**：
   - ❌ 旧方案：创建独立的 sage-operators 包
   - ✅ 新方案：算子分两层
     - **基础算子** → `sage-kernel/operators/` (MapFunction 等基类)
     - **领域算子** → `sage-middleware/operators/` (继承基础算子，实现业务逻辑)
   - **原因**：middleware 的 generator 等算子需要继承基础算子，如果 operators 依赖 middleware 会造成循环依赖

3. **agents 归属问题**：
   - ❌ 旧方案1：创建独立的 sage-agents 包
   - ❌ 旧方案2：agents → `sage-apps/agents/` (agents 当作应用)
   - ✅ 新方案：保留 `sage-libs/agents/` 或提升到 `sage-middleware/agents/`
   - **原因**：agents 是**构建应用的框架**，应用可以基于 agents 来构建，所以 agents 应该比应用低一层

4. **studio 层级问题**：
   - ❌ 旧理解：studio 与 apps 平级
   - ✅ 新定位：**studio 是最高层**
   - **原因**：用户通过 studio UI 可视化构建任何应用（包括 agents、RAG 等）

### 📊 新架构简图

```
L6: sage-studio          (可视化构建平台)
      ↓
L5: sage-apps            (应用层 - 使用 agents 框架)
      ↓
L4: sage-middleware      (中间件 + 领域算子 + agents框架)
      ↓
L3: sage-kernel          (数据流引擎 + 基础算子) ← → sage-libs (算法库 + agents?)
      ↓
L1: sage-common          (基础工具 + 核心类型/异常)
```

**关键依赖**：
- common/core（类型、异常）被 kernel、middleware、libs 等使用
- **agents（框架）**在 middleware 或 libs 层，提供代理构建能力
- middleware/operators（领域算子）**继承** kernel/operators（基础算子）
- middleware/operators（领域算子）**使用** sage-libs（算法库）
- **apps（应用）基于 agents 框架**构建多代理应用
- studio（最高层）**编排** apps（应用）

---

## 一、当前问题分析

### 1. sage-libs 的定位问题

**现状**：
```
sage-libs/src/sage/libs/
├── agents/              ❌ 应用层组件（不是库）
├── applications/        ❌ 完整应用（不是库）
├── context/            ✓ 通用数据结构（库）
├── io_utils/           ✓ I/O 工具（库）
├── operators/          ❌ 数据流算子（不是库，应该在 middleware）
├── rag/                ⚠️  混合物 - 算法库 + 数据流算子
├── tools/              ✓ 工具集（库）
├── unlearning/         ✓ 算法库（库）
└── utils/              ✓ 工具函数（库）
```

**核心问题**：
- `agents` - 代理系统属于**应用层**，不属于库
- `operators` 中的 `VLLMServiceGenerator` 是**数据流算子**，应该在 middleware
- `rag/` 中的 `RefinerOperator` 等混合了**算法库**和**数据流算子**
- `applications/` 是**完整应用**，不属于库包

### 2. 依赖关系混乱

**现状不正确的依赖**：
```
sage-libs 依赖 ← sage-middleware (❌ 应该反向)
sage-apps 依赖 ← sage-libs.agents (❌ agents 不在 libs 中)
```

**应该的关系**：
```
sage-common          (基础工具、配置、数据结构)
    ↑
sage-kernel         (核心 dataflow、执行引擎、API)
    ↑
sage-middleware     (中间件、数据流算子、服务集成)
    ↑               ↑
    ├── 依赖 ──────┤
    │               │
sage-libs          (通用算法库、工具)
    ↑
    └── 被 ────→ sage-apps (应用层)
                    ↑
    sage-tools ────→ 工具链、CLI、DevOps
    sage-studio ──→ Web UI
    sage-benchmark→ 性能基准
```

## 二、包结构重新规划

### 核心设计原则调整

**关键认识**：
1. **基础组件下沉**: kernel 中的 core（类型、异常）应该下沉到 sage-common
2. **算子分层**: 基础算子在 kernel，业务算子在上层
3. **agents 是框架**: agents 是构建应用的框架，应该在 libs 或 middleware 层
4. **应用使用 agents**: 应用层（sage-apps）可以基于 agents 框架构建
5. **Studio 最高层**: 通过 UI 构建和编排任何应用（包括基于 agents 的应用）

### 阶段 1：算子分层设计

#### 0.0 基础组件下沉到 sage-common

**需要下沉的内容**：

从 `sage-kernel/core/` 移到 `sage-common/core/`:
- `types.py` - 共享类型定义（ExecutionMode, TaskStatus, TaskID 等）
- `exceptions.py` - 共享异常类（KernelError, SchedulingError 等）
- `constants.py` - 共享常量

**理由**：
- 这些是基础类型和异常，不依赖任何复杂逻辑
- 会被 kernel、middleware、libs 等多个包使用
- 应该在最底层，避免循环依赖

**新结构**：
```
sage-common/src/sage/common/
├── core/                      # ← 从 kernel 移过来
│   ├── __init__.py
│   ├── types.py               # ExecutionMode, TaskStatus, TaskID 等
│   ├── exceptions.py          # KernelError 基类及子类
│   └── constants.py           # 共享常量
├── config/                    # 配置管理
├── utils/                     # 工具函数
└── model_registry/            # 模型注册
```

**sage-kernel 保留**：
```
sage-kernel/src/sage/kernel/
├── api/                       # ✓ Environment, DataStream (依赖运行时)
├── operators/                 # ✓ 基础算子（新增）
├── runtime/                   # ✓ 执行运行时
├── scheduler/                 # ✓ 调度器
├── fault_tolerance/           # ✓ 容错机制
└── utils/                     # ✓ kernel 专用工具
```

#### 1.1 kernel 层：基础算子（sage-kernel/operators）

**位置**: `sage-kernel/src/sage/kernel/operators/`

```
sage-kernel/src/sage/kernel/operators/
├── __init__.py
├── base.py                    # MapFunction, FilterFunction 等基类
├── common/
│   ├── __init__.py
│   ├── transform.py           # 通用转换算子
│   ├── filter.py              # 通用过滤算子
│   └── aggregate.py           # 通用聚合算子
└── README.md
```

**特点**：
- 不依赖具体业务
- 提供基础数据流转换能力
- 被 middleware 和上层继承

#### 1.2 middleware 层：领域算子（sage-middleware/operators）

**位置**: `sage-middleware/src/sage/middleware/operators/`

```
sage-middleware/src/sage/middleware/operators/
├── __init__.py
├── base.py                    # 继承 kernel 的基础算子
├── llm/
│   ├── __init__.py
│   ├── base_generator.py      # 基础生成器算子（抽象类）
│   ├── vllm_generator.py      # vLLM 实现
│   ├── openai_generator.py    # OpenAI 实现
│   └── ollama_generator.py    # Ollama 实现
├── rag/
│   ├── __init__.py
│   ├── base_retriever.py      # 基础检索器算子（抽象类）
│   ├── dense_retriever.py     # 密集检索
│   ├── sparse_retriever.py    # 稀疏检索
│   ├── reranker.py            # 重排序算子
│   └── promptor.py            # 提示词构建算子
├── tool/
│   ├── __init__.py
│   ├── searcher_operator.py   # 搜索算子
│   └── extractor_operator.py  # 提取算子
└── README.md
```

**依赖**：
```
sage-middleware/operators:
  dependencies:
    - isage-kernel (继承基础算子)
    - isage-libs (使用算法库)
```

**特点**：
- 继承 kernel 的基础算子
- 实现具体业务逻辑（LLM、RAG、Tool）
- 可以依赖 sage-libs 的算法

### 阶段 2：代理系统的定位调整

**重新认识 agents**：
- agents 不是应用，而是**构建应用的框架**
- 应用可以基于 agents 框架来实现多代理协作
- agents 应该在 middleware 或 libs 层

**方案对比**：

#### 方案 A：agents 留在 sage-libs（推荐）

**位置**: `sage-libs/src/sage/libs/agents/`

**理由**：
- agents 是可复用的**框架库**，符合 libs 的定位
- 与其他库（rag、tools、unlearning）平级
- 应用层可以导入使用

**结构**：
```
sage-libs/src/sage/libs/
├── agents/                    # ✓ 保留
│   ├── __init__.py
│   ├── base_agent.py          # 基础代理抽象
│   ├── answer_bot.py          # 预定义代理
│   ├── question_bot.py
│   ├── searcher_bot.py
│   ├── critic_bot.py
│   ├── action/                # 代理行动系统
│   ├── planning/              # 代理规划系统
│   ├── profile/               # 代理配置
│   └── runtime/               # 代理运行时
├── rag/                       # RAG 算法库
├── tools/                     # 工具库
└── unlearning/                # 非学习库
```

**应用使用示例**：
```python
# sage-apps 中使用 agents 框架
from sage.libs.agents import BaseAgent, AnswerBot, SearcherBot
from sage.middleware.operators.llm import VLLMGenerator

# 构建自定义代理应用
class MedicalDiagnosisAgent(BaseAgent):
    def __init__(self):
        self.searcher = SearcherBot()
        self.answerer = AnswerBot()
        
    def diagnose(self, symptoms):
        # 使用 agents 框架构建诊断流程
        findings = self.searcher.search(symptoms)
        diagnosis = self.answerer.answer(findings)
        return diagnosis
```

#### 方案 B：agents 提升到 sage-middleware

**位置**: `sage-middleware/src/sage/middleware/agents/`

**理由**：
- agents 可能需要使用 middleware 的算子和服务
- 与 operators 同级，更容易集成

**结构**：
```
sage-middleware/src/sage/middleware/
├── operators/                 # 领域算子
├── agents/                    # ← agents 框架
│   ├── __init__.py
│   ├── base_agent.py
│   ├── answer_bot.py
│   └── ...
└── components/                # 中间件组件
```

**权衡**：
- ✅ 更容易使用 middleware 的能力
- ❌ 增加了 middleware 的复杂度
- ❌ agents 可能不需要那么多 middleware 特性

### 推荐方案：保留在 sage-libs

**最终建议**：
- ✅ **agents 保留在 `sage-libs/agents/`**
- agents 作为**框架库**，提供代理构建能力
- 应用层（sage-apps）基于 agents 框架构建具体应用
- 只移除 `operators/` 和 `applications/` 从 sage-libs

### 阶段 3：清理 sage-libs

**保留** (真正的库)：
```
sage-libs/src/sage/libs/
├── context/           # 数据结构库 ✓
├── io_utils/          # I/O 工具库 ✓
├── rag/               # RAG 算法库 (仅算法，不含算子)
│   ├── retriever.py   # 改为纯算法
│   ├── generator.py
│   ├── reranker.py
│   ├── chunk.py
│   ├── promptor.py
│   └── evaluate.py
├── tools/             # 工具集 ✓
│   ├── arxiv_searcher.py
│   ├── image_captioner.py
│   ├── text_detector.py
│   ├── url_extractor.py
│   └── base_tool.py
├── unlearning/        # 非学习算法库 ✓
└── utils/             # 工具函数 ✓
```

**删除** (移出):
```
❌ operators/        → sage-middleware/operators (领域算子)
❌ applications/     → sage-apps (如果存在)
```

**保留** (agents 是框架库):
```
✓ agents/           # 保留！代理框架库
```

**pyproject.toml** (sage-libs 更新):
```toml
[project]
name = "isage-libs"
description = "SAGE Libraries - Reusable algorithms, utilities and frameworks"

dependencies = [
    "isage-kernel>=0.1.0",  # 只依赖核心
    
    # Vector databases
    "chromadb>=1.0.20",
    "pymilvus[model]>=2.4.0",
    
    # Evaluation tools
    "datasets>=2.0.0",
    "evaluate>=0.4.0",
    "rouge-score>=0.1.0",
    
    # RAG libraries
    "sentence-transformers>=3.1.0",
    "PyPDF2>=3.0.0",
    
    # Agent framework dependencies
    "pydantic>=2.0.0",
    "tenacity>=8.0.0",
]

# 不再依赖 middleware
```

### 阶段 4：更新 sage-apps 使用 agents 框架

### 阶段 4：更新 sage-apps 使用 agents 框架

**应用示例**：应用基于 agents 框架构建

```
packages/sage-apps/src/sage/apps/
├── __init__.py
├── medical_diagnosis/         # 医疗诊断应用
│   ├── __init__.py
│   ├── diagnosis_agent.py     # 使用 agents 框架
│   └── medical_pipeline.py
├── video_intelligence/        # 视频智能应用
│   ├── __init__.py
│   ├── video_agent.py         # 使用 agents 框架
│   └── video_pipeline.py
├── customer_service/          # 客服应用
│   ├── __init__.py
│   ├── service_agent.py       # 使用 agents 框架
│   └── service_pipeline.py
└── research_assistant/        # 研究助手应用
    ├── __init__.py
    ├── research_agent.py      # 使用 agents 框架
    └── research_pipeline.py
```

**使用 agents 框架的示例**：
```python
# sage-apps/medical_diagnosis/diagnosis_agent.py
from sage.libs.agents import BaseAgent, AnswerBot, SearcherBot
from sage.middleware.operators.llm import VLLMGenerator
from sage.libs.rag.retriever import DenseRetriever

class DiagnosisAgent(BaseAgent):
    """医疗诊断代理 - 基于 agents 框架构建"""
    
    def __init__(self):
        super().__init__()
        self.searcher = SearcherBot(
            retriever=DenseRetriever(index_path="medical_kb")
        )
        self.answerer = AnswerBot(
            generator=VLLMGenerator(model="medical-llm")
        )
        
    def diagnose(self, symptoms: str) -> str:
        """诊断流程"""
        # 1. 搜索相关医学知识
        findings = self.searcher.search(symptoms)
        
        # 2. 生成诊断建议
        diagnosis = self.answerer.answer(
            query=symptoms,
            context=findings
        )
        
        return diagnosis

# 在应用中使用
from sage.apps.medical_diagnosis import DiagnosisAgent

agent = DiagnosisAgent()
result = agent.diagnose("患者出现发热和咳嗽症状")
```

**依赖**：
```
sage-apps:
  dependencies:
    - isage-middleware>=0.1.0  # 使用算子
    - isage-libs>=0.1.0        # 使用 agents 框架和其他库
```

### 阶段 5：更新 sage-studio 为最高层

**现在定位**：
- Studio 是最高层的可视化构建平台
- 用户通过 Studio UI 编排和构建任何应用
- 包括：代理应用、RAG 应用、自定义流水线

```
packages/sage-studio/
├── pyproject.toml
└── src/sage/studio/
    ├── ui/                    # Web UI 界面
    │   ├── components/
    │   ├── pages/
    │   └── api/
    ├── builder/               # 应用构建器
    │   ├── agent_builder.py   # 代理构建器
    │   ├── pipeline_builder.py # 流水线构建器
    │   └── app_builder.py     # 应用构建器
    ├── templates/             # 应用模板
    │   ├── agent_templates/
    │   ├── rag_templates/
    │   └── custom_templates/
    └── runtime/               # 运行时管理
        └── app_manager.py
```

**依赖**：
```
sage-studio:
  dependencies:
    - isage-apps>=0.1.0        # 所有应用类型
    - isage-middleware>=0.1.0  # 算子和服务
    - isage-libs>=0.1.0        # 算法库
    
    # Web framework
    - fastapi>=0.100.0
    - uvicorn>=0.23.0
    - pydantic>=2.0.0
```

### 阶段 5：更新 sage-studio 为最高层

**现状**：
```
sage-libs/
└── applications/     ❌ 这里不合适
```

**应该**：
```
packages/sage-apps/src/sage/apps/
├── medical_diagnosis/
├── video_intelligence/
└── general_rag/       # 如果有通用应用
```

## 三、依赖关系新架构

### 分层架构（自下而上）

```
┌─────────────────────────────────────────────────────────┐
│              Layer 6: 可视化构建层                        │
│                  sage-studio                             │
│  (Web UI、可视化编排、应用模板、运行时管理)              │
└───────────────────┬─────────────────────────────────────┘
                    │ 依赖所有下层
        ┌───────────┼──────────────┐
        │           │              │
┌───────▼──────┐ ┌─▼──────────┐ ┌─▼────────┐
│   Layer 5:   │ │  Layer 5:  │ │ Layer 5: │
│  sage-apps   │ │sage-tools  │ │sage-bench│
│(基于 agents  │ │(CLI, DevOps)│ │(性能测试)│
│  框架的应用) │ └────────────┘ └──────────┘
└──────┬───────┘
       │ 使用
┌──────▼────────────────────────────────────┐
│          Layer 4: 中间件层                 │
│        sage-middleware                     │
│  ┌────────────────────────────────────┐   │
│  │  operators/ (领域算子)             │   │
│  │  - llm/ (generator 等)             │   │
│  │  - rag/ (retriever, reranker 等)  │   │
│  │  - tool/ (searcher, extractor)    │   │
│  └────────────────────────────────────┘   │
│  components/ (DB、Flow、Mem、TSDB)        │
└──────┬───────────────┬────────────────────┘
       │               │
       │ 继承/依赖     │ 使用
       │               │
┌──────▼──────┐   ┌───▼──────────────────┐
│   Layer 3:  │   │     Layer 3:          │
│sage-kernel  │   │    sage-libs          │
│┌───────────┐│   │ (算法库、框架)        │
││operators/ ││   │ - agents/ (框架)     │
││(基础算子) ││   │ - rag/ (纯算法)      │
│└───────────┘│   │ - tools/             │
│core, api,   │   │ - unlearning/        │
│scheduler... │   │ - context/           │
└──────┬──────┘   └──────────────────────┘
       │
┌──────▼──────────────────────────────────┐
│          Layer 1: 基础层                 │
│         sage-common                      │
│  (Config、Utils、Logging)               │
└─────────────────────────────────────────┘
```

### 关键依赖关系说明

**1. 算子的分层依赖**：
```
middleware/operators (领域算子)
    ↓ 继承
kernel/operators (基础算子)
    ↓ 使用
libs (算法库)
```

例如：
- `kernel/operators/base.py`: 定义 `MapFunction` 基类
- `middleware/operators/llm/base_generator.py`: 继承 `MapFunction`
- `middleware/operators/llm/vllm_generator.py`: 继承 `base_generator`，使用 `libs` 的算法

**2. Studio 的最高层地位**：
```
studio
  ↓ 依赖
apps (基于 agents 框架构建)
  ↓ 使用
libs/agents (框架) + middleware/operators
```

Studio 可以：
- 可视化使用 agents 框架构建代理
- 构建基于代理的应用（医疗、客服等）
- 组装自定义流水线
- 管理应用生命周期

### 依赖矩阵

| 包 | 层级 | 依赖 | 说明 |
|---|------|-----|------|
| **sage-common** | L1 | 无 | 基础工具 + **核心类型/异常** |
| **sage-kernel** | L3 | common | 数据流引擎 + 基础算子 |
| **sage-libs** | L3 | common, kernel | 算法库 + **agents框架** |
| **sage-middleware** | L4 | common, kernel, libs | 中间件 + 领域算子 |
| **sage-apps** | L5 | common, middleware, libs | **基于 agents 框架的应用** |
| **sage-studio** | L6 | common, apps, middleware, libs | 最高层可视化平台 |
| **sage-tools** | L5 | 所有包 | DevOps 工具 |
| **sage-benchmark** | L5 | 所有包 | 性能基准 |

### 核心类型和异常的使用示例

```python
# 在 sage-common/core/types.py 中定义
from enum import Enum

class ExecutionMode(Enum):
    LOCAL = "local"
    REMOTE = "remote"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

# 在 sage-common/core/exceptions.py 中定义
class KernelError(Exception):
    """Base kernel exception"""
    pass

class SchedulingError(KernelError):
    """Scheduling related exception"""
    pass

# 在 sage-kernel 中使用
from sage.common.core.types import ExecutionMode, TaskStatus
from sage.common.core.exceptions import SchedulingError

class Scheduler:
    def schedule(self, task):
        if task.mode == ExecutionMode.LOCAL:
            # ...
            task.status = TaskStatus.RUNNING
        else:
            raise SchedulingError("Unsupported mode")

# 在 sage-middleware 中使用
from sage.common.core.types import TaskStatus
from sage.common.core.exceptions import KernelError

class Service:
    def check_status(self):
        try:
            return TaskStatus.RUNNING
        except Exception as e:
            raise KernelError(f"Status check failed: {e}")

# 在 sage-libs 中使用
from sage.common.core.exceptions import KernelError

class Algorithm:
    def process(self, data):
        if not data:
            raise KernelError("Invalid data")
```

### 算子继承关系示例

```python
# Layer 3: kernel/operators/base.py
class MapFunction:
    """基础映射算子"""
    def execute(self, data):
        raise NotImplementedError

# Layer 4: middleware/operators/llm/base_generator.py
from sage.kernel.operators.base import MapFunction

class BaseGenerator(MapFunction):
    """基础生成器算子（抽象类）"""
    def execute(self, data):
        prompt = self.prepare_prompt(data)
        return self.generate(prompt)
    
    def generate(self, prompt):
        raise NotImplementedError

# Layer 4: middleware/operators/llm/vllm_generator.py
from sage.middleware.operators.llm.base_generator import BaseGenerator
from sage.libs.rag.promptor import Promptor  # 使用算法库

class VLLMGenerator(BaseGenerator):
    """vLLM 生成器算子实现"""
    def __init__(self):
        self.promptor = Promptor()  # 使用 libs
    
    def generate(self, prompt):
        # 调用 vLLM 服务
        return self.call_vllm_service(prompt)
```

## 四、迁移步骤（调整版）

### 第零步：将 kernel/core 下沉到 common

1. **移动文件**：
   - `sage-kernel/src/sage/kernel/core/types.py` → `sage-common/src/sage/common/core/types.py`
   - `sage-kernel/src/sage/kernel/core/exceptions.py` → `sage-common/src/sage/common/core/exceptions.py`
   - `sage-kernel/src/sage/kernel/core/constants.py` → `sage-common/src/sage/common/core/constants.py`

2. **更新导入**：
   ```python
   # 旧导入
   from sage.kernel.core.types import ExecutionMode, TaskStatus
   from sage.kernel.core.exceptions import KernelError
   
   # 新导入
   from sage.common.core.types import ExecutionMode, TaskStatus
   from sage.common.core.exceptions import KernelError
   ```

3. **更新所有包**：
   - sage-kernel: 更新内部导入
   - sage-middleware: 更新类型导入
   - sage-libs: 更新异常导入

### 第一步：在 kernel 中建立基础算子层

1. 创建目录：`sage-kernel/src/sage/kernel/operators/`
2. 定义基础算子接口：
   - `MapFunction`
   - `FilterFunction`
   - `AggregateFunction`
3. 提供通用算子实现

### 第二步：在 middleware 中建立领域算子层

1. 创建目录：`sage-middleware/src/sage/middleware/operators/`
2. 移动并重构代码：
   - `sage-libs/operators/vllm_service.py` → `middleware/operators/llm/vllm_generator.py`
   - `sage-libs/rag/*Operator` → `middleware/operators/rag/`
3. 让领域算子继承 kernel 的基础算子
4. 领域算子可以使用 `sage-libs` 的算法

### 第三步：清理 sage-libs

1. 删除 `operators/` 目录（已移至 middleware）
2. **保留** `agents/` 目录（agents 是框架库）
3. 删除 `applications/` 目录（已移至 apps）
4. 保留 RAG 纯算法在 sage-libs

### 第四步：更新 sage-apps 使用 agents 框架

1. 重新设计应用结构，基于 agents 框架
2. 示例：
   - `medical_diagnosis/` - 使用 agents 框架构建医疗诊断应用
   - `customer_service/` - 使用 agents 框架构建客服应用
3. 更新 `sage-apps/pyproject.toml` 依赖 libs（含 agents）

### 第五步：调整 sage-studio 为最高层

1. 更新 `sage-studio/pyproject.toml`：
   ```toml
   dependencies = [
       "isage-apps>=0.1.0",       # 依赖所有应用
       "isage-libs>=0.1.0",       # agents 框架和其他库
       "isage-middleware>=0.1.0",
   ]
   ```
2. 添加应用构建器功能（包括基于 agents 框架的应用构建）
3. 添加可视化编排界面

### 第六步：更新所有包的依赖关系

1. **sage-kernel**: 不变，继续依赖 common
2. **sage-middleware**: 依赖 kernel + libs
3. **sage-libs**: 只依赖 kernel（保留 agents 框架）
4. **sage-apps**: 依赖 middleware + libs（使用 agents 框架）
5. **sage-studio**: 依赖 apps + middleware + libs
6. **sage-tools**: 依赖所有包

### 第七步：更新文档和导入

1. 更新所有 README
2. 更新 import 语句
3. 更新示例代码
4. 更新架构文档

## 五、快速参考：包职责清单

| 包 | 层级 | 职责 | 示例 |
|---|------|-----|------|
| **sage-common** | L1 | 基础工具 + **核心类型/异常** | Config、Logger、**ExecutionMode、KernelError** |
| **sage-kernel** | L3 | 数据流引擎、调度器、**基础算子** | Environment、Scheduler、MapFunction |
| **sage-libs** | L3 | 算法库 + **agents框架** | RAG算法、Tools、**AgentFramework** |
| **sage-middleware** | L4 | 中间件、**领域算子**、服务集成 | DB、Cache、Generator、Retriever算子 |
| **sage-apps** | L5 | **基于 agents 框架的应用** | 医疗诊断、客服、研究助手 |
| **sage-studio** | L6 | **最高层**可视化构建平台 | Web UI、应用编排、模板管理 |
| **sage-tools** | L5 | 开发工具 | CLI、性能分析、DevOps |
| **sage-benchmark** | L5 | 性能基准测试 | 性能测试用例、基准报告 |

### 组件的层级划分

| 层级 | 位置 | 类型 | 示例 |
|-----|------|------|------|
| **L1** | `common/core/` | 核心类型/异常 | ExecutionMode, TaskStatus, KernelError |
| **L3** | `kernel/operators/` | 基础算子 | MapFunction, FilterFunction |
| **L4** | `middleware/operators/` | 领域算子 | VLLMGenerator, DenseRetriever, Reranker |

**关键点**：
- ✅ 核心类型/异常在 common（最底层，被所有包使用）
- ✅ 基础算子在 kernel（不依赖业务）
- ✅ 领域算子在 middleware（继承基础算子 + 使用 libs）
- ✅ **agents 是框架，在 sage-libs 中**
- ✅ **应用基于 agents 框架构建，在 sage-apps 中**
- ✅ studio 是最高层，可视化构建任何应用

## 六、实施时间表（调整版）

**第一周（基础组件下沉）**：
- [ ] 移动 `sage-kernel/core/` → `sage-common/core/`
- [ ] 更新所有包对 types、exceptions 的导入
- [ ] 测试基础组件下沉后的依赖

**第二周（基础算子层）**：
- [ ] 在 sage-kernel 中创建 `operators/` 基础算子层
- [ ] 定义基础算子接口和抽象类
- [ ] 编写基础算子文档

**第三周（领域算子层）**：
- [ ] 在 sage-middleware 中创建 `operators/` 领域算子层
- [ ] 移动 `sage-libs/operators/vllm_service.py` 
- [ ] 重构为继承 kernel 基础算子的领域算子

**第四周（RAG 算子迁移）**：
- [ ] 从 sage-libs/rag 中分离算子部分到 middleware
- [ ] 迁移 RAG 相关算子（Retriever, Generator, Reranker 等）
- [ ] 保留 RAG 纯算法和 agents 框架在 sage-libs

**第五周（应用层重构）**：
- [ ] 清理 sage-libs（删除 operators、applications，保留 agents）
- [ ] 重构 sage-apps，基于 agents 框架构建应用
- [ ] 更新 sage-apps/pyproject.toml

**第六周（studio 升级）**：
- [ ] 调整 sage-studio 为最高层
- [ ] 添加基于 agents 框架的应用构建器
- [ ] 添加可视化编排功能
- [ ] 更新所有包的依赖关系

**第七周（测试和文档）**：
- [ ] 全面测试所有包
- [ ] 更新所有文档和示例
- [ ] 更新 import 路径

**第八周（发布准备）**：
- [ ] 回归测试
- [ ] 性能测试
- [ ] 准备发布

## 七、向后兼容性考虑

### 过渡期（1-2 个版本）

#### 兼容导入 - sage-libs

```python
# sage-libs/__init__.py - 过渡导入
import warnings

# 对于移到 middleware 的算子
try:
    from sage.middleware.operators.llm import VLLMGenerator
    warnings.warn(
        "Importing operators from sage.libs is deprecated. "
        "Please use: from sage.middleware.operators.llm import VLLMGenerator",
        DeprecationWarning,
        stacklevel=2
    )
except ImportError:
    pass

# 对于移到 apps 的 agents
try:
    from sage.apps.agents import *
    warnings.warn(
        "Importing agents from sage.libs is deprecated. "
        "Please use: from sage.apps.agents import ...",
        DeprecationWarning,
        stacklevel=2
    )
except ImportError:
    pass
```

#### 兼容导入 - sage-middleware

```python
# sage-middleware/__init__.py
# 导出算子供外部使用
from sage.middleware.operators import *
```

### 迁移指南

#### 对于算子的使用者

**旧方式**：
```python
from sage.libs.operators.vllm_service import VLLMServiceGenerator
```

**新方式**：
```python
from sage.middleware.operators.llm import VLLMGenerator
```

#### 对于 agents 的使用者

**保持不变**：
```python
# agents 仍在 sage.libs 中
from sage.libs.agents import BaseAgent, AnswerBot, SearcherBot
```

**应用使用 agents 框架**：
```python
# 在 sage-apps 中基于 agents 框架构建应用
from sage.libs.agents import BaseAgent
from sage.middleware.operators.llm import VLLMGenerator

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.generator = VLLMGenerator()
```

#### 对于算法库的使用者

**不变**：
```python
# 这些保持不变
from sage.libs.rag.chunk import ChunkProcessor
from sage.libs.tools.arxiv_searcher import ArxivSearcher
from sage.libs.unlearning import GaussianUnlearning
```

### 版本计划

- **v0.9.x**: 当前版本（重构前）
- **v1.0.0**: 重构版本
  - 新结构生效
  - 保留兼容导入
  - 发出弃用警告
- **v1.1.x - v1.5.x**: 过渡期
  - 继续保留兼容导入
  - 文档中标注新旧方式
- **v2.0.0**: 完全移除兼容导入
  - 只支持新结构
  - 清理所有过渡代码

## 八、参考资源

### 相关 Issues
- #1032: Package restructuring

### 现有文档
- DEVELOPER.md
- 各包的 README.md
- 架构文档 (在 docs/dev-notes/ 中)

### 需要更新的文档
- [ ] DEVELOPER.md - 更新包结构说明
- [ ] 各包 README.md - 更新职责说明
- [ ] 快速开始指南 - 更新导入示例
- [ ] 架构文档 - 重新梳理依赖关系

---

**作者**: AI Assistant
**最后更新**: 2025-10-21
**状态**: 草案 (待讨论和确认)
