### 3.1 交互式调试面板 (Playground) ⭐⭐⭐

**功能描述**:
- 画布右侧/下方可折叠面板
- 实时与流程交互，输入问题查看输出
- 显示中间步骤和执行时间
- 支持流式输出

**技术实现**:
```typescript
// frontend-v2/src/components/PlaygroundPanel.tsx
interface PlaygroundPanelProps {
  flowId: string;
  isRunning: boolean;
}

// 功能：
// 1. WebSocket 连接到后端
// 2. 发送用户输入
// 3. 实时接收流式输出
// 4. 显示中间节点状态
```

```python
# backend: api.py
@router.post("/flows/{flow_id}/chat")
async def chat_with_flow(
    flow_id: str,
    message: str,
    tweaks: Optional[Dict] = None,
    stream: bool = True
):
    """实时执行流程并返回结果"""
    # 1. 加载流程
    # 2. 应用 tweaks
    # 3. 执行流程
    # 4. 流式返回中间结果和最终输出
```


#### 3.2 运行时参数覆盖 (Tweaks) ⭐⭐

**功能描述**:
- 在 Playground 中临时覆盖节点参数
- 不修改流程本身
- 支持 JSON 或表单输入
- 记录最佳参数组合

**技术实现**:
```typescript
// PlaygroundPanel.tsx
interface Tweak {
  nodeId: string;
  parameter: string;
  value: any;
}

// UI: 显示可调整的参数列表
// 用户修改后，发送到后端执行
```

**优势**:
- ✅ 快速实验不同参数组合
- ✅ A/B 测试更便捷
- ✅ 找到最佳配置更容易

#### 3.3 状态轮询与实时更新 ⭐

**功能描述**:
- 流程运行时，画布自动刷新节点状态
- 显示每个节点的执行进度
- 高亮当前执行的节点
- 显示错误和警告

**技术实现**:
```typescript
// 前端：每秒轮询或 WebSocket 订阅
useEffect(() => {
  const interval = setInterval(() => {
    fetchJobStatus(jobId).then(status => {
      updateNodeStates(status.nodeStates);
    });
  }, 1000);
}, [jobId]);
```

**优势**:
- ✅ 追平 Phase 2 最后 15% 的核心功能
- ✅ 用户体验大幅提升

#### 3.4 流程模板库 ⭐

**功能描述**:
- 内置 10-15 个常见 RAG 模板
- 一键加载和修改
- 包含详细说明和最佳实践

**模板示例**:
1. 基础问答 RAG
2. 多文档对比 RAG
3. 混合检索 (Dense + Sparse)
4. 重排序 RAG
5. Agent + RAG
6. 多模态 RAG
7. 长文档摘要
8. 知识图谱 RAG

**优势**:
- ✅ 降低入门门槛
- ✅ 展示最佳实践
- ✅ 追平 Coze 的易用性

---


##### 4.1.1 自动化评估框架

**功能描述**:
- 支持多种评估指标（Context Precision, Recall, Faithfulness, Answer Relevancy）
- 自动运行评估数据集
- 生成详细报告和可视化
- 对比多个流程版本

**技术实现**:
```python
# 新增评估算子
class RAGEvaluator(BaseOperator):
    """RAG 评估算子"""
    
    def evaluate(self, 
                 questions: List[str],
                 contexts: List[List[str]],
                 answers: List[str],
                 ground_truths: List[str]) -> Dict:
        """
        计算多种评估指标
        返回详细的评估报告
        """
        return {
            "context_precision": self._calc_precision(contexts, ground_truths),
            "context_recall": self._calc_recall(contexts, ground_truths),
            "faithfulness": self._calc_faithfulness(answers, contexts),
            "answer_relevancy": self._calc_relevancy(answers, questions),
            "latency": self._calc_latency(),
        }
```

**前端可视化**:
```typescript
// EvaluationDashboard.tsx
// 功能：
// 1. 雷达图：显示各项指标得分
// 2. 对比图：多个版本的对比
// 3. 详细列表：每个问题的详细得分
// 4. 建议面板：AI 生成的优化建议
```

**优势**:
- ✅✅✅ **核心差异化竞争力**
- ✅ LangFlow/Coze 都没有的专业功能
- ✅ 从"能用"到"专业"的关键

##### 4.1.2 A/B 测试与实验管理

**功能描述**:
- 同时运行多个流程版本
- 自动对比评估结果
- 统计显著性检验
- 实验历史记录

**优势**:
- ✅ 科学的性能优化流程
- ✅ 适合研究和生产环境

#### 4.2 深度可解释性与调试 ⭐⭐⭐⭐

**核心价值**: 让 RAG 流程透明可控

##### 4.2.1 数据流可视化

**功能描述**:
- 执行后，点击节点查看详细输入输出
- 高亮数据流动路径
- 显示每个 chunk 的来源、分数、排序变化
- 可视化 rerank 前后的变化

**技术实现**:
```typescript
// DataFlowVisualization.tsx
// 功能：
// 1. 点击节点后，在侧边栏显示详细数据
// 2. 对于 retriever：显示所有检索到的 chunks
// 3. 对于 reranker：显示分数变化
// 4. 对于 LLM：显示 prompt 和 response
```

**优势**:
- ✅ 深度理解 RAG 为何返回某个结果
- ✅ 调试复杂流程的利器
- ✅ LangFlow/Coze 无法达到的深度

##### 4.2.2 执行 Trace 与性能分析

**功能描述**:
- 类似 LangSmith 的 trace 功能
- 显示每个节点的执行时间
- 识别性能瓶颈
- 提供优化建议

**可视化**:
```
Timeline View:
[Source] ----2ms-----> [Chunking] ----150ms-----> 
[Embedding] ----500ms-----> [Retrieval] ----50ms-----> 
[Rerank] ----300ms-----> [LLM] ----2000ms-----> [Output]

Bottleneck: LLM (2000ms, 66% of total)
Suggestion: 考虑使用更小的模型或启用缓存
```

**优势**:
- ✅ 性能优化有据可依
- ✅ 生产环境监控基础

#### 4.3 AI 辅助优化 ⭐⭐⭐⭐⭐

**核心价值**: **引入 AI 帮 AI 调优，形成智能闭环**

**功能描述**:
- 基于评估结果，AI Agent 分析流程瓶颈
- 自动生成优化建议（文字 + 代码）
- 支持一键应用建议
- 学习历史优化经验

**示例场景**:
```
输入：一个召回率低的 RAG 流程

AI 分析：
1. 检测到召回率仅 45%，低于推荐的 70%
2. 当前使用单一检索器（Dense）
3. Query 较短，平均 8 个 token

建议：
✅ 添加 BM25 检索器，构建混合检索
✅ 添加 Query Expansion 节点（HyDE 或 Multi-Query）
✅ 调整 top_k 从 5 增加到 10

一键应用：[应用建议] 按钮
```

**技术实现**:
```python
# AI Optimizer Agent
class RAGOptimizer:
    def analyze(self, 
                flow: Pipeline, 
                evaluation: Dict) -> List[Suggestion]:
        """
        使用 LLM 分析流程和评估结果
        生成结构化的优化建议
        """
        prompt = f"""
        你是一个 RAG 专家。分析以下流程和评估结果：
        
        流程结构：{flow.to_dict()}
        评估结果：{evaluation}
        
        请提供 3-5 条具体的优化建议，包括：
        1. 问题诊断
        2. 优化方案
        3. 预期效果
        """
        
        suggestions = llm.generate(prompt)
        return self._parse_suggestions(suggestions)
```

#### 4.4 知识图谱与结构化数据支持 ⭐⭐⭐

**功能描述**:
- 支持从知识图谱检索
- 可视化实体和关系
- 结构化数据源（SQL、GraphQL）
- 混合检索（向量 + 图谱）

**优势**:
- ✅ 支持更复杂的 RAG 场景

---


#### 5.2 Agent 原生支持 ⭐⭐⭐⭐⭐

##### 5.2.1 Agent 编排能力

**功能描述**:
- 在画布中可视化构建 Agent
- 支持 ReAct, Function Calling, Multi-Agent
- Agent 可以调用 SAGE 流程作为 Tool
- 可视化 Agent 的思考过程

**技术实现**:
```python
# 新增 Agent 算子
class AgentExecutor(BaseOperator):
    """Agent 执行器"""
    
    def __init__(self, llm, tools, agent_type="react"):
        self.llm = llm
        self.tools = tools  # 可以是 SAGE 流程
        self.agent_type = agent_type
    
    def execute(self, query):
        # 执行 Agent 循环
        # 返回思考步骤和最终结果
```

**可视化**:
```
Agent 思考过程：
1. [Thought] 我需要检索相关文档
2. [Action] 调用 RAG_Pipeline 工具
3. [Observation] 找到 3 个相关文档
4. [Thought] 信息足够，可以回答
5. [Final Answer] ...
```

**优势**:
- ✅ 补齐最大短板
- ✅ RAG + Agent 的强大组合

##### 5.2.2 SAGE 流程作为 Tool

**功能描述**:
- 任何 SAGE 流程都可封装为 Tool
- 提供标准的 Tool 接口（LangChain, OpenAI Function）
- 自动生成 Tool 描述

**示例**:
```python
# 将 SAGE 流程导出为 LangChain Tool
from langchain.tools import Tool

rag_tool = sage_flow.export_as_tool(
    name="document_qa",
    description="回答关于技术文档的问题"
)

# 在 LangChain Agent 中使用
agent = initialize_agent(
    tools=[rag_tool, ...],
    llm=llm,
    agent="zero-shot-react-description"
)
```

---

## 🎯 实施路线图

### Week 1-2: Phase 3 核心体验

```
Day 1-3:  Playground 基础版（WebSocket + 实时输出）
Day 4-5:  状态轮询（节点状态实时更新）
Day 6-7:  Tweaks 实现（运行时参数覆盖）
Day 8-10: 流程模板库（10个模板 + 文档）
Day 11-14: 测试和优化
```

### Week 3-6: Phase 4 RAG 专业化

```
Week 3:   RAG 评估框架（基础指标 + 数据集支持）
Week 4:   评估可视化（Dashboard + 对比功能）
Week 5:   深度调试（数据流可视化 + Trace）
Week 6:   AI 优化助手（基础版）
```