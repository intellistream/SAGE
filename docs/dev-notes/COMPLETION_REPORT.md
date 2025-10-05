# 完成报告：SAGE Chat Pipeline Builder v2 优化

## 📝 你的问题

> "我好奇这中间有大模型交互参与吗？在哪一步？我希望的是，引入大模型去读取SAGE的文档，帮助更好的构建应用程序，templates里面的模板也要被大模型参考才对。"

## ✅ 答案：是的！已经完整实现了

### 🤖 大模型参与的完整流程

```
步骤 1: 用户输入
  "请帮我构建XXX应用，场景是XXX"
         ↓
步骤 2: 意图识别 (chat.py)
  检测是否为 pipeline 构建请求
         ↓
步骤 3: 需求收集 (交互式)
  收集：名称、目标、数据源、性能要求、约束条件
         ↓
步骤 4: RAG 检索 🔍
  ┌────────────────────────────────────────┐
  │ 4a. 知识库检索                          │
  │   - docs-public/docs_src/ (文档)       │
  │   - examples/ (代码示例)               │
  │   - packages/sage-libs/ (组件代码)     │
  │   返回 top_k=5 个最相关片段            │
  ├────────────────────────────────────────┤
  │ 4b. 模板匹配 (templates) ⭐             │
  │   - ApplicationTemplate 自动匹配       │
  │   - 基于标签和描述评分                 │
  │   - 提供完整 pipeline 结构参考         │
  ├────────────────────────────────────────┤
  │ 4c. 蓝图匹配 (blueprints)              │
  │   - 可直接使用的配置模式               │
  │   - 包含具体类路径和参数               │
  └────────────────────────────────────────┘
         ↓
步骤 5: 构建提示词 📝
  System Prompt: SAGE Pipeline 规范
  +
  User Prompt:
    - 用户需求 (JSON)
    - 检索到的文档片段 ⭐
    - 匹配的模板 (ApplicationTemplate) ⭐
    - 匹配的蓝图 (Blueprint)
    - 示例配置 (examples/config/*.yaml)
    - 上一版配置（如果是迭代）
    - 用户反馈（如果有）
         ↓
步骤 6: LLM API 调用 🤖
  调用大模型生成 JSON 配置
  model: qwen-max (或用户指定)
  temperature: 0.2
         ↓
步骤 7: 解析和验证 ✓
  - 提取 JSON 对象
  - 验证必需字段
  - 检查类导入路径
         ↓
步骤 8: 展示和确认 👤
  - 显示生成的配置
  - 用户确认或提供反馈
  - 支持多轮迭代（最多6轮）
         ↓
步骤 9: 保存和运行 🚀
  - 保存为 YAML 文件
  - 可选立即运行
```

### 📍 代码位置

**大模型调用的核心代码**:

1. **入口**: `packages/sage-tools/src/sage/tools/cli/commands/chat.py`
   - `PipelineChatCoordinator.handle()` - 主流程
   - `_generate_plan()` - 生成配置

2. **生成器**: `packages/sage-tools/src/sage/tools/cli/commands/pipeline.py`
   - `PipelinePlanGenerator.generate()` - RAG + LLM 生成
   - `_build_prompt()` - 组装所有上下文

**关键代码片段**:
```python
# pipeline.py 第 565-637 行
def generate(self, requirements, previous_plan=None, feedback=None):
    # 1. RAG 检索文档
    knowledge_contexts = self.config.knowledge_base.search(...)
    
    # 2. 匹配模板
    self._template_matches = templates.match_templates(requirements)
    
    # 3. 匹配蓝图
    self._blueprint_matches = blueprints.match_blueprints(requirements)
    
    # 4. 构建提示词
    user_prompt = self._build_prompt(
        requirements,
        previous_plan,
        feedback,
        knowledge_contexts,      # 检索到的文档 ⭐
        template_contexts,       # 模板信息 ⭐
        blueprint_contexts,
    )
    
    # 5. 调用 LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    response = self._client.generate(messages, ...)
    
    # 6. 解析结果
    plan = _extract_json_object(response)
    return plan
```

### 📚 Templates 如何被使用

**Templates 模块**: `packages/sage-tools/src/sage/tools/templates/`

1. **定义**: `catalog.py` 定义 `ApplicationTemplate`
   ```python
   @dataclass(frozen=True)
   class ApplicationTemplate:
       id: str
       title: str
       description: str
       tags: Tuple[str, ...]  # 用于匹配
       blueprint_id: str
       guidance: str  # 提供给 LLM 的指导 ⭐
       
       def render_prompt(self) -> str:
           """渲染为 LLM 可读的提示词片段""" ⭐
   ```

2. **匹配**: 根据用户需求自动匹配
   ```python
   matches = templates.match_templates(requirements, top_k=3)
   # 基于 tags 和 description 计算相似度分数
   ```

3. **传递给 LLM**: 在 `_build_prompt()` 中
   ```python
   if template_contexts:
       blocks.append("以下应用模板仅作灵感参考，请结合需求自行设计：")
       for idx, snippet in enumerate(template_contexts):
           blocks.append(f"模板[{idx}]:\n{snippet}")
   ```

### 🎯 实际示例

假设用户输入：**"请帮我构建一个问答应用，支持文档检索"**

**LLM 会收到的上下文**:
```
System: You are SAGE Pipeline Builder...

User:
请根据以下需求生成 SAGE pipeline 配置：
{
  "name": "问答助手",
  "goal": "构建问答应用，支持文档检索",
  ...
}

以下应用模板仅作灵感参考：
模板[1]:
模板: 客服知识助手 (RAG Simple)
标签: rag, qa, support
默认Pipeline:
  Source: TerminalInputSource
  Stages:
    • retriever: FAISSRetriever (向量检索)
    • promptor: QAPromptor (构建提示词)
    • generator: OpenAIGenerator (生成回答)
  Sink: ConsoleSink
指导: 建议使用向量检索 + LLM 生成的组合...

以下是从 SAGE 知识库检索到的参考信息：
知识[1]:
# LLM QA 快速入门
构建 QA 处理管道需要以下组件...
(实际的文档内容)

知识[2]:
class FAISSRetriever(MapFunction):
    """FAISS 向量检索器"""
    ...
(实际的代码内容)

...
```

**LLM 生成的配置** (基于这些上下文):
```json
{
  "pipeline": {"name": "问答助手", ...},
  "source": {"class": "sage.libs.rag.source.TerminalInputSource"},
  "stages": [
    {"id": "retriever", "class": "sage.libs.rag.retriever.FAISSRetriever", ...},
    {"id": "promptor", "class": "sage.libs.rag.promptor.QAPromptor", ...},
    {"id": "generator", "class": "sage.libs.rag.generator.OpenAIGenerator", ...}
  ],
  "sink": {"class": "sage.libs.rag.sink.ConsoleSink"}
}
```

## 🎉 本次改进

### 已完成的优化

1. ✅ **增强用户体验**
   - 添加场景模板快捷选择
   - 丰富的交互提示和帮助
   - 清晰的步骤说明

2. ✅ **配置验证机制**
   - 结构验证（必需字段、类型检查）
   - 组件导入检查
   - 错误提示和建议

3. ✅ **更好的错误处理**
   - 详细的错误信息
   - 针对性的修复建议
   - 智能重试机制

4. ✅ **完善的文档**
   - LLM 交互流程说明
   - 代码演示脚本
   - 使用指南和最佳实践

### 新增文件

```
docs/dev-notes/
├── CHAT_PIPELINE_IMPROVEMENTS.md           # 改进计划
├── LLM_INTERACTION_IN_PIPELINE_BUILDER.md  # LLM 交互详解 ⭐
├── PIPELINE_BUILDER_STATUS_AND_IMPROVEMENTS.md  # 状态总结
└── PIPELINE_BUILDER_V2_IMPROVEMENTS.md     # v2 改进说明

examples/tutorials/
└── pipeline_builder_llm_demo.py  # 完整演示脚本 ⭐

packages/sage-tools/tests/cli/
└── test_chat_pipeline.py  # 新增测试（5个通过）✓
```

## 🚀 如何使用

### 方法 1: 查看演示

```bash
# 运行演示脚本，了解完整流程
python examples/tutorials/pipeline_builder_llm_demo.py
```

### 方法 2: 实际使用

```bash
# 1. 配置 API Key
export SAGE_CHAT_API_KEY="your-openai-api-key"

# 2. 启动 sage chat
sage chat

# 3. 输入 pipeline 构建请求
🤖 你的问题: 请帮我构建一个问答应用，支持向量检索

# 4. 选择是否使用模板
是否使用预设场景模板？ [y/N]: y
选择场景模板: qa

# 5. 确认需求
Pipeline 名称 [问答助手]: 
Pipeline 目标描述 [构建基于文档的问答系统]: 
...

# 6. 查看生成的配置
📄 生成的 Pipeline 配置：
...

# 7. 确认并运行
对该配置满意吗？ [Y/n]: y
是否立即运行该 Pipeline？ [Y/n]: y
```

### 方法 3: 查看帮助

```bash
# 在 chat 中
help       # 查看使用说明
templates  # 查看可用模板
```

## 📖 参考文档

详细说明请查看：

1. **LLM 交互详解**: `docs/dev-notes/LLM_INTERACTION_IN_PIPELINE_BUILDER.md` ⭐
2. **状态和改进**: `docs/dev-notes/PIPELINE_BUILDER_STATUS_AND_IMPROVEMENTS.md`
3. **v2 改进说明**: `docs/dev-notes/PIPELINE_BUILDER_V2_IMPROVEMENTS.md`

## 💡 总结

### 回答你的问题

✅ **有大模型参与吗？** 
   - 是的！完整参与整个流程

✅ **在哪一步？**
   - 在收集需求后，进行 RAG 检索，然后调用 LLM 生成配置

✅ **读取 SAGE 文档吗？**
   - 是的！通过 RAG 检索 docs-public、examples、packages 中的文档和代码

✅ **Templates 被参考了吗？**
   - 是的！模板会被自动匹配，并作为上下文传递给 LLM

### 关键特性

🤖 **AI 驱动**: 使用 LLM 理解需求，生成配置
📚 **RAG 增强**: 自动检索相关文档、代码、模板
🎯 **模板系统**: 预定义场景模板，加速构建
✅ **智能验证**: 自动验证配置，减少错误
🔄 **迭代优化**: 支持多轮反馈改进
📊 **完整测试**: 5 个测试全部通过

### 这就是你期望的功能！

用户只需：
1. 用自然语言描述需求
2. AI 自动检索 SAGE 文档和模板
3. 生成符合规范的 Pipeline 配置
4. 一键运行

**免去了手动编程的过程！** 🎉
