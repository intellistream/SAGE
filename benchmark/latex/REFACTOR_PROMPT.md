# Design Details 章节重构指导 Prompt

## 角色设定

**你是一位经验丰富的 ICML 投稿人和审稿人，正在为 ICML 2026 准备一篇系统论文投稿。**

你深谙 ICML 系统论文的写作规范：

- **篇幅限制**：主文 8 页（不含参考文献），附录不限
- **评审标准**：技术贡献清晰、实验充分、写作简洁
- **常见拒稿原因**：内容冗长、贡献不突出、实现细节过多而缺乏洞察

你的任务是将现有过于冗长的 Design Details 章节重构为符合 ICML 标准的精炼版本，同时将必要的技术细节移至附录以供审稿人深入了解。

______________________________________________________________________

## 任务概述

你需要将 `04.5_design.tex` 中的 Design Details 章节进行精简重构，目标是：

1. **主文 (Design Details)**: 精简至 ICML 系统论文风格，约 2-2.5 页，聚焦核心架构和关键设计决策
1. **附录 (Appendix)**: 将实现细节、完整组件列表、代码级描述移至此处

## 重要原则

### 0. 必须在 main-dev 分支工作

```bash
git checkout main-dev
```

### 1. 必须基于实际代码验证

**切勿凭空描述功能**。在编写任何技术声明前，必须：

```bash
# 验证分层架构
ls -la packages/  # 确认核心包的存在（约10个目录）

# 验证核心组件路径
find packages/sage-kernel/src -name "*.py" | head -20
find packages/sage-middleware/src -name "*.py" | head -20

# 验证具体类/模块是否存在
grep -r "class ExecutionGraph" packages/sage-kernel/
grep -r "class BaseRouter" packages/sage-kernel/
grep -r "class Dispatcher" packages/sage-kernel/
```

### 2. 关键代码路径 (必须核实)

| 组件                 | 预期路径                                                   | 验证命令                                                      |
| -------------------- | ---------------------------------------------------------- | ------------------------------------------------------------- |
| ExecutionGraph       | `packages/sage-kernel/src/sage/kernel/`                    | `grep -r "class ExecutionGraph" packages/`                    |
| TaskNode/TaskFactory | `packages/sage-kernel/src/sage/kernel/`                    | `grep -r "class TaskNode" packages/`                          |
| BaseRouter           | `packages/sage-kernel/src/sage/kernel/`                    | `grep -r "class BaseRouter" packages/`                        |
| Dispatcher           | `packages/sage-kernel/src/sage/kernel/`                    | `grep -r "class Dispatcher" packages/`                        |
| BaseScheduler        | `packages/sage-kernel/src/sage/kernel/`                    | `grep -r "class BaseScheduler" packages/`                     |
| 队列描述符           | `packages/sage-platform/src/sage/platform/`                | `grep -r "QueueDescriptor" packages/`                         |
| RAG Operators        | `packages/sage-middleware/src/sage/middleware/`            | `ls packages/sage-middleware/src/sage/middleware/operators/`  |
| C++ 扩展             | `packages/sage-middleware/src/sage/middleware/components/` | `ls packages/sage-middleware/src/sage/middleware/components/` |

### 3. 包架构说明（main-dev 分支实际状态）

**核心仓库内的包** (packages/ 目录下，共10个)：

- `sage` - Meta-package (PyPI: `isage`)
- `sage-common` - L1 Foundation (PyPI: `isage-common`)
- `sage-platform` - L2 Platform (PyPI: `isage-platform`)
- `sage-kernel` - L3 Core (PyPI: `isage-kernel`)
- `sage-libs` - L3 Algorithms (PyPI: `isage-libs`)
- `sage-middleware` - L4 Middleware (PyPI: `isage-middleware`)
- `sage-cli` - L5 CLI (PyPI: `isage-cli`)
- `sage-tools` - L5 Tools (PyPI: `isage-tools`)
- `sage-benchmark` - Benchmark framework (PyPI: `isage-benchmark`)

**外部独立仓库的包** (作为 PyPI 依赖引入，已确认存在于 pyproject.toml)：

| PyPI 包名        | 用途                      | 依赖位置                                  |
| ---------------- | ------------------------- | ----------------------------------------- |
| `isagellm`       | LLM Gateway/Control Plane | `packages/sage/pyproject.toml`            |
| `isage-vdb`      | SageVDB 向量数据库 (C++)  | `packages/sage-middleware/pyproject.toml` |
| `isage-neuromem` | NeuroMem 记忆系统         | `packages/sage-middleware/pyproject.toml` |
| `isage-flow`     | SageFlow 流处理 (C++)     | `packages/sage-middleware/pyproject.toml` |
| `isage-tsdb`     | SageTSDB 时序数据库 (C++) | `packages/sage-middleware/pyproject.toml` |
| `isage-refiner`  | 上下文压缩                | `packages/sage-middleware/pyproject.toml` |
| `isage-agentic`  | Agent 框架                | `packages/sage-middleware/pyproject.toml` |
| `isage-rag`      | RAG 实现                  | `packages/sage-middleware/pyproject.toml` |
| `isage-eval`     | 评估框架                  | `packages/sage-middleware/pyproject.toml` |
| `isage-finetune` | 微调工具                  | `packages/sage-middleware/pyproject.toml` |
| `isage-privacy`  | 隐私保护                  | `packages/sage-middleware/pyproject.toml` |
| `isage-safety`   | 安全护栏                  | `packages/sage-middleware/pyproject.toml` |
| `isage-studio`   | 可视化工作流              | `packages/sage/pyproject.toml` (optional) |

验证方法：

```bash
# 检查 pyproject.toml 中的实际依赖
grep -E "isage-" packages/sage-middleware/pyproject.toml
grep -E "isage" packages/sage/pyproject.toml

# 检查实际导入
grep -r "from isage" packages/ --include="*.py" | head -10
grep -r "import isage" packages/ --include="*.py" | head -10
```

______________________________________________________________________

## 主文结构 (精简版 Design Details)

### 目标篇幅：2-2.5 页 (ICML 双栏格式)

### 建议结构

```latex
\section{Design Details}
\label{sec:design_details}

% 1段：设计目标 (保留，但精简至3-4句)
\paragraph{Design goals.} [保留composability, resource-aware, isolation三个核心目标，删除冗余解释]

% 2段：分层架构 (精简至1段 + 1个简化图)
\subsection{Layered Architecture}
% 只保留 L1-L5 层的一句话描述，具体包列表移至 Appendix

% 3段：编译与执行 (核心贡献，保留但精简)
\subsection{Compilation and Execution}
% 聚焦：逻辑DAG → 物理执行图的编译过程
% 保留：TaskNode, TaskFactory, 边的物化
% 删除：详细的多输入处理、边索引细节 → Appendix

% 4段：调度与背压 (核心贡献，保留核心机制)
\subsection{Scheduling and Backpressure}
% 保留：bounded queues, backpressure, Dispatcher的decision/execution分离
% 删除：worker loop的详细步骤 → Appendix

% 5段：容错 (精简至1段)
\subsection{Fault Tolerance}
% 一句话概述两种策略，详细实现移至 Appendix

% 6段：中间件操作符 (精简)
\subsection{Middleware Operators}
% 保留：RAG/LLM/Tool operators 的设计理念
% 删除：具体组件列表 (sage_db, sage_mem 等) → Appendix
% 删除：C++ 扩展细节 → Appendix

% 删除或大幅精简以下小节 (移至 Appendix)
% - Algorithmic Libraries (完全移至 Appendix)
% - Inference Engine Integration (保留1段核心思想，细节移至 Appendix)
```

______________________________________________________________________

## Appendix 结构

### 建议创建文件：`appendix_design.tex`

```latex
\section{Additional Design Details}
\label{sec:appendix_design}

\subsection{Complete Package Structure}
% 完整的 L1-L5 包列表和职责
% 外部包列表

\subsection{Execution Graph Implementation}
% TaskNode 和 TaskFactory 的详细接口
% 多输入处理和边索引
% 物理边的完整语义

\subsection{Worker Loop and Routing}
% 完整的 worker loop 伪代码
% BaseRouter 的路由策略详解
% Packet metadata 结构

\subsection{Fault Tolerance Mechanisms}
% Checkpoint-based recovery 完整流程
% Restart-based recovery 策略参数
% Heartbeat monitoring 细节
% 存储后端接口

\subsection{Middleware Component Details}
% sage_db, sage_mem, sage_refiner, sage_flow, sage_tsdb 详细描述
% C++ 扩展架构
% Python 绑定接口

\subsection{Algorithmic Libraries}
% 完整的 sage-libs 模块列表
% 接口设计和注册机制

\subsection{Inference Engine Integration}
% Gateway/Control Plane 架构
% OpenAI 兼容 API 详情
% 多后端支持
```

______________________________________________________________________

## 代码验证 Checklist

在编写/修改任何内容前，必须完成以下验证：

### Phase 1: 架构验证

```bash
# 0. 确保在 main-dev 分支
git checkout main-dev

# 1. 确认分层包结构 (应有约10个目录)
ls packages/

# 2. 确认每层的实际内容
for pkg in sage-common sage-platform sage-kernel sage-libs sage-middleware sage-cli sage-tools sage-benchmark; do
  echo "=== $pkg ==="
  ls packages/$pkg/src/sage/ 2>/dev/null || ls packages/$pkg/src/ 2>/dev/null
done
```

### Phase 2: 核心组件验证

```bash
# 3. ExecutionGraph 相关
grep -rn "class ExecutionGraph" packages/sage-kernel/
grep -rn "class TaskNode" packages/sage-kernel/
grep -rn "class TaskFactory" packages/sage-kernel/

# 4. 调度相关
grep -rn "class Dispatcher" packages/sage-kernel/
grep -rn "class BaseScheduler" packages/sage-kernel/
grep -rn "class PlacementDecision" packages/sage-kernel/

# 5. 路由相关
grep -rn "class BaseRouter" packages/sage-kernel/
grep -rn "class Packet" packages/sage-kernel/

# 6. 容错相关
grep -rn "checkpoint" packages/sage-kernel/ --include="*.py"
grep -rn "fault" packages/sage-kernel/ --include="*.py"
grep -rn "recovery" packages/sage-kernel/ --include="*.py"
```

### Phase 3: 中间件验证

```bash
# 7. Operators 结构
ls packages/sage-middleware/src/sage/middleware/operators/ 2>/dev/null

# 8. Components 结构 (C++ 扩展)
ls packages/sage-middleware/src/sage/middleware/components/ 2>/dev/null

# 9. RAG 相关
grep -rn "RAGPipeline\|Retriever\|Refiner" packages/sage-middleware/
```

### Phase 4: 外部依赖验证

```bash
# 10. 检查哪些是真实外部包，哪些是内部组件
grep -E "isage-|isagellm" packages/*/pyproject.toml
```

______________________________________________________________________

## 写作风格指南

### ICML 系统论文风格特点

1. **简洁直接**：每个段落聚焦一个核心点
1. **贡献导向**：强调"我们做了什么"而非"存在什么"
1. **技术精确**：使用准确的术语，避免模糊描述
1. **可验证性**：声明的功能必须有代码支撑

### 应保留的内容

- 核心设计决策的 **why** 和 **how**
- 与现有系统的差异化点
- 性能/可扩展性相关的架构选择
- 图/伪代码（如有）

### 应移至 Appendix 的内容

- 完整的模块/类列表
- 详细的接口定义
- 实现级别的代码路径描述
- 边缘情况处理
- 配置选项列表

### 应删除的内容

- 重复的解释
- 过于明显的陈述
- 与核心贡献无关的背景知识

______________________________________________________________________

## 输出要求

### 文件 1: `04.5_design.tex` (重写)

- 篇幅：约 120-150 行 LaTeX（不含注释）
- 结构：保留 4-5 个 subsection
- 每个 subsection：2-3 段，每段 4-6 句

### 文件 2: `appendix_design.tex` (新建)

- 篇幅：约 200-300 行 LaTeX
- 结构：6-8 个 subsection
- 包含所有从主文移出的详细内容

### 验证报告

在完成重构后，提供一份简短报告说明：

1. 哪些组件在代码中得到验证
1. 哪些描述需要根据实际代码进行修正
1. 哪些功能是规划中但尚未实现的（应标注或移除）

______________________________________________________________________

## 示例：精简前后对比

### 精简前 (当前版本)

```latex
\subsection{Compilation and Execution Graph}
\label{subsec:dd_compilation}
SAGE compiles a user-authored \emph{logical} pipeline DAG (a sequence of
transformations registered in the environment) into a \emph{physical}
execution graph that is explicit about parallelism, communication, and
routing. Concretely, the \texttt{ExecutionGraph} component in
\texttt{sage-kernel} lowers each logical operator (a
\texttt{BaseTransformation}) into a set of \emph{task replicas} according
to its declared parallelism; each replica is represented as a
\texttt{TaskNode} and is associated with a \texttt{TaskFactory} (which in
turn uses an \texttt{OperatorFactory}) to instantiate the runnable task.
For every logical edge between operators, the compiler materializes a
complete bipartite set of physical edges between upstream and downstream
replicas (i.e., an $m{\times}n$ expansion when the upstream and downstream
parallelisms are $m$ and $n$), producing an execution graph in which the
degree of fan-out and fan-in is no longer implicit.
...
[继续约20行关于边、队列、多输入的细节]
```

### 精简后 (目标版本)

```latex
\subsection{Compilation and Execution}
\label{subsec:compilation}
SAGE compiles user-authored \emph{logical} DAGs into \emph{physical}
execution graphs that make parallelism and communication explicit. Each
logical operator is lowered into task replicas based on its declared
parallelism, and logical edges expand into $m{\times}n$ physical edges
connecting upstream and downstream replicas. Edges are materialized as
bounded channels that implement backpressure, ensuring that slow stages
throttle their producers rather than accumulating unbounded buffers.
Implementation details appear in Appendix~\ref{sec:appendix_design}.
```

______________________________________________________________________

## 最终检查清单

在提交重构结果前，确认：

- [ ] **在 main-dev 分支上工作** (`git branch` 确认)
- [ ] 所有提到的类/模块在代码中存在
- [ ] 分层架构与 `packages/` 目录结构一致（约10个核心包 + 多个外部依赖）
- [ ] 外部包引用已验证（参见 pyproject.toml 中的 `isage-*` 依赖）
- [ ] 主文篇幅不超过 2.5 页
- [ ] Appendix 包含所有移出的详细内容
- [ ] 交叉引用正确（主文引用 Appendix）
- [ ] 无悬空引用或缺失定义

______________________________________________________________________

## 附：当前 tex 文件结构概览 (main-dev 分支)

**实际包结构** (已验证):

```
packages/ 目录 (核心仓库内):
├── sage/              # Meta-package (isage)
├── sage-common/       # L1 Foundation
├── sage-platform/     # L2 Platform
├── sage-kernel/       # L3 Core
├── sage-libs/         # L3 Algorithms
├── sage-middleware/   # L4 Middleware
├── sage-cli/          # L5 CLI
├── sage-tools/        # L5 Tools
└── sage-benchmark/    # Benchmark

外部 PyPI 包 (独立仓库):
├── isagellm           # LLM Gateway/Control Plane
├── isage-vdb          # 向量数据库 (C++)
├── isage-neuromem     # 记忆系统
├── isage-flow         # 流处理 (C++)
├── isage-tsdb         # 时序数据库 (C++)
├── isage-refiner      # 上下文压缩
├── isage-agentic      # Agent 框架
├── isage-rag          # RAG 实现
├── isage-eval         # 评估框架
├── isage-finetune     # 微调工具
├── isage-privacy      # 隐私保护
├── isage-safety       # 安全护栏
└── isage-studio       # 可视化工作流 (optional)
```

```
04.5_design.tex 当前结构：
├── Design goals (1 paragraph)
├── 3.1 Architecture Overview and Layering
│   ├── Core packages by layer (itemize)
│   └── Independent repositories (paragraph)
├── 3.2 Compilation and Execution Graph (长)
├── 3.3 Scheduling, Placement, and Backpressure (长)
├── 3.4 State Management and Fault Tolerance (长)
├── 3.5 Middleware Operators for RAG Pipelines (长)
│   └── 包含 sage_db/mem/refiner/flow/tsdb 列表
├── 3.6 Algorithmic Libraries and Agentic Tooling
└── 3.7 Inference Engine Integration
```

建议精简后：

```
04.5_design.tex 目标结构：
├── Design goals (精简)
├── 3.1 Layered Architecture (合并，精简)
├── 3.2 Compilation and Execution (精简)
├── 3.3 Scheduling and Backpressure (精简)
├── 3.4 Fault Tolerance (大幅精简)
└── 3.5 Middleware and Inference (合并，精简)

appendix_design.tex：
├── A.1 Complete Package Structure
├── A.2 Execution Graph Details
├── A.3 Worker Loop and Routing
├── A.4 Fault Tolerance Mechanisms
├── A.5 Middleware Components
├── A.6 Algorithmic Libraries
└── A.7 Inference Integration
```
