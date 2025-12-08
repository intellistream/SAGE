# SAGE Studio Multi-Agent 子任务清单

本目录包含所有任务的细化子任务，每个子任务独立可执行。

## 子任务索引

### Task 1: Intent Classifier (意图分类器)
| 子任务 | 文件 | 预计工时 | 前置依赖 | 状态 |
|--------|------|----------|----------|------|
| 1.1 | [task1.1-intent-enums.md](./task1.1-intent-enums.md) | 0.5h | 无 | ✅ 已创建 |
| 1.2 | [task1.2-intent-tools-definition.md](./task1.2-intent-tools-definition.md) | 1h | 1.1 | ✅ 已创建 |
| 1.3 | [task1.3-intent-classifier-core.md](./task1.3-intent-classifier-core.md) | 2h | 1.2 | ✅ 已创建 |
| 1.4 | [task1.4-intent-classifier-tests.md](./task1.4-intent-classifier-tests.md) | 1h | 1.3 | ✅ 已创建 |

### Task 2: Knowledge Manager (知识库管理器)
| 子任务 | 文件 | 预计工时 | 前置依赖 | 状态 |
|--------|------|----------|----------|------|
| 2.1 | [task2.1-knowledge-source-schema.md](./task2.1-knowledge-source-schema.md) | 1h | 无 | ✅ 已创建 |
| 2.2 | [task2.2-document-loader.md](./task2.2-document-loader.md) | 2h | 2.1 | ✅ 已创建 |
| 2.3 | [task2.3-vector-store-integration.md](./task2.3-vector-store-integration.md) | 2h | 2.1 | ✅ 已创建 |
| 2.4 | [task2.4-knowledge-manager-api.md](./task2.4-knowledge-manager-api.md) | 2h | 2.2, 2.3 | ✅ 已创建 |

### Task 3: Agent Orchestrator (Agent 编排器)
| 子任务 | 文件 | 预计工时 | 前置依赖 | 状态 |
|--------|------|----------|----------|------|
| 3.1 | [task3.1-agent-step-schema.md](./task3.1-agent-step-schema.md) | 0.5h | 无 | ✅ 已创建 |
| 3.2 | [task3.2-orchestrator-core.md](./task3.2-orchestrator-core.md) | 2h | Task 1, 2, 3.1 | ✅ 已创建 |
| 3.3 | [task3.3-stream-handler.md](./task3.3-stream-handler.md) | 1h | 3.1 | ✅ 已创建 |
| 3.4 | [task3.4-chat-api-integration.md](./task3.4-chat-api-integration.md) | 1h | 3.2, 3.3 | ✅ 已创建 |

### Task 4: Tools (工具层)
| 子任务 | 文件 | 预计工时 | 前置依赖 | 状态 |
|--------|------|----------|----------|------|
| 4.1 | [task4.1-base-tool.md](./task4.1-base-tool.md) | 1h | sage-libs | ✅ 已创建 |
| 4.2 | [task4.2-knowledge-search-tool.md](./task4.2-knowledge-search-tool.md) | 1h | 2.4, 4.1 | ✅ 已创建 |
| 4.3 | [task4.3-arxiv-search-tool.md](./task4.3-arxiv-search-tool.md) | 1h | 4.1 | ✅ 已创建 |

### Task 5: Frontend (前端改进)
| 子任务 | 文件 | 预计工时 | 前置依赖 | 状态 |
|--------|------|----------|----------|------|
| 5.1 | [task5.1-reasoning-accordion.md](./task5.1-reasoning-accordion.md) | 2h | 无 | ✅ 已创建 |
| 5.2 | [task5.2-chat-message-update.md](./task5.2-chat-message-update.md) | 1h | 5.1 | ✅ 已创建 |
| 5.3 | [task5.3-sse-client.md](./task5.3-sse-client.md) | 2h | Task 3 后端 | ✅ 已创建 |

### Task 6: File Upload & Memory (文件上传与记忆)
| 子任务 | 文件 | 预计工时 | 前置依赖 | 状态 |
|--------|------|----------|----------|------|
| 6.1 | [task6.1-file-upload-service.md](./task6.1-file-upload-service.md) | 2h | 无 | ✅ 已创建 |
| 6.2 | [task6.2-memory-integration.md](./task6.2-memory-integration.md) | 2h | sage-memory | ✅ 已创建 |

## 依赖关系图

```
Task 1 (意图分类器)
  1.1 → 1.2 → 1.3 → 1.4
                 ↓
Task 3 (编排器)  ←───────────────────────────────────────────
  3.1 ──────────→ 3.2 → 3.3 → 3.4                            │
                   ↑         ↓                                │
Task 2 (知识库)    │    Task 5 (前端)                         │
  2.1 ──┬──→ 2.2 ──→ 2.4    5.1 → 5.2 → 5.3                  │
        └──→ 2.3 ──↗                                          │
                   ↓                                          │
Task 4 (工具)      │                                          │
  4.1 ──────────→ 4.2, 4.3                                   │
                                                              │
Task 6 (文件/记忆)                                            │
  6.1 (独立)                                                  │
  6.2 ─────────────────────────────────────────────────────→│
```

## 执行阶段

### 阶段 1 - 基础模块（可完全并行，约 5h）
无前置依赖，可立即开始：
- **1.1** Intent Enums (0.5h)
- **2.1** Knowledge Source Schema (1h)  
- **3.1** AgentStep Schema (0.5h)
- **4.1** BaseTool (1h)
- **5.1** ReasoningAccordion (2h)
- **6.1** File Upload Service (2h)

### 阶段 2 - 核心组件（部分可并行，约 8h）
依赖阶段 1：
- **1.2** → **1.3** Intent Classifier (3h)
- **2.2**, **2.3** → **2.4** Knowledge Manager (6h)
- **4.2** Knowledge Search Tool (1h，依赖 2.4, 4.1)
- **4.3** ArXiv Search Tool (1h，依赖 4.1)
- **5.2** ChatMessage Update (1h，依赖 5.1)
- **6.2** Memory Integration (2h)

### 阶段 3 - 集成测试（约 3h）
依赖阶段 2：
- **1.4** Intent Classifier Tests (1h)
- **3.2** Orchestrator Core (2h，核心集成点)

### 阶段 4 - API & 流式（约 2h）
依赖阶段 3：
- **3.3** Stream Handler (1h)
- **3.4** Chat API Integration (1h)

### 阶段 5 - 前端集成（约 2h）
依赖阶段 4：
- **5.3** SSE Client (2h)

## 快速开始

**可立即并行开始的子任务**（无前置依赖）：
- **1.1**: Intent 枚举定义
- **2.1**: 知识源 Schema 定义
- **3.1**: AgentStep Schema 定义
- **4.1**: BaseTool 基类（复用 sage-libs）
- **5.1**: ReasoningAccordion 组件
- **6.1**: 文件上传服务

这 6 个任务可以同时分配给不同的开发者/AI Agent 执行。

## 使用说明

每个子任务文件包含:
1. **目标**: 明确的任务目标
2. **依赖**: 需要先完成的任务
3. **文件位置**: 要创建/修改的文件路径
4. **提示词**: 完整的实现提示，可直接用于 AI 编程助手
5. **代码模板**: 参考实现
6. **验收标准**: 任务完成检查清单

### 执行方式
复制任务文件中的「提示词」部分到 Copilot Chat，即可开始实现该子任务。

### 总工时估算
- 阶段 1-5 串行执行：约 20h
- 最大并行优化后：约 8-10h
