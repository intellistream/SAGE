# SAGE 智能代理模块

智能代理模块提供多种专门化的AI代理，用于执行特定的智能任务和决策。

## 模块概述

智能代理模块实现了多种AI代理，每个代理都有特定的功能和职责，可以协同工作完成复杂的智能任务。

## 核心代理

### `agent.py`
基础代理框架：
- 定义代理的基础抽象类
- 提供通用的代理行为接口
- 支持代理间的通信和协调
- 包含状态管理和生命周期控制

### `answer_bot.py`
回答代理：
- 专门负责回答用户问题
- 基于知识库和上下文生成答案
- 支持多轮对话和上下文理解
- 提供答案质量评估和优化

### `question_bot.py`
提问代理：
- 智能生成相关问题
- 用于引导对话和深入探索
- 支持问题分类和优先级排序
- 提供问题质量评估

### `searcher_bot.py`
搜索代理：
- 执行智能信息搜索
- 从多个数据源检索相关信息
- 支持语义搜索和关键词搜索
- 提供搜索结果排序和过滤

### `chief_bot.py`
主管代理：
- 协调和管理其他代理
- 制定任务分配和执行计划
- 监控代理执行状态
- 处理代理间的冲突和协调

### `critic_bot.py`
评判代理：
- 评估其他代理的输出质量
- 提供改进建议和反馈
- 执行质量控制和优化
- 支持多维度评估标准

## 主要特性

- **专业分工**: 每个代理专注于特定领域
- **协同工作**: 代理间可以协调配合
- **智能决策**: 基于AI的智能决策能力
- **可扩展性**: 支持自定义代理开发
- **状态管理**: 完善的代理状态跟踪

## 代理协作模式

### 串行协作
代理按顺序执行任务：
```
Question Bot → Searcher Bot → Answer Bot → Critic Bot
```

### 并行协作
多个代理同时执行不同任务：
```
┌── Searcher Bot ──┐
│                  ├── Chief Bot → Answer Bot
└── Question Bot ──┘
```

### 层次协作
Chief Bot统一管理其他代理：
```
        Chief Bot
       /    |    \
Question  Searcher  Answer
  Bot       Bot      Bot
   |         |        |
Critic    Critic   Critic
  Bot       Bot      Bot
```

## 使用场景

- **智能问答系统**: 多代理协作的问答服务
- **知识发现**: 通过多角度探索发现知识
- **内容生成**: 协作生成高质量内容
- **决策支持**: 多维度分析和决策建议
- **教育辅导**: 智能教学和学习指导

## 快速开始

```python
from sage.lib.agents import AnswerBot, QuestionBot, SearcherBot

# 创建代理实例
answer_bot = AnswerBot(model="gpt-4")
question_bot = QuestionBot(model="gpt-4")
searcher_bot = SearcherBot(knowledge_base="my_kb")

# 使用代理
user_query = "什么是机器学习？"

# 搜索相关信息
search_results = searcher_bot.search(user_query)

# 生成回答
answer = answer_bot.answer(user_query, context=search_results)

# 生成后续问题
follow_up = question_bot.generate_questions(user_query, answer)
```

## 协作工作流

```python
from sage.lib.agents import ChiefBot

# 创建主管代理
chief = ChiefBot()

# 注册子代理
chief.register_agent("searcher", SearcherBot())
chief.register_agent("answerer", AnswerBot())
chief.register_agent("critic", CriticBot())

# 执行复杂任务
result = chief.execute_task({
    "type": "complex_qa",
    "query": "解释量子计算的原理",
    "requirements": ["accurate", "comprehensive", "easy_to_understand"]
})
```

## 配置和定制

### 代理配置
```python
agent_config = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000,
    "timeout": 30,
    "retry_count": 3
}

bot = AnswerBot(config=agent_config)
```

### 自定义代理
```python
from sage.lib.agents.agent import BaseAgent

class CustomBot(BaseAgent):
    def __init__(self, config=None):
        super().__init__(config)
    
    def process(self, input_data):
        # 自定义处理逻辑
        return processed_result
```

## 性能监控

- 代理响应时间监控
- 任务成功率统计
- 资源使用情况跟踪
- 协作效率分析
