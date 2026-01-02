# SAGE Studio Multi-Agent 架构改进

## 概述

本项目将 SAGE Studio 从单一 Chat 模式升级为 Multi-Agent 架构，支持：

- 按需加载知识库（不再默认加载 docs-src）
- 智能意图识别与工具选择
- 多 Agent 协作处理复杂任务

## 分支信息

- **开发分支**: `feature/studio_multi_agent`
- **基于分支**: `feature/studio_deployment`

## 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SAGE Studio Multi-Agent 架构                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                      用户界面层 (Frontend)                         │     │
│   │   ChatMode.tsx → ReasoningAccordion (推理步骤 + 工具调用可视化)     │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│                                    ▼                                         │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                   AgentOrchestrator (编排层)                       │     │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │     │
│   │   │ Intent      │  │ Tool        │  │ Execution   │              │     │
│   │   │ Classifier  │→ │ Router      │→ │ Coordinator │              │     │
│   │   └─────────────┘  └─────────────┘  └─────────────┘              │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│        ┌───────────────────────────┼───────────────────────────┐            │
│        ▼                           ▼                           ▼            │
│   ┌─────────────┐           ┌─────────────┐           ┌─────────────┐      │
│   │ Knowledge   │           │ Pipeline    │           │ General     │      │
│   │ Agent       │           │ Agent       │           │ Chat Agent  │      │
│   └─────────────┘           └─────────────┘           └─────────────┘      │
│        │                           │                           │            │
│        ▼                           ▼                           ▼            │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                         工具层 (Tools)                             │     │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐         │     │
│   │  │ Knowledge │ │ Workflow  │ │ Code      │ │ API Docs  │         │     │
│   │  │ Search    │ │ Generator │ │ Executor  │ │ Retriever │         │     │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘         │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│                                    ▼                                         │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                    知识源层 (Knowledge Sources)                    │     │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐         │     │
│   │  │ SAGE Docs │ │ Examples  │ │ API Refs  │ │ User      │         │     │
│   │  │ (docs-src)│ │ (examples)│ │(docstring)│ │ Uploads   │         │     │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘         │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                    │                                         │
│                                    ▼                                         │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │                   记忆层 (sage-memory 集成)                        │     │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐         │     │
│   │  │ Short-term│ │ VDB       │ │ KV Store  │ │ Graph     │         │     │
│   │  │ (滑动窗口) │ │ (语义检索)│ │ (关键词)  │ │ (关系推理)│         │     │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘         │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 任务拆分

本项目拆分为 **6 个并行任务**，可以同时开发：

| 任务   | 文件                                                                 | 负责模块            | 依赖                | 优先级 |
| ------ | -------------------------------------------------------------------- | ------------------- | ------------------- | ------ |
| Task 1 | [task1-intent-classifier.md](./task1-intent-classifier.md)           | 意图分类器          | sage-libs selectors | P0     |
| Task 2 | [task2-knowledge-manager.md](./task2-knowledge-manager.md)           | 知识库管理          | 无                  | P0     |
| Task 3 | [task3-agent-orchestrator.md](./task3-agent-orchestrator.md)         | Agent 编排器        | Task 1, 2, 6 接口   | P0     |
| Task 4 | [task4-tools.md](./task4-tools.md)                                   | 工具实现            | Task 2 接口         | P1     |
| Task 5 | [task5-frontend.md](./task5-frontend.md)                             | 前端改进            | Task 3, 6 API       | P1     |
| Task 6 | [task6-file-upload-and-memory.md](./task6-file-upload-and-memory.md) | 文件上传 & 记忆集成 | sage-memory         | P0     |

## 依赖关系

```
Task 1 (IntentClassifier) ────┐
                              │
Task 2 (KnowledgeManager) ────┼──→ Task 3 (AgentOrchestrator) ──→ Task 5 (Frontend)
         │                    │              ▲                           ▲
         └──→ Task 4 (Tools) ─┘              │                           │
                                             │                           │
Task 6 (FileUpload & Memory) ────────────────┴───────────────────────────┘
```

**并行开发策略**：

- Task 1、2、4、6 可以完全并行开发
- Task 3 需要 Task 1、2、6 的接口定义（但可以先 mock）
- Task 5 需要 Task 3、6 的 API 定义（但可以先 mock）

**sage-memory 集成说明**：

- Studio 已有 MemorySettings 组件和 `/chat/memory/*` API
- Task 6 需要将 Memory 与 KnowledgeManager 和 AgentOrchestrator 深度集成
- 支持 4 种记忆后端：short_term、vdb、kv、graph

## 文件结构变更

```
packages/sage-studio/src/sage/studio/
├── services/
│   ├── __init__.py              # 更新导出
│   ├── agent_orchestrator.py    # [新增] Task 3
│   ├── intent_classifier.py     # [新增] Task 1  
│   ├── knowledge_manager.py     # [新增] Task 2
│   ├── file_upload_service.py   # [新增] Task 6 - 文件上传处理
│   ├── memory_integration.py    # [新增] Task 6 - sage-memory 集成
│   ├── docs_processor.py        # [保留] 微调数据处理
│   ├── workflow_generator.py    # [保留] 工作流生成
│   └── ...
├── tools/                       # [新增目录] Task 4
│   ├── __init__.py
│   ├── base.py                  # 工具基类
│   ├── knowledge_search.py      # 知识搜索工具
│   ├── code_executor.py         # 代码执行工具
│   └── api_docs.py              # API 文档工具
├── config/
│   ├── backend/
│   │   └── api.py               # [修改] 集成 Orchestrator + 文件上传 API
│   └── knowledge_sources.yaml   # [新增] 知识源配置
└── frontend/src/
    ├── components/
    │   ├── ChatMode.tsx         # [修改] Task 5
    │   ├── FileUpload.tsx       # [新增] Task 6 - 文件上传组件
    │   ├── MemorySettings.tsx   # [已有] 记忆配置组件
    │   └── ToolCallDisplay.tsx  # [新增] Task 5
    └── services/
        └── api.ts               # [修改] Task 5 + Task 6
```

## 配置文件

新增 `config/knowledge_sources.yaml`：

```yaml
knowledge_sources:
  sage_docs:
    enabled: true
    path: "docs-public/docs_src"
    auto_load: false  # 关键：不自动加载

  examples:
    enabled: true
    path: "examples/"
    auto_load: false

  api_reference:
    enabled: true
    source: "docstrings"
    auto_load: false

  user_uploads:              # 新增：用户上传
    enabled: true
    path: "~/.local/share/sage/studio/uploads/"
    auto_load: false
    max_file_size: "10MB"
    allowed_types:
      - ".pdf"
      - ".md"
      - ".txt"
      - ".py"
      - ".json"
      - ".yaml"

# sage-memory 集成配置
memory:
  default_backend: "short_term"
  backends:
    short_term:
      max_dialogs: 20
    vdb:
      collection_prefix: "studio_memory_"
      embedding_model: "BAAI/bge-small-zh-v1.5"
    kv:
      index_path: "~/.local/share/sage/studio/memory_kv/"
    graph:
      enabled: false  # 暂不启用图记忆

  # 与知识库联动
  knowledge_integration:
    enabled: true
    auto_index_uploads: true      # 上传的文件自动加入记忆
    context_window: 5             # 最近 N 轮对话作为上下文
```

## 开发规范

1. **Layer 归属**: 所有新代码属于 L6 (sage-studio)
1. **依赖方向**: 只能向下依赖 L1-L5，不能反向
1. **测试要求**: 每个模块需要单元测试
1. **文档要求**: 公开接口需要 docstring

## 里程碑

- [ ] M1: 基础框架 - IntentClassifier + KnowledgeManager 接口定义
- [ ] M2: 核心功能 - AgentOrchestrator 集成 + Tools 实现
- [ ] M3: 前端集成 - ChatMode 支持工具调用展示
- [ ] M4: 测试完善 - 单元测试 + 集成测试

## 参考资料

- [SAGE 架构文档](../../package-architecture.md)
- [sage-studio 现有代码](../../../../../packages/sage-studio/)
- [sage-libs workflow generators](../../../../../packages/sage-libs/src/sage/libs/agentic/workflow/)
- **[Studio 作为 Pipeline 的架构设计](./studio-as-pipeline.md)** ← 新增

## 设计理念

### SAGE Studio 本身就是 SAGE Pipeline

Studio 是 SAGE 框架的**最佳示例应用**：

- **Phase 1 (当前)**: 使用 Python services 实现，验证功能
- **Phase 2 (未来)**: 将 services 封装为 SAGE Operators
- **Phase 3 (远期)**: 在 Studio 中可视化编辑 Pipeline
- Pipeline 以 `examples/tutorials/L3-kernel/advanced/pipeline_as_service/qa_pipeline_as_service.py`
  为蓝本，只加薄薄一层记忆/知识检索，保证和已有 QA Pipeline 保持一致、易于维护。

详见 [studio-as-pipeline.md](./studio-as-pipeline.md)

### 意图分类简化

用户意图简化为 **4 类**（而非 6 类）：

| 意图                 | 说明          | 知识领域标签                                         |
| -------------------- | ------------- | ---------------------------------------------------- |
| **KNOWLEDGE_QUERY**  | 知识库问答    | sage_docs, examples, research_guidance, user_uploads |
| **SAGE_CODING**      | SAGE 编程助手 | -                                                    |
| **SYSTEM_OPERATION** | 系统操作      | -                                                    |
| **GENERAL_CHAT**     | 普通对话      | -                                                    |

**研究指导**：导师上传研究方法论、写作经验文档，作为 `research_guidance` 知识领域，学生可通过 KNOWLEDGE_QUERY 意图检索。
