# Tool Use Agent Pipeline

SAGE 框架的智能体工具调用 Pipeline，集成了 ReAct 推理、记忆服务和上下文压缩。

## 架构图

```
+-----------------------------------------------------------------------------------+
|                           Tool Use Agent Pipeline                                 |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-------------+   +--------------+   +--------------+   +-------------------+    |
|  | UserQuery   |-->| ToolSelector |-->| ToolExecutor |-->| ResponseGenerator |    |
|  |   Source    |   |              |   |              |   |                   |    |
|  +-------------+   +--------------+   +--------------+   +-------------------+    |
|        |                 |                  |                     |               |
|        v                 v                  v                     v               |
|  +-------------------------------------------------------------------------+      |
|  |                         LocalEnvironment                                |      |
|  |  +-------------------------------------------------------------------+  |      |
|  |  |              Registered Services (env.register_service)          |  |      |
|  |  |                                                                   |  |      |
|  |  |  +----------------+  +-----------------+  +------------------+   |  |      |
|  |  |  | memory_service |  | context_service |  |    vector_db     |   |  |      |
|  |  |  |   (sage-mem)   |  |  (sage-refiner) |  |    (sage-db)     |   |  |      |
|  |  |  |                |  |                 |  |                  |   |  |      |
|  |  |  | - retrieve()   |  | - manage_       |  | - search()       |   |  |      |
|  |  |  | - insert()     |  |   context()     |  | - add_batch()    |   |  |      |
|  |  |  | - delete()     |  | - add_to_       |  |                  |   |  |      |
|  |  |  |                |  |   history()     |  |                  |   |  |      |
|  |  |  +----------------+  +-----------------+  +------------------+   |  |      |
|  |  +-------------------------------------------------------------------+  |      |
|  +-------------------------------------------------------------------------+      |
|                                                                                   |
|  +-------------------------------------------------------------------------+      |
|  |                            Tool Registry                                |      |
|  |                                                                         |      |
|  |  +--------------+ +------------+ +------------+ +--------------+ +----+ |      |
|  |  |vector_search | | web_search | | calculator | |memory_search | |email |      |
|  |  | Uses:        | | Simulated  | | Safe eval  | | Uses:        | |search|      |
|  |  | vector_db    | |            | |            | | memory_svc   | |     | |      |
|  |  +--------------+ +------------+ +------------+ +--------------+ +----+ |      |
|  +-------------------------------------------------------------------------+      |
|                                                                                   |
|  +-------------------------------------------------------------------------+      |
|  |                    External Services (Remote LLM)                       |      |
|  |                                                                         |      |
|  |  UnifiedInferenceClient --> http://localhost:8901/v1 (Qwen2.5-7B)      |      |
|  |                         --> http://localhost:8090/v1 (BGE Embedding)   |      |
|  +-------------------------------------------------------------------------+      |
+-----------------------------------------------------------------------------------+
```

## ReAct 推理流程

```
+-----------------------------------------------------------------------------------+
|                              ReAct Reasoning Flow                                 |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   Query --> [Thought] --> [Action] --> [Observation] --> [Reflection] --> Response|
|              分析需求       选择工具      执行并观察         反思总结              |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## 数据流

```
        |
        v
+------------------+
|  UserQuerySource |  创建 AgentState，包含 query, session_id
+--------+---------+
         |
         v
+------------------+  1. 调用 memory_service.retrieve() 获取历史
|   ToolSelector   |  2. 调用 context_service.manage_context() 压缩上下文
| (ReAct Reasoning)|  3. LLM 推理选择工具 (或关键词 fallback)
|  Thought+Action  |  4. 记录 Thought 和 Action 到 AgentState
+--------+---------+
         |
         v
+------------------+  1. 注入 service_caller 到工具
|   ToolExecutor   |  2. 执行选中的工具
|  (Observation)   |  3. 工具通过 call_service() 访问服务
+--------+---------+  4. 记录 Observation 到 AgentState
         |
         v
+------------------+  1. 使用 LLM 生成最终回答
|ResponseGenerator |  2. 添加 Reflection 反思
|  (Reflection)    |  3. 调用 memory_service.insert() 保存交互
+--------+---------+  4. 调用 context_service.add_to_history()
         |
         v
+------------------+
|   ResponseSink   |  格式化输出 Response + ReAct Trace
+------------------+
```

## 服务调用关系

| Operator          | 调用服务                  | 方法             | 用途               |
| ----------------- | ------------------------- | ---------------- | ------------------ |
| ToolSelector      | memory_service            | retrieve()       | 获取相关历史记忆   |
| ToolSelector      | context_service           | manage_context() | 压缩长上下文       |
| ToolExecutor      | (通过工具) vector_db      | search()         | 向量相似度搜索     |
| ToolExecutor      | (通过工具) memory_service | retrieve()       | 搜索记忆           |
| ResponseGenerator | memory_service            | insert()         | 保存本次交互到记忆 |
| ResponseGenerator | context_service           | add_to_history() | 更新对话历史       |

## 运行方法

### 前'EOF'

```bash
# 设置远程 LLM 服务 (可选，不设置则使用 fallback 模式)
export SAGE_CHAT_BASE_URL="http://localhost:8901/v1"
export SAGE_CHAT_MODEL="Qwen/Qwen2.5-7B-Instruct"
export SAGE_EMBEDDING_BASE_URL="http://localhost:8090/v1"
export SAGE_EMBEDDING_MODEL="BAAI/bge-large-zh-v1.5"
```

### 方式 1: 默认 Demo 模式

```
            # Extract action
```

```bash
cd examples/tutorials/L3-libs/agents/tool_use_agent
python pipeline.py
```

### 方式 2: 自定义查询

```bash
# 单个查询
python pipeline.py --query "What is SAGE framework?"

# 多个查询
python pipeline.py --query "What is SAGE?" --query "Calculate 2+2" --query "Search memory docs"
```

```
            # Extract action (无服务)
```

```bash
python pipeline.py --no-services --query "Calculate 100 * 5"
```

### 方式 4: 静默模式

```bash
python pipeline.py --quiet --query "Hello"
```

### 方式 5: 交互模式

```bash
python pipeline.py --interactive
```

:

- 输入查询并按 Enter 执行
- `clear` - 清除记忆，开始新会话
- `quit` / `exit` / `q` - 退出

### 方式 6: Python API 调用

```python
import sys
sys.path.insert(0, 'examples/tutorials/L3-libs/agents/tool_use_agent')

from pipeline import run_tool_use_demo

# 运行 demo
run_tool_use_demo(
    queries=["What is SAGE?", "Calculate 1+2"],
    verbose=True,
    register_services=True,
)
```

### 方式 7: 测试模式

```bash
SAGE_TEST_MODE=true python pipeline.py
```

## 文件结构

```
tool_use_agent/
 __init__.py       # 包入口，导出 run_tool_use_demo, run_interactive_mode
 models.py         # 数据模型: AgentState, ReActStep, ToolCallRequest/Result
 agent_tools.py    # 工具定义: BaseTool, ToolRegistry, 5个内置工具
 operators.py      # Pipeline 算子: Source, Selector, Executor, Generator, Sink
 pipeline.py       # 主程序: , CLI, 入口函数
 README.md         # 本文档
```

## 可用工具

| 工具名        | 描述               | 服务依赖       |
| ------------- | ------------------ | -------------- |
| vector_search | 语义搜索 SAGE 知识 | vector_db      |
| web_search    | 网络搜索 (模拟)    | 无             |
| calculator    | 数学表达式计算     | 无             |
| memory_search | 搜索智能体记忆     | memory_service |
| email_search  | 邮件搜索 (模拟)    | 无             |

## 环境变量

| 变量                    | 描述                  | 默认值                   |
| ----------------------- | --------------------- | ------------------------ |
| SAGE_CHAT_BASE_URL      | LLM API 地址          | 无 (使用 fallback)       |
| SAGE_CHAT_MODEL         | LLM 模型名            | Qwen/Qwen2.5-7B-Instruct |
| SAGE_EMBEDDING_BASE_URL | Embedding API 地址    | 无                       |
| SAGE_EMBEDDING_MODEL    | Embedding 模型名      | BAAI/bge-large-zh-v1.5   |
| SAGE_TEST_MODE          | 测试模式 (限制查询数) | false                    |

## 常见'EOF'

### Q: 服务报错 "Service queue not available"

A: `--no-services` 参数，但工具尝试访问服务。请移除该参数或使用不依赖服务的工具

### Q: LLM 报错 "No LLM backend available"

A: 未配'EOF' LLM 环境变量，Pipeline 会自动使用 fallback 关键词匹配模式。

### Q: vector_db 报错 "could not convert string to float"

A: SageDBService 期望向量输入，Pipeline 会自动使用内置关键词搜索 fallback。

## 扩展开发

### 添加新工具

```python
# 在 agent_tools.py 中
class MyTool(BaseTool):
    name = "my_tool"
    description = "My custom tool description"
    input_schema = {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param"]
    }

    def call(self, arguments: dict) -> dict:
        # 访问服务
        result = self.call_service("my_service", method="my_method", **arguments)
        return {"success": True, "result": result}

# 注册到 create_default_registry()
def create_default_registry():
    registry = ToolRegistry()
    registry.register(MyTool())
    # ...
    return registry
```

### 添加新服务

```python
# 在 pipeline.py 中
def register_my_service(env: LocalEnvironment) -> bool:
    from sage.middleware.components.my_module import MyService

    env.register_service(
        "my_service",
        MyService,
        config={"key": "value"},
    )
    return True
```
