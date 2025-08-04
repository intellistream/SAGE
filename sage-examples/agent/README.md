# 智能体示例 (Agent Examples)

这个目录包含基于SAGE框架的智能体系统示例，展示多智能体协作、决策制定和复杂任务处理。

## 📁 文件列表

### `multiagent_app.py`
多智能体协作系统，展示：
- **QuestionBot** - 问题生成智能体
- **ChiefBot** - 主控制智能体，负责任务分配
- **SearcherBot** - 搜索智能体，执行信息检索
- **AnswerBot** - 答案生成智能体
- **CriticBot** - 评判智能体，负责质量控制

#### 系统架构：
```
QuestionBot → ChiefBot → [SearcherBot/DirectResponse] → AnswerBot → CriticBot
```

#### 运行方式：
```bash
python multiagent_app.py
```

## 🔧 配置文件

使用 `../../config/multiagent_config.yaml` 配置文件，包含：
- 各个智能体的LLM配置
- 工具和过滤器设置
- 数据流控制参数

## 🎯 核心概念

### 智能体类型
1. **源智能体 (Source Agents)** - 生成初始数据
2. **处理智能体 (Processing Agents)** - 执行特定任务
3. **决策智能体 (Decision Agents)** - 进行路由和控制
4. **评估智能体 (Evaluation Agents)** - 质量控制

### 数据流控制
- **过滤器 (Filters)** - 条件路由
- **连接流 (Connect Streams)** - 多路合并
- **工具调用 (Tool Calling)** - 外部服务集成

## 🚀 扩展示例

### 添加新智能体
```python
from sage.lib.agents.custom_bot import CustomBot

custom_stream = (
    env.from_source(CustomBot, config["custom_bot"])
       .sink(ContextFileSink, config["custom_sink"])
)
```

### 工具集成
```python
from sage.lib.tools.custom_tool import CustomTool

tool_stream = (
    agent_stream
        .map(CustomTool, config["custom_tool"])
        .sink(ContextFileSink, config["tool_sink"])
)
```

## 📊 监控和调试

每个智能体都会输出到对应的sink文件：
- `question_bot_sink` - 问题生成日志
- `chief_bot_sink` - 主控制决策日志
- `searcher_bot_sink` - 搜索结果日志
- `answer_bot_sink` - 答案生成日志

## 🔗 相关资源

- [智能体框架文档](../../packages/sage-userspace/src/sage/lib/agents/)
- [工具系统文档](../../packages/sage-userspace/src/sage/lib/tools/)
- [上下文管理](../../packages/sage-userspace/src/sage/lib/context/)
