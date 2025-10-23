# SAGE Studio - Source 和 Sink 配置指南

> 本文档说明如何在 SAGE Studio 中配置不同类型的数据源（Source）和数据接收器（Sink）。

## 📥 数据源（Source）配置

在 VisualNode 的 `config` 中设置 `source_type` 来指定数据源类型。

### 1. 内存数据源（Memory Source）

用于测试和开发，直接提供数据列表。

```json
{
  "source_type": "memory",
  "data": [
    {"input": "测试数据1"},
    {"input": "测试数据2"}
  ]
}
```

或者省略 `source_type`（默认为 memory）：

```json
{
  "data": [
    {"query": "什么是机器学习？"},
    {"query": "深度学习的应用"}
  ]
}
```

### 2. 文件源（File Source）

#### 通用文件源

```json
{
  "source_type": "file",
  "file_path": "/path/to/data.txt"
}
```

#### JSON 文件源

```json
{
  "source_type": "json_file",
  "file_path": "/path/to/data.json"
}
```

#### CSV 文件源

```json
{
  "source_type": "csv_file",
  "file_path": "/path/to/data.csv",
  "delimiter": ","
}
```

#### 文本文件源

```json
{
  "source_type": "text_file",
  "file_path": "/path/to/data.txt"
}
```

### 3. 网络源（Network Source）

#### Socket 源

```json
{
  "source_type": "socket",
  "host": "localhost",
  "port": 9999
}
```

#### Kafka 源

```json
{
  "source_type": "kafka",
  "topic": "input-topic",
  "bootstrap_servers": "localhost:9092"
}
```

### 4. 数据库源（Database Source）

```json
{
  "source_type": "database",
  "query": "SELECT * FROM users WHERE active = true",
  "connection_string": "postgresql://user:pass@localhost/dbname"
}
```

### 5. API 源（API Source）

```json
{
  "source_type": "api",
  "url": "https://api.example.com/data",
  "method": "GET"
}
```

## 📤 数据接收器（Sink）配置

在 VisualPipeline 层级设置 `sink_type`（将来可能在 UI 中配置）。

### 1. 打印接收器（Print Sink）

简单打印到标准输出（默认）。

```python
pipeline.sink_type = "print"
```

### 2. 终端接收器（Terminal Sink）

带颜色的终端输出，更美观。

```python
pipeline.sink_type = "terminal"
```

### 3. 文件接收器（File Sink）

输出到文件。

```python
pipeline.sink_type = "file"
# 注意：需要在配置中指定文件路径
```

### 4. 内存接收器（Memory Sink）

用于测试，将结果存储在内存中。

```python
pipeline.sink_type = "memory"
```

### 5. 收集接收器（Retrieve Sink）

收集所有结果并返回。

```python
pipeline.sink_type = "retrieve"
```

## 🔧 在代码中使用

### Python API 示例

```python
from sage.studio.models import VisualNode, VisualConnection, VisualPipeline
from sage.studio.services import PipelineBuilder

# 创建带文件源的节点
source_node = VisualNode(
    id="source",
    type="map",
    label="File Source",
    config={
        "source_type": "json_file",
        "file_path": "/data/input.json"
    },
    position={"x": 0, "y": 0}
)

# 创建处理节点
processor_node = VisualNode(
    id="processor",
    type="retriever",
    label="Retriever",
    config={
        "top_k": 5,
        "index_name": "my_index"
    },
    position={"x": 200, "y": 0}
)

# 创建连接
connection = VisualConnection(
    id="c1",
    source_node_id="source",
    source_port="output",
    target_node_id="processor",
    target_port="input"
)

# 创建 Pipeline
pipeline = VisualPipeline(
    id="my_pipeline",
    name="File Processing Pipeline",
    nodes=[source_node, processor_node],
    connections=[connection]
)

# 设置 sink 类型（可选，默认为 print）
pipeline.sink_type = "terminal"

# 构建并执行
builder = PipelineBuilder()
env = builder.build(pipeline)
result = env.execute()
```

### REST API 示例

```json
{
  "id": "pipeline1",
  "name": "My Pipeline",
  "nodes": [
    {
      "id": "source1",
      "type": "map",
      "label": "Kafka Source",
      "config": {
        "source_type": "kafka",
        "topic": "input-events",
        "bootstrap_servers": "kafka:9092"
      },
      "position": {"x": 0, "y": 0}
    },
    {
      "id": "processor1",
      "type": "generator",
      "label": "LLM Generator",
      "config": {
        "model": "gpt-3.5-turbo"
      },
      "position": {"x": 200, "y": 0}
    }
  ],
  "connections": [
    {
      "id": "conn1",
      "source_node_id": "source1",
      "source_port": "output",
      "target_node_id": "processor1",
      "target_port": "input"
    }
  ],
  "sink_type": "terminal"
}
```

## 📝 注意事项

1. **Source 配置位置**: Source 的配置在**第一个节点**的 `config` 中
2. **Sink 配置位置**: Sink 的配置在 **Pipeline** 层级（`pipeline.sink_type`）
3. **默认值**:
   - 默认 Source: 内存数据源（`memory`）
   - 默认 Sink: 打印接收器（`print`）
4. **路径**: 文件路径支持相对路径和绝对路径
5. **验证**: 配置错误会在 Pipeline 构建时抛出异常

## 🔗 参考

- **完整 Source 列表**: `sage.libs.io.source`
- **完整 Sink 列表**: `sage.libs.io.sink`
- **SAGE 包架构**: `/docs-public/docs_src/dev-notes/package-architecture.md`
- **Pipeline Builder**: `sage.studio.services.pipeline_builder`

## 🚀 扩展

如果需要添加新的 Source 或 Sink 类型：

1. 在 `sage.libs.io.source` 或 `sage.libs.io.sink` 中实现新类
2. 在 `PipelineBuilder._create_source()` 或 `_create_sink()` 中添加对应的 case
3. 更新本文档

示例：添加新的 Redis Source

```python
# 在 PipelineBuilder._create_source() 中添加
elif source_type == "redis":
    from sage.libs.io.source import RedisSource
    host = node.config.get("host", "localhost")
    port = node.config.get("port", 6379)
    key = node.config.get("key")
    return RedisSource, (host, port, key), {}
```
