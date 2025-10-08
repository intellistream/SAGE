# 🎨 SAGE 应用模板使用指南

## 快速开始

SAGE 现在提供 **10 个应用模板**，帮助你快速构建各种 AI 应用。

### 📋 可用模板

| 模板 | 场景 | 难度 |
|------|------|------|
| `rag-simple-demo` | 简单问答演示 | ⭐ 入门 |
| `rag-dense-milvus` | 大规模语义检索 | ⭐⭐⭐ 生产级 |
| `rag-rerank` | 高精度问答 | ⭐⭐⭐ 生产级 |
| `rag-bm25-sparse` | 关键词检索 | ⭐⭐ 中级 |
| `agent-workflow` | 智能体工作流 | ⭐⭐⭐ 高级 |
| `rag-memory-enhanced` | 多轮对话 | ⭐⭐⭐ 高级 |
| `multimodal-cross-search` | 跨模态搜索 | ⭐⭐⭐ 高级 |
| `rag-multimodal-fusion` | 多模态问答 | ⭐⭐⭐ 高级 |
| `hello-world-batch` | 批处理入门 | ⭐ 入门 |
| `hello-world-log` | 日志处理 | ⭐ 入门 |

## 🚀 使用方式

### 方式一: 交互式命令 (推荐)

```bash
sage chat
```

然后输入你的需求，系统会自动匹配最合适的模板：

```
你想构建什么应用？
> 我想使用 Milvus 构建一个大规模语义检索系统

✨ 为你匹配到: Milvus 密集向量检索问答
正在生成配置...
```

### 方式二: 直接获取模板

```python
from sage.tools.templates.catalog import get_template

# 获取模板
template = get_template("rag-dense-milvus")

# 查看 Pipeline 配置
config = template.pipeline_plan()

# 查看使用指导
print(template.guidance)
```

### 方式三: 智能匹配

```python
from sage.tools.templates.catalog import match_templates

# 描述你的需求
requirements = {
    "name": "智能问答系统",
    "goal": "构建高精度的问答系统",
    "constraints": "需要重排序"
}

# 获取最匹配的模板
matches = match_templates(requirements, top_k=3)

for match in matches:
    print(f"{match.template.title}: {match.score:.3f}")
```

## 💡 场景推荐

### 🔍 语义检索场景

**问题**: 需要在大量文档中快速找到相关内容

**推荐模板**: `rag-dense-milvus` 或 `rag-rerank`

```bash
sage chat
> 我要构建一个文档检索系统，文档库有 100 万篇文章
# 系统自动推荐 rag-dense-milvus
```

### 🤖 智能助手场景

**问题**: 需要一个能自主完成复杂任务的 AI 助手

**推荐模板**: `agent-workflow`

```bash
sage chat
> 我需要一个能自动调用工具的智能助手
# 系统自动推荐 agent-workflow
```

### 💬 对话机器人场景

**问题**: 需要记住历史对话的客服机器人

**推荐模板**: `rag-memory-enhanced`

```bash
sage chat
> 构建一个支持多轮对话的客服机器人
# 系统自动推荐 rag-memory-enhanced
```

### 🖼️ 图文搜索场景

**问题**: 需要同时搜索文本和图片

**推荐模板**: `multimodal-cross-search`

```bash
sage chat
> 我要做一个电商图文搜索引擎
# 系统自动推荐 multimodal-cross-search
```

## 📊 模板对比

### 检索方式对比

| 模板 | 检索方式 | 适合场景 | 精确度 | 成本 |
|------|---------|---------|--------|------|
| `rag-dense-milvus` | 密集向量 | 大规模语义搜索 | ⭐⭐⭐⭐ | 💰💰 |
| `rag-rerank` | 向量+重排 | 高精度要求 | ⭐⭐⭐⭐⭐ | 💰💰💰 |
| `rag-bm25-sparse` | 稀疏向量 | 关键词匹配 | ⭐⭐⭐ | 💰 |

### 应用类型对比

| 类型 | 模板 | 复杂度 | 适用场景 |
|------|------|--------|---------|
| RAG 问答 | `rag-dense-milvus` | 中 | 通用问答 |
| RAG 高精度 | `rag-rerank` | 高 | 法律/医疗/金融 |
| Agent | `agent-workflow` | 高 | 复杂任务自动化 |
| 多轮对话 | `rag-memory-enhanced` | 高 | 客服/助手 |
| 多模态 | `multimodal-cross-search` | 高 | 电商/媒体 |

## 🔧 模板定制

每个模板都可以根据需求定制：

```python
from sage.tools.templates.catalog import get_template

template = get_template("rag-dense-milvus")
config = template.pipeline_plan()

# 修改参数
config['stages'][0]['params']['top_k'] = 10  # 改为返回 top-10
config['stages'][2]['params']['model_name'] = 'gpt-4'  # 使用 GPT-4

# 使用修改后的配置
# ...
```

## 📚 更多资源

### 文档

- **[算子清单](../dev-notes/SAGE_LIBS_OPERATORS.md)** - 所有可用的 44 个算子
- **[模板详细说明](../dev-notes/NEW_TEMPLATES_SUMMARY.md)** - 6 个新模板的详细介绍
- **[完成报告](../dev-notes/FINAL_COMPLETION_REPORT.md)** - 项目总结

### 示例代码

- `examples/rag/` - RAG 应用示例
- `examples/agents/` - Agent 应用示例
- `examples/multimodal/` - 多模态应用示例
- `examples/memory/` - 记忆服务示例

### 测试脚本

```bash
# 测试模板匹配
python examples/tutorials/test_template_matching.py

# 查看模板演示
python examples/tutorials/demo_new_templates.py
```

## ❓ 常见问题

### Q: 如何知道应该使用哪个模板？

A: 使用 `sage chat` 命令，描述你的需求，系统会自动为你推荐最合适的模板。

### Q: 模板可以修改吗？

A: 可以！获取模板的 pipeline_plan() 后，你可以修改任何参数。

### Q: 生产环境应该用哪些模板？

A: 推荐：
- `rag-dense-milvus` - 大规模检索
- `rag-rerank` - 高精度问答
- `agent-workflow` - 复杂任务

### Q: 模板使用的算子都是真实的吗？

A: 是的！所有 44 个算子都经过验证，详见 [算子清单](../dev-notes/SAGE_LIBS_OPERATORS.md)

### Q: 我可以创建自己的模板吗？

A: 可以！参考 `packages/sage-tools/src/sage/tools/templates/catalog.py` 中的现有模板，创建自己的模板。

## 🎯 快速验证

```bash
# 1. 查看所有模板
python -c "
from sage.tools.templates.catalog import list_templates
for t in list_templates():
    print(f'{t.id}: {t.title}')
"

# 2. 测试模板匹配
python examples/tutorials/test_template_matching.py

# 3. 尝试交互式命令
sage chat
```

## 💬 获取帮助

- 查看文档: `docs/dev-notes/`
- 查看示例: `examples/`
- 运行测试: `pytest packages/sage-tools/tests/cli/test_chat_pipeline.py`

---

**祝你构建成功！** 🚀

如有问题，请参考详细文档或提交 Issue。
