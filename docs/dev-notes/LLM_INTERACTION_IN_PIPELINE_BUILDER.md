# SAGE Pipeline Builder 中的大模型交互流程

## 📍 大模型参与的关键位置

### 1. 入口：`sage chat` 命令
- **文件**: `packages/sage-tools/src/sage/tools/cli/commands/chat.py`
- **类**: `PipelineChatCoordinator`
- **方法**: `handle()` → `_generate_plan()` → `_build_config()`

### 2. 核心生成器：`PipelinePlanGenerator`
- **文件**: `packages/sage-tools/src/sage/tools/cli/commands/pipeline.py`
- **关键方法**: `generate()`

## 🔄 完整的大模型交互流程

```
用户输入："请帮我构建一个问答应用"
    ↓
1. 意图识别 (chat.py)
    _looks_like_pipeline_request() 检测是否为 pipeline 构建请求
    ↓
2. 需求收集 (chat.py)
    _collect_requirements() 收集用户详细需求
    {
        "name": "问答助手",
        "goal": "构建基于文档的问答系统",
        "data_sources": ["文档知识库"],
        ...
    }
    ↓
3. 构建配置 (chat.py)
    _build_config() 准备生成器配置
    - 加载 domain_contexts (示例配置文件)
    - 初始化 knowledge_base (文档+代码检索)
    ↓
4. RAG 检索阶段 (pipeline.py - PipelinePlanGenerator.generate())
    ┌─────────────────────────────────────────┐
    │ 4.1 知识库检索                           │
    │  - 从 docs-public/docs_src 检索文档     │
    │  - 从 examples/ 检索代码示例            │
    │  - 从 packages/sage-libs 检索组件信息   │
    │  - 返回 top_k=5 个最相关片段            │
    └─────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────┐
    │ 4.2 模板匹配 (templates)                │
    │  - 匹配应用模板（基于标签和描述）       │
    │  - 例如：qa_simple, rag_retrieval 等    │
    │  - 提供完整的 pipeline 结构参考         │
    └─────────────────────────────────────────┘
    ↓
    ┌─────────────────────────────────────────┐
    │ 4.3 蓝图匹配 (blueprints)               │
    │  - 匹配配置蓝图（可直接使用的配置）     │
    │  - 包含具体的类路径和参数               │
    └─────────────────────────────────────────┘
    ↓
5. 构建提示词 (_build_prompt())
    组装所有上下文：
    ┌─────────────────────────────────────────┐
    │ System Prompt (SYSTEM_PROMPT)           │
    │  - 说明 SAGE Pipeline 的 JSON 结构      │
    │  - 定义必需字段和规则                   │
    └─────────────────────────────────────────┘
    +
    ┌─────────────────────────────────────────┐
    │ User Prompt:                            │
    │  1. 用户需求 (JSON)                     │
    │  2. 应用模板 (template_contexts)        │
    │  3. 配置蓝图 (blueprint_contexts)       │
    │  4. 知识库检索结果 (knowledge_contexts) │
    │  5. Domain 上下文 (domain_contexts)     │
    │  6. 上一版配置 (previous_plan，如有)    │
    │  7. 用户反馈 (feedback，如有)           │
    └─────────────────────────────────────────┘
    ↓
6. 大模型调用 🤖
    self._client.generate(messages, max_tokens=1200, temperature=0.2)
    ↓
7. 解析响应
    _extract_json_object(response) → JSON 配置
    ↓
8. 验证配置
    _validate_plan(plan) → 检查必需字段
    ↓
9. 返回给用户
    显示配置 → 用户确认 → 保存/运行
```

## 📚 各类上下文的作用

### Domain Contexts
- **来源**: `pipeline_domain.py` - `load_domain_contexts()`
- **内容**: examples/config/*.yaml 中的示例配置
- **作用**: 提供组件速查表，让 LLM 知道有哪些可用组件

### Knowledge Base
- **来源**: `pipeline_knowledge.py` - `PipelineKnowledgeBase`
- **内容**: 
  - `docs-public/docs_src/` - 文档
  - `examples/` - 代码示例
  - `packages/sage-libs/` - 组件代码
- **作用**: RAG 检索，根据用户需求找到最相关的文档和代码

### Templates
- **来源**: `sage.tools.templates` - `ApplicationTemplate`
- **内容**: 预定义的应用模板（如 QA、RAG、Chat 等）
- **作用**: 提供完整的 pipeline 结构参考

### Blueprints
- **来源**: `sage.tools.cli.pipeline_blueprints`
- **内容**: 可直接复用的配置蓝图
- **作用**: 提供可直接使用的配置模式

## 🎯 当前实现的优点

✅ **已经实现 RAG**：知识库检索已集成
✅ **多层次上下文**：模板、蓝图、文档、代码
✅ **迭代优化**：支持用户反馈多轮改进
✅ **验证机制**：生成后验证配置合法性

## 🔧 可以优化的地方

### 1. 增强提示词工程
当前 SYSTEM_PROMPT 比较简单，可以：
- 添加更多示例和最佳实践
- 强调组件的正确使用方式
- 说明常见错误和如何避免

### 2. 改进知识库检索
- 根据不同场景调整检索策略
- 增加代码示例的优先级
- 支持多模态检索（文档+代码混合）

### 3. 模板系统增强
- 扩展模板库（当前数量较少）
- 添加更多领域特定模板
- 模板组合推荐

### 4. 智能推荐
- 根据用户历史生成推荐
- 组件兼容性检查
- 参数自动推断

## 📊 提示词示例

下面是一个实际发送给 LLM 的提示词示例：

```
System:
You are SAGE Pipeline Builder, an expert in configuring Streaming-Augmented 
Generative Execution pipelines...

User:
请根据以下需求生成符合 SAGE 框架的 pipeline 配置 JSON：
{
  "name": "问答助手",
  "goal": "构建基于文档的问答系统",
  "data_sources": ["文档知识库"],
  "latency_budget": "实时响应优先",
  ...
}

以下应用模板仅作灵感参考，请结合需求自行设计：
模板[1]:
模板: 简单问答应用 (qa_simple)
示例路径: examples/rag/qa_without_retrieval.py
...

以下蓝图可直接复用或在此基础上扩展：
蓝图[1]:
Blueprint: qa_simple_blueprint
...

以下是从 SAGE 知识库检索到的参考信息：
知识[1]:
QA 快速入门
构建 QA 处理管道需要以下组件...

知识[2]:
OpenAIGenerator 使用说明
...

以下是与 SAGE 管道构建相关的参考资料：
参考[1]:
# config_for_qa.yaml 示例配置
...

严格输出单个 JSON 对象，不要包含 markdown、注释或多余文字。
```

## 🚀 使用建议

### 为了获得最佳效果：

1. **使用真实 LLM 后端**（而非 mock）
   ```bash
   export SAGE_CHAT_API_KEY="your-api-key"
   sage chat --backend openai --model qwen-max
   ```

2. **启用知识库检索**（默认开启）
   ```bash
   sage pipeline build --name "MyApp" --goal "..." 
   # 知识库会自动加载
   ```

3. **查看检索结果**（调试用）
   ```bash
   sage pipeline build --show-knowledge ...
   # 会显示检索到的文档和模板
   ```

4. **提供详细需求**
   - 明确说明数据源、处理流程、输出要求
   - 提及特定组件或技术（如 "使用 FAISS"、"支持流式输出"）

## 📝 总结

**是的，大模型已经深度参与了 pipeline 构建过程！**

整个流程就是一个完整的 RAG 应用：
1. 用户提问
2. 检索相关文档、模板、示例
3. 组装上下文
4. 调用 LLM 生成配置
5. 验证和优化

templates 中的模板、docs 中的文档、examples 中的代码都会被：
- 索引到知识库
- 根据用户需求检索
- 作为上下文传递给 LLM
- 指导 LLM 生成符合 SAGE 规范的配置
