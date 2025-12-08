# SAGE Studio 作为 Pipeline 的架构设计

## 核心理念

**SAGE Studio 本身就是一个 SAGE Pipeline！**

这是一个优雅的 meta 设计：
- Studio 是 SAGE 框架的**最佳示例应用**
- 展示 SAGE 如何处理实时流式数据
- 展示 SAGE 的 Operator 组合能力
- 自己吃自己的狗粮 (Dogfooding)

## Pipeline 架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SAGE Studio Pipeline                                 │
│                                                                              │
│  ┌─────────────┐                                                            │
│  │   Source    │  WebSocket 接收用户消息                                     │
│  │ UserInput   │  {"message": "怎么写 Related Work?", "session_id": "..."}  │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │  Operator   │  意图分类 + 路由                                            │
│  │IntentRouter │  → KNOWLEDGE_QUERY + [RESEARCH_GUIDANCE]                   │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ├─────────────────┬─────────────────┬─────────────────┐             │
│         ▼                 ▼                 ▼                 ▼             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  Operator   │   │  Operator   │   │  Operator   │   │  Operator   │     │
│  │MemoryLoader │   │KnowledgeRAG │   │ToolExecutor │   │  DirectLLM  │     │
│  │  加载上下文  │   │  知识检索    │   │  执行工具    │   │  直接对话   │     │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘     │
│         │                 │                 │                 │             │
│         └─────────────────┴─────────────────┴─────────────────┘             │
│                                    │                                         │
│                                    ▼                                         │
│                           ┌─────────────┐                                   │
│                           │  Operator   │  组合上下文，生成 Prompt           │
│                           │PromptBuilder│                                   │
│                           └──────┬──────┘                                   │
│                                  │                                           │
│                                  ▼                                           │
│                           ┌─────────────┐                                   │
│                           │  Operator   │  调用 LLM，流式生成                │
│                           │LLMInference │  使用 UnifiedInferenceClient      │
│                           └──────┬──────┘                                   │
│                                  │                                           │
│                                  ├───────────────────┐                      │
│                                  ▼                   ▼                      │
│                           ┌─────────────┐     ┌─────────────┐               │
│                           │  Operator   │     │    Sink     │               │
│                           │ MemorySaver │     │ StreamOutput│               │
│                           │  保存记忆    │     │ WebSocket   │               │
│                           └─────────────┘     └─────────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 参考已有 QA Pipeline

SAGE 已在 `examples/tutorials/L3-kernel/advanced/pipeline_as_service/qa_pipeline_as_service.py` 中实现了一个**完整可运行的 QA Pipeline**：

```
UserInput → EmbeddingSearchOp → ContextBuilderOp → PromptBuilderOp → GeneratorOp → StreamSink
```

它支撑了 Studio 早期的问答体验，并且已经验证：

- **可部署**：可以注册为 service，通过 `call_service` 调用
- **可回放**：自带 mock generator 配置，离线也能跑
- **可扩展**：替换 embedding 或 generator profile 即可对接本地/远程 LLM

我们在 Studio Pipeline 设计上直接复用这条成熟的 QA Pipeline，只在必要处加上“记忆读取 + 工具调用”两个轻量 Operator，避免重新造轮子。

## Operator 定义

### 1. UserInputSource (Source)
```python
@sage_source
class UserInputSource:
    """WebSocket 用户输入源"""

    async def emit(self) -> AsyncGenerator[UserMessage, None]:
        async for msg in websocket.receive():
            yield UserMessage(
                content=msg["message"],
                session_id=msg["session_id"],
                history=msg.get("history", []),
            )
```

### 2. IntentRouterOp (Operator)
```python
@sage_operator
class IntentRouterOp:
    """意图分类与路由"""

    def __init__(self):
        self.classifier = IntentClassifier(mode="hybrid")

    async def process(self, msg: UserMessage) -> RoutedMessage:
        result = await self.classifier.classify(msg.content, msg.history)
        return RoutedMessage(
            original=msg,
            intent=result.intent,
            knowledge_domains=result.knowledge_domains,
        )
```

### 3. MemoryLoaderOp (Operator)
```python
@sage_operator  
class MemoryLoaderOp:
    """加载会话记忆"""

    async def process(self, msg: RoutedMessage) -> ContextEnrichedMessage:
        memory_service = get_memory_service(msg.original.session_id)
        context = await memory_service.retrieve_context(msg.original.content)
        return ContextEnrichedMessage(
            routed=msg,
            memory_context=context,
        )
```

### 4. KnowledgeRAGOp (Operator)
```python
@sage_operator
class KnowledgeRAGOp:
    """知识库检索"""

    def __init__(self):
        self.km = KnowledgeManager()

    async def process(self, msg: ContextEnrichedMessage) -> KnowledgeEnrichedMessage:
        if msg.routed.intent != UserIntent.KNOWLEDGE_QUERY:
            return KnowledgeEnrichedMessage(context=msg, documents=[])

        docs = await self.km.search(
            query=msg.routed.original.content,
            sources=[d.value for d in msg.routed.knowledge_domains or []],
        )
        return KnowledgeEnrichedMessage(context=msg, documents=docs)
```

### 5. PromptBuilderOp (Operator)
```python
@sage_operator
class PromptBuilderOp:
    """构建 LLM Prompt"""

    async def process(self, msg: KnowledgeEnrichedMessage) -> LLMRequest:
        system_prompt = self._build_system_prompt(msg.routed.intent)
        context = self._format_context(msg.memory_context, msg.documents)

        return LLMRequest(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\n用户问题: {msg.original.content}"},
            ],
            session_id=msg.original.session_id,
        )
```

### 6. LLMInferenceOp (Operator)
```python
@sage_operator
class LLMInferenceOp:
    """LLM 推理（流式输出）"""

    def __init__(self):
        self.client = UnifiedInferenceClient.create_with_control_plane(...)

    async def process(self, req: LLMRequest) -> AsyncGenerator[StreamChunk, None]:
        async for chunk in self.client.chat_stream(req.messages):
            yield StreamChunk(
                content=chunk,
                session_id=req.session_id,
                is_final=False,
            )
        yield StreamChunk(content="", session_id=req.session_id, is_final=True)
```

### 7. StreamOutputSink (Sink)
```python
@sage_sink
class StreamOutputSink:
    """WebSocket 流式输出"""

    async def consume(self, chunk: StreamChunk):
        await websocket.send({
            "type": "text" if not chunk.is_final else "done",
            "content": chunk.content,
        })
```

> **提示**：如果只想快速复刻 QA Pipeline，可直接复用现有 Operators（`EmbeddingSearchOp`, `ContextBuilderOp`, `GeneratorOp`, `StreamSink`），再插入 MemoryLoader + KnowledgeManager 即可；若未来需要更多工具/守卫，再新增 Operator。

## Pipeline 定义

```python
from sage.kernel.pipeline import Pipeline

def create_studio_pipeline() -> Pipeline:
    """创建 Studio Pipeline（基于现有 QA Pipeline 加薄层）"""

    pipeline = Pipeline("studio_qa")

    # 直接复用 qa_pipeline_as_service 的核心组件
    source = UserInputSource()
    memory_loader = MemoryLoaderOp()            # 新增：记忆上下文
    knowledge_rag = KnowledgeRAGOp()            # 新增：按需检索
    prompt_builder = PromptBuilderOp()          # 沿用 QA pipeline Prompt
    llm_inference = LLMInferenceOp()            # 沿用 GeneratorOp
    stream_output = StreamOutputSink()          # 沿用 StreamSink

    # 串行连接（保持简单稳定）
    pipeline.add_source(source)
    pipeline.connect(source, memory_loader)
    pipeline.connect(memory_loader, knowledge_rag)
    pipeline.connect(knowledge_rag, prompt_builder)
    pipeline.connect(prompt_builder, llm_inference)
    pipeline.connect(llm_inference, stream_output)

    return pipeline
```

## 与现有架构的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                    当前实现 (Task-based)                         │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Route → AgentOrchestrator → Stream Handler → SSE      │
│  (Python async/await 直接编排)                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 未来演进
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline 实现 (Operator-based)               │
├─────────────────────────────────────────────────────────────────┤
│  Pipeline(Operators) → SAGE Kernel 调度 → 流式输出              │
│  (声明式 Dataflow，可分布式)                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 实现路线

### Phase 1: Task-based（当前目标）
使用 Python async/await 直接实现，验证功能：
- IntentClassifier (service)
- KnowledgeManager (service)  
- AgentOrchestrator (service)
- Tools (classes)

### Phase 2: Operator-based（未来）
将 services 封装为 SAGE Operators：
- 复用 Phase 1 的核心逻辑
- 获得 SAGE Kernel 的调度能力
- 支持分布式部署
- 作为 SAGE 框架的示例应用

### Phase 3: Visual Pipeline（远期）
在 Studio 中可视化编辑 Pipeline：
- 拖拽 Operators
- 可视化数据流
- 实时调试

## 为什么保持简单

1. **现成可跑**：QA Pipeline 已在多轮演示中验证，最小修改即可上线 Studio。
2. **易调试**：串行拓扑便于在 FastAPI/SSE 层面逐步打印和定位问题。
3. **依赖清晰**：每个 Operator 都有现成模块（embedding、prompt、generator），不需要额外的 Guard/Telemetry 依赖。
4. **可渐进增强**：若真有多工具并发/安全审计需求，再在此基础上按需插入新的 Operator，而不是一开始就堆复杂度。
5. **与示例对齐**：便于用户对照 `examples/tutorials/L3-kernel/advanced/pipeline_as_service/qa_pipeline_as_service.py`，降低二次学习成本。

## 优势

1. **Dogfooding**: Studio 使用 SAGE 自己的 Pipeline
2. **示例价值**: 展示如何用 SAGE 构建实时应用
3. **可扩展**: 新功能 = 新 Operator
4. **可分布式**: 利用 SAGE Kernel 的分布式能力
5. **可观测**: Pipeline 自带监控和追踪

## 高级能力（回答“是不是太简单”的问题）

| 维度 | 能力 | 说明 |
|------|------|------|
| **并行** | Fork/ParallelGroup | 记忆、RAG、工具执行并行，减少首 token 延迟 |
| **回路** | Feedback Channel | Guardrail 失败可回退到 PromptBuilder 重生成 |
| **弹性** | Retry/Timeout/Backpressure | 每个 Operator 支持 `max_retries`、`timeout_ms`、`queue_capacity` |
| **优先级** | Priority Scheduling | RequestClassifier 可根据租户/角色打标签，由 Kernel 优先执行 |
| **多租户** | Session Affinity | pipeline key = session id，可在多工作节点上粘性调度 |
| **遥测** | TelemetrySink + OpenTelemetry | 每个阶段输出事件，接入 Prometheus / Jaeger |
| **配额** | Token Budget Guard | LLMInferenceOp 之前计算 tokens，超限提前拒绝 |
| **热插拔** | Operator Registry | YAML 配置即可开关某条支路，便于 A/B 测试 |

此外，还可以：
- 使用 `EventBusSink` 将步骤推送到 Kafka / Redis Stream，支持 Studio 与 CLI 共享同一 pipeline。
- 在 ToolExecutorPool 中按工具类型分桶（IO 密集 vs CPU 密集），并发度不同。
- 对 MemoryLoaderOp 结果做 TTL 缓存，避免频繁查询。
- 将 Pipeline 部署在 Sage Gateway 背后的 Ray Cluster，实现 GPU/CPU 混部。

## 注意事项

- Phase 1 先用 services 实现，确保功能正确
- Phase 2 再抽象为 Operators，避免过度设计
- Operator 粒度要适中，太细碎会增加复杂度
