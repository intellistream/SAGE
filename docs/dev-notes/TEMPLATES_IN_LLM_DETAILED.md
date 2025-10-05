# Templates 参与 LLM 交互 - 详细说明

## 🎯 直接回答你的问题

### Q1: 大模型是在哪一步参考了我们提前构建的 templates？

**答**: 在 **步骤 5** - 构建 LLM 提示词时

### 完整流程（5个步骤）

```
步骤 1: 收集用户需求
  ↓
步骤 2: Template 自动匹配 ⭐
  代码: templates.match_templates(requirements, top_k=3)
  位置: pipeline.py:598-601
  ↓
步骤 3: 转换为 LLM 提示词 ⭐
  代码: match.template.render_prompt(score)
  位置: templates/catalog.py:51-82
  ↓
步骤 4: 组装所有上下文
  代码: _template_contexts(self._template_matches)
  位置: pipeline.py:226-228
  ↓
步骤 5: 注入到 User Prompt ⭐⭐⭐
  代码: _build_prompt(..., template_contexts, ...)
  位置: pipeline.py:654-657
  
  if template_contexts:
      blocks.append("以下应用模板仅作灵感参考，请结合需求自行设计：")
      for idx, snippet in enumerate(template_contexts, start=1):
          blocks.append(f"模板[{idx}]:\n{snippet.strip()}")
  
  ↓
步骤 6: 发送给 LLM 🤖
  messages = [
      {"role": "system", "content": SYSTEM_PROMPT},
      {"role": "user", "content": user_prompt}  # ← 包含 templates!
  ]
  response = self._client.generate(messages, ...)
  位置: pipeline.py:632-637
```

### 关键代码片段

#### 1. Template 匹配（pipeline.py:598-601）
```python
self._template_matches = tuple(
    templates.match_templates(requirements, top_k=3)
)
self._last_template_contexts = _template_contexts(self._template_matches)
```

#### 2. Template 转换为提示词（catalog.py:51-82）
```python
def render_prompt(self, score: Optional[float] = None) -> str:
    """Render a prompt snippet describing the template for LLM guidance."""
    
    plan = self.pipeline_plan()
    stages = plan.get("stages", [])
    stage_lines = [
        f"              • {stage['id']}: {stage['class']} ({stage.get('summary', '')})"
        for stage in stages
    ]
    # ... 格式化为可读的文本
    prompt = textwrap.dedent(f"""
        模板: {self.title} ({self.id}) {score_line}
        示例路径: {self.example_path}
        标签: {', '.join(self.tags) or '通用'}
        描述: {self.description}
        
        默认Pipeline:
          Source: {source_class}
{stage_text}
          Sink: {sink_class}
        
        额外指导:
        {self.guidance.strip()}
    """).strip()
    return prompt
```

#### 3. 注入到 User Prompt（pipeline.py:654-657）
```python
def _build_prompt(self, ..., template_contexts, ...):
    blocks = [
        "请根据以下需求生成符合 SAGE 框架的 pipeline 配置 JSON：",
        json.dumps(requirements, ensure_ascii=False, indent=2),
    ]
    
    # ⭐ 这里！Templates 被注入
    if template_contexts:
        blocks.append("以下应用模板仅作灵感参考，请结合需求自行设计：")
        for idx, snippet in enumerate(template_contexts, start=1):
            blocks.append(f"模板[{idx}]:\n{snippet.strip()}")
    
    # ... 其他上下文
    
    return "\n\n".join(blocks)
```

#### 4. 调用 LLM（pipeline.py:632-637）
```python
user_prompt = self._build_prompt(
    requirements,
    previous_plan,
    feedback,
    knowledge_contexts,
    self._last_template_contexts,  # ← Templates 在这里！
    self._last_blueprint_contexts,
)

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_prompt},  # ← 包含 Templates
]

response = self._client.generate(messages, max_tokens=1200, temperature=0.2)
```

## 📝 实际发送给 LLM 的内容示例

```
System Prompt:
-------------
You are SAGE Pipeline Builder, an expert in configuring SAGE pipelines...
(规范说明)

User Prompt:
-----------
请根据以下需求生成符合 SAGE 框架的 pipeline 配置 JSON：

{
  "name": "智能问答助手",
  "goal": "构建基于文档检索的问答系统",
  "data_sources": ["文档知识库"],
  "latency_budget": "实时响应优先"
}

以下应用模板仅作灵感参考，请结合需求自行设计：

模板[1]:
模板: 客服知识助手 (RAG Simple) (rag-simple-demo) 匹配度: 0.17
示例路径: examples/rag/rag_simple.py
标签: rag, qa, support, 问答, 客户支持, 知识助手
描述: 面向客服问答的简化RAG工作流，使用内置示例算子即可离线演示。

默认Pipeline:
  Source: examples.rag.rag_simple.SimpleQuestionSource
  • retriever: examples.rag.rag_simple.SimpleRetriever (Lookup canned snippets)
  • prompt-builder: examples.rag.rag_simple.SimplePromptor (Combine context)
  • generator: examples.rag.rag_simple.SimpleGenerator (Create answer)
  Sink: examples.rag.rag_simple.SimpleTerminalSink

注意事项:
- 基于 examples.rag.rag_simple 模块构建，适合离线演示
- 无需外部服务或大模型依赖即可运行

额外指导:
适合客服场景的FAQ自动答复。可直接运行，无需远程服务...

模板[2]:
... (其他模板)

以下是从 SAGE 知识库检索到的参考信息：
知识[1]:
... (文档内容)

严格输出单个 JSON 对象，不要包含 markdown、注释或多余文字。
```

**这就是 LLM 看到的完整提示词！Templates 在里面！**

---

## 🧪 Q2: 测试的时候用的是真实的 OpenAI 大模型吗？

**答**: **否，测试使用 Mock（假的生成器）**

### 测试环境 (test_chat_pipeline.py)

```python
@pytest.fixture()
def fake_generator(monkeypatch):
    # 预定义的返回配置
    plan = {
        "pipeline": {"name": "demo", ...},
        "source": {...},
        "stages": [...],
        "sink": {...}
    }
    
    # Mock 生成器
    class DummyGenerator:
        def generate(self, requirements, previous_plan=None, feedback=None):
            self.calls.append((requirements, previous_plan, feedback))
            return plan  # 直接返回预定义配置，不调用 LLM
    
    # 替换真实的 PipelinePlanGenerator
    monkeypatch.setattr(pipeline_builder, "PipelinePlanGenerator", DummyGenerator)
```

**为什么用 Mock？**

1. ❌ **避免依赖外部服务**: 不需要 API Key
2. ⚡ **提高测试速度**: 不需要网络请求
3. ✅ **提高测试稳定性**: 不受 API 限制、网络波动影响
4. 💰 **节省成本**: 不消耗 API 调用额度
5. 🎯 **测试重点**: 测试流程逻辑，而非 LLM 质量

### 生产环境（真实使用）

```python
# 在 PipelinePlanGenerator.__init__ 中
if self.config.backend != "mock":
    # 使用真实的 OpenAI Client
    self._client = OpenAIClient(
        model_name=self.config.model,
        base_url=self.config.base_url,
        api_key=self.config.api_key,
        seed=42,
    )
```

**真实使用示例**:
```bash
# 配置 API Key
export SAGE_CHAT_API_KEY="sk-xxx"

# 使用真实 LLM
sage chat --backend openai --model qwen-max

# 或
sage pipeline build \
  --backend openai \
  --model qwen-turbo \
  --api-key "sk-xxx" \
  --name "MyApp" \
  --goal "构建问答应用"
```

### Mock vs Real 对比

| 特性 | Mock (测试) | Real (生产) |
|------|------------|------------|
| LLM 调用 | ❌ 不调用 | ✅ 真实调用 |
| API Key | ❌ 不需要 | ✅ 必需 |
| 返回内容 | 预定义配置 | LLM 生成 |
| Templates 使用 | ❌ 不传递给 LLM | ✅ 传递给 LLM |
| 速度 | 快（毫秒级） | 慢（秒级） |
| 成本 | 免费 | 按调用收费 |
| 适用场景 | 自动化测试 | 实际使用 |

---

## 🔍 如何验证 Templates 真的被 LLM 使用？

### 方法 1: 启用调试输出

```bash
sage pipeline build \
  --name "TestApp" \
  --goal "构建问答应用" \
  --show-knowledge  # ← 显示匹配的模板
```

输出会包含：
```
╭─────────────── Matched Templates ───────────────╮
│ [1] 客服知识助手 (RAG Simple)                    │
│     Score: 0.17                                 │
│     Tags: rag, qa, support                      │
╰─────────────────────────────────────────────────╯
```

### 方法 2: 添加调试代码

在 `pipeline.py:638` 后添加：

```python
# 调试：打印发送给 LLM 的完整提示词
print("=" * 80)
print("USER PROMPT:")
print("=" * 80)
print(user_prompt)
print("=" * 80)
```

这样你就能看到 Templates 确实在提示词中了！

### 方法 3: 运行演示脚本

```bash
python examples/tutorials/templates_to_llm_demo.py
```

这个脚本详细展示了从 Template 匹配到传递给 LLM 的完整过程。

### 方法 4: 查看真实 LLM 生成的配置

使用真实 API：
```bash
export SAGE_CHAT_API_KEY="your-key"
sage chat --backend openai --model qwen-max --show-knowledge

# 输入：请帮我构建一个问答应用
```

观察生成的配置是否参考了匹配的模板结构。

---

## 📊 Templates 的价值

### 为什么需要 Templates？

1. **结构指导**: 提供完整的 Pipeline 结构示例
2. **组件推荐**: 展示合适的组件组合
3. **最佳实践**: 包含使用建议和注意事项
4. **降低幻觉**: 减少 LLM 生成不存在的组件
5. **加速生成**: 给 LLM 一个好的起点

### Templates 包含什么信息？

```python
ApplicationTemplate(
    id="rag-simple-demo",
    title="客服知识助手 (RAG Simple)",
    tags=("rag", "qa", "support"),  # ← 用于匹配
    description="面向客服问答的简化RAG工作流...",
    example_path="examples/rag/rag_simple.py",
    blueprint_id="rag-simple-demo",
    guidance="适合客服场景的FAQ自动答复...",  # ← 给 LLM 的指导
)
```

### 实际效果

**没有 Templates**:
- LLM 可能生成不存在的类名
- 结构可能不符合 SAGE 规范
- 需要更多轮迭代

**有 Templates**:
- LLM 参考真实存在的组件
- 生成的配置结构正确
- 首次生成成功率更高

---

## 🎯 总结

### 回答你的问题

1. **Templates 在哪一步被参考？**
   - ✅ 在构建 User Prompt 时（pipeline.py:654-657）
   - ✅ 作为"应用模板参考"传递给 LLM
   - ✅ LLM 会基于这些模板生成符合规范的配置

2. **测试用的是真实 OpenAI 吗？**
   - ❌ 测试使用 Mock（DummyGenerator）
   - ✅ 生产环境使用真实 LLM（OpenAIClient）
   - ✅ 通过 `backend` 参数控制（mock / openai）

### 验证方法

```bash
# 查看完整演示
python examples/tutorials/templates_to_llm_demo.py

# 真实使用（需要 API Key）
export SAGE_CHAT_API_KEY="your-key"
sage chat --backend openai --model qwen-max --show-knowledge
```

**Templates 确实被 LLM 使用了，这是整个系统的核心特性！** 🎉
