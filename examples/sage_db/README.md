# SageDB × SAGE Workflow DAG Demo

这个目录展示了如何把 SageDB 检索能力嵌入到 SAGE 的本地推理 DAG 中：通过 `LocalEnvironment` 串联数据源、检索节点、Prompt 构建以及大模型生成（这里使用一个本地的 Mock 生成器）。

## 目录

| 文件 | 说明 |
|------|------|
| `workflow_dag_demo.py` | 主示例脚本：注册 SageDB 服务、构建 LocalEnvironment 流水线，并运行查询→检索→提示→生成的 DAG。|

## 运行准备

1. **编译 SageDB Python 扩展**（首次运行时必需）：

   ```bash
   cd packages/sage-middleware/src/sage/middleware/components/sage_db
   ./build.sh
   ```

2. （可选）如果你要运行其他官方示例或使用真实的大模型接口，请确保相关环境变量/API Key 就绪。

## 快速体验

在仓库根目录执行：

```bash
python examples/sage_db/workflow_dag_demo.py
```

运行过程会：

1. 使用 Mock 嵌入模型把文档向量化，并通过自定义 `BootstrappedSageDBService` 写入 SageDB。
2. 构建一个基于 `LocalEnvironment` 的 DAG：`QuerySource → SageDBRetrieverNode → QAPromptor → MockLLMGenerator → ConsoleReporter`。
3. 依次处理两个默认问题，打印检索结果与生成回答。

### 自定义参数

- 指定检索邻居数量：

  ```bash
  python examples/sage_db/workflow_dag_demo.py --top-k 5
  ```

- 自定义查询（可多次传入）：

  ```bash
  python examples/sage_db/workflow_dag_demo.py \
    --query "SageDB 如何融入 SAGE 的服务体系?" \
    --query "Prompt 阶段要注意什么?"
  ```

## 与真实大模型对接

当前示例的 `MockLLMGenerator` 会根据检索命中的文本拼一个回答，便于快速演示数据流。如果需要串接真实的大模型推理：

1. 将 `MockLLMGenerator` 替换为 `sage.libs.rag.generator.OpenAIGenerator` 或其他 `MapFunction` 生成节点。
2. 在 `.map(QAPromptor, ...)` 后追加真实生成器，例如：

   ```python
   .map(OpenAIGenerator, {
       "model_name": "gpt-4o-mini",
       "base_url": "http://localhost:8000/v1",
       "api_key": os.getenv("OPENAI_API_KEY"),
   })
   ```
3. 再添加一个终端输出节点（可以复用 `ConsoleReporter`）。

## 下一步拓展

- 将文档知识库改为动态加载：可结合 `JSONLBatch`、`MapFunction` 管线在启动前写入 SageDB。
- 利用 `self.call_service_async` 改造检索为异步模式。
- 把生成步骤换成真实的 VLLM/OpenAI 网关，或引入多轮对话的反馈边（`env.from_future`）。

欢迎在此基础上拓展更复杂的 DAG 流程，或将脚本嵌入到你现有的服务启动逻辑中。🙂

## 已知问题（2025-10-01）

- **服务初始化失败并伴随检索调用超时**：当前示例在向 `BootstrappedSageDBService` 写入初始语料时，会把 `tags` 字段作为 `list[str]` 传给 `_sage_db.add_numpy`。C++ 扩展仅支持 `str -> str` 的字典，因此会报错 `Unable to cast Python instance of type <class 'dict'> to C++ type 'std::map<...>'`。服务未能成功注册，导致后续对 `vector_store_service.search` 的调用持续超时。
  - **复现方式**：运行 `python examples/sage_db/workflow_dag_demo.py --top-k 2`。
  - **临时规避**：将 `prepare_metadata` 中的 `tags` 等非字符串字段转为字符串（例如 `",".join(tags)` 或 `json.dumps(metadata)`）。
  - **后续计划**：在服务写入前统一序列化元数据，或为 `_sage_db` 扩展增加对列表类型的支持。

> 上述问题将在后续修复，当前提交先记录现象以便追踪。
