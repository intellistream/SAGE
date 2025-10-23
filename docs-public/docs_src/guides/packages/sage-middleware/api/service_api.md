# Service API

一句话概述：统一的服务调用入口，支持同步与异步，在 Function 与 Service 中均可使用。服务通过 Environment 注册后，以名称暴露给调用侧；在 BaseFunction/BaseService 中通过 call_service/call_service_async 访问。

!!! tip "先决条件（Prerequisites）"
    - 了解 SAGE 的 Function/Operator 编程模型
    - 已在 Environment 中注册对应服务（如 memory_service、kv_service、vdb_service、graph_service 等）

---

## 一、快速开始

=== "Python"
    ```python title="在 Function 中调用服务（与仓库实现一致）" linenums="1"
    from sage.core.api.function.base_function import BaseFunction

    class MyFn(BaseFunction):
        def execute(self, data):
            # 同步调用 KV
            self.call_service["kv_service"].put("key1", data)

            # 异步调用 KV（future）
            fut = self.call_service_async["kv_service"].get("key1")
            value = fut.result(timeout=5)

            # 同步调用 Memory Service（Neuromem 提供的服务）
            self.call_service["memory_service"].store_memory(
                content=str(value),
                vector=data.get("vector"),
                session_id=data.get("session_id", "default"),
                memory_type="conversation",
                metadata={"source": "demo"}
            )
            return {"ok": True}
    ```

---

## 二、调用入口（速查）
```python
class BaseFunction:
    @property
    def call_service(self): ...
    @property
    def call_service_async(self): ...
    def execute(self, data): ...

class BaseService:
    @property
    def call_service(self): ...
    @property
    def call_service_async(self): ...
```

- 同步：self.call_service["service_name"].method(args...)
- 异步：self.call_service_async["service_name"].method(args...) -> Future（用 .result(timeout=…) 获取结果）
- 若运行时上下文未注入，访问上述属性会抛出 RuntimeError

---

## 三、服务清单（基于当前仓库，按模块划分）

说明：

- 下列服务名称为常用注册名；需与实际注册时的名称一致。
- 具体方法以仓库实现为准；示例仅展示仓库中出现的典型用法，避免虚构接口。
- 如需浏览完整代码，请参考仓库目录：packages/sage-middleware/src/sage/middleware/services

### 1) Memory Service（由 Neuromem 提供的长期记忆服务）

- 典型注册名：memory_service
- 组件关系：Memory Service = Neuromem 的服务化封装，对接底层 VDB/KV/Graph 等后端
- 模块位置（参考）：services/memory/
- 常见能力

    - 集合/空间管理（如创建集合）
    - 写入长期记忆（内容、向量、会话上下文与元数据）
    - 相似检索/语义检索（基于向量/过滤条件）

- 仓库中示例用法（节选）

  - 在环境中注册后使用：
    ```python
    # 参考仓库 README 用法
    def memory_service_factory():
        service = MemoryService()
        # 可选初始化集合（在 README 中出现过）
        service.create_collection(
            name="qa_collection",
            backend_type="VDB",
            description="QA pipeline memory"
        )
        return service

    env.register_service("memory_service", memory_service_factory)
    ```
  - 在 Function 中读写：
    ```python
    # 写入
    memory_id = self.call_service["memory_service"].store_memory(
        content=content,
        vector=vector,
        session_id=session_id,
        memory_type="conversation",
        metadata={"source": "user_input"}
    )

    # 检索（仓库示例中出现过 search_memories 用法）
    results = self.call_service["memory_service"].search_memories(
        query_vector=vector,
        session_id=session_id,
        limit=5  # 命名可能为 limit/top_k，按实际实现为准
    )
    ```

### 2) KV Service（键值存储服务）

- 典型注册名：kv_service
- 模块位置（参考）：services/kv/kv_service.py
- 常见能力

    - 键值写入与读取
    - 作为 Memory 编排中的元数据/缓存支撑

- 仓库中示例用法（节选）
  ```python
  # 同步写入
  self.call_service["kv_service"].put("key1", data)

  # 异步读取
  fut = self.call_service_async["kv_service"].get("key1")
  value = fut.result(timeout=5)
  ```

### 3) VDB Service（向量数据库服务）

- 典型注册名：vdb_service
- 模块位置（参考）：services/vdb/
- 常见能力

    - 向量集合管理
    - 向量写入/更新
    - 相似度检索、过滤检索

- 使用说明

    - 该服务通常由 Memory Service 间接使用；用户也可直接注册后在 Function 中调用
    - 具体方法名称请参考模块代码与 examples/services/vdb/examples/vdb_demo.py

### 4) Graph Service（图存储/关系索引服务）

- 典型注册名：graph_service
- 模块位置（参考）：services/graph/
- 常见能力

    - 节点/边的写入与查询
    - 关系/邻域检索，辅助长期记忆的上下文组织

- 使用说明

    - 该服务通常作为 Memory/Neuromem 的关系后端；具体接口以实现为准
    - 可参考 examples/services/graph/examples/graph_demo.py

---

## 四、服务注册与调用模式

- 注册服务（工厂函数返回服务实例）
  ```python
  def some_service_factory():
      # 返回具体服务实例
      return SomeService(...)

  env.register_service("some_service", some_service_factory)
  ```

- 在 Function 中调用
  ```python
  class MyFn(BaseFunction):
      def execute(self, data):
          out = self.call_service["some_service"].some_method(arg1, arg2)
          fut = self.call_service_async["some_service"].other_method(...)
          result = fut.result(timeout=5)
          return {"out": out, "async": result}
  ```

---

## 五、常见错误与排查

- 运行时上下文未注入：确保通过 Environment 构建 DAG 并以标准方式运行
- 服务未注册或名称不匹配：检查 env.register_service 的名称与调用侧一致
- 下游服务异常/超时：对异步调用使用合理的 timeout，并在调用侧捕获异常
- 数据契约不一致：遵循各服务示例中的字段约定，必要时在调用前做输入校验

---

## 参考

- 代码总览（服务目录）：https://github.com/ZeroJustMe/SAGE/tree/main/packages/sage-middleware/src/sage/middleware/services
- 示例导航（含 KV/VDB/Memory/Graph 示例）：packages/sage-middleware/src/sage/middleware/examples

注：以上清单基于当前可见的仓库结构与示例文件，可能未完全覆盖所有内部/实验性服务模块；请以服务目录与对应示例为准。