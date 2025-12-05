# Task 1.2: Intent 伪工具定义

## 目标
将意图定义为"伪工具"，以复用 sage-libs 的 Tool Selection 框架。

## 依赖
- Task 1.1 (UserIntent 枚举)

## 文件位置
`packages/sage-studio/src/sage/studio/services/intent_classifier.py` (追加)

## 提示词

```
请在 intent_classifier.py 中定义 INTENT_TOOLS 列表，将意图建模为伪工具。

## 背景
SAGE 的 sage-libs 包含 Tool Selection 算法（KeywordSelector, EmbeddingSelector 等）。
我们将"意图"建模为"工具"，复用这些算法进行分类。

## 要求
1. 导入 Tool schema:
   ```python
   from sage.libs.agentic.agents.action.tool_selection.schemas import Tool
   ```

2. 为每个 UserIntent 创建对应的 Tool 对象:
   - tool_id: 意图枚举值 (如 "KNOWLEDGE_QUERY")
   - name: 人类可读名称 (如 "知识库查询")
   - description: 详细描述，包含触发场景
   - keywords: 关键词列表，用于 KeywordSelector

3. INTENT_TOOLS 示例结构:
```python
INTENT_TOOLS: list[Tool] = [
    Tool(
        tool_id="KNOWLEDGE_QUERY",
        name="知识库查询",
        description="用户询问关于 SAGE 框架、API、配置、使用方法的问题",
        keywords=["SAGE", "怎么用", "如何", "文档", "API", "配置", "教程", ...],
        # ... 其他字段
    ),
    # ... 其他意图
]
```

## 关键词参考
- KNOWLEDGE_QUERY: SAGE, 怎么用, 如何, 文档, API, 配置, 教程, 示例, example
- PIPELINE_GENERATION: 创建流水线, 生成工作流, pipeline, 拓扑图, DAG, 节点
- CODE_ASSISTANCE: 代码, 调试, bug, 错误, 报错, 修复, 写一个, 实现
- SYSTEM_OPERATION: 启动, 停止, 状态, 服务, 部署, 集群, 运行
- GENERAL_CHAT: 你好, 谢谢, 再见, 聊天, 帮助
- PAPER_RESEARCH: 论文, paper, arxiv, 研究, 文献, 搜索论文, 学术

## 注意
- 每个意图至少 10 个关键词（中英文混合）
- description 要足够详细，便于 EmbeddingSelector 计算相似度
- 添加 __all__ 导出 INTENT_TOOLS
```

## 验收标准
- [ ] 6 个意图都有对应的 Tool 对象
- [ ] 每个 Tool 有 10+ 关键词
- [ ] description 详细描述了意图的触发场景
- [ ] 代码可正常导入
