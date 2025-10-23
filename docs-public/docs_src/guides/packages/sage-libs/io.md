# SAGE I/O 核心组件 (Core I/O Components)

本文档详细介绍了 SAGE 数据处理流中的核心输入/输出 (I/O) 组件。这些组件分为两大类：

* **Source (数据源)**: 数据流的起点，负责从外部系统（如文件、消息队列等）读取数据并创建数据流。
* **Sink (数据汇聚)**: 数据流的终点，负责将处理完成的数据输出到外部系统（如终端、文件、数据库等）。

---

## 1. Source Functions (数据源)

数据源是启动数据处理流程的入口。

### 1.1 `FileSource`

`FileSource` 是一个从文本文件中逐行读取数据的数据源。它会持续监控文件，并在文件有新内容时读取新行。

* **核心功能**: 逐行读取指定文件内容，并将每一行作为字符串输出到数据流中。
* **输入**: 无 (直接从文件系统读取)。
* **输出**: `str` - 文件中的每一行内容。

#### 配置

在实例化 `FileSource` 时，需要在 `config` 字典中提供以下参数：

* `data_path` (必需): 要读取的源文件的路径。

#### 路径解析 (`resolve_data_path`)

`FileSource` 的路径处理逻辑如下：
* **如果 `data_path` 是绝对路径**: 直接使用该路径。
* **如果 `data_path` 是相对路径**: 将其解析为相对于当前项目根目录的路径。

#### 使用示例

假设你在一个 YAML 配置文件中定义一个数据处理流程：

```yaml
# pipeline.yaml
sources:
  - name: my_file_reader
    type: FileSource
    config:
      data_path: "data/input_questions.txt" # 相对于项目根目录的路径

# 假设 data/input_questions.txt 内容为:
# What is SAGE?
# How does it work?
```

`FileSource` 会依次读取 "What is SAGE?" 和 "How does it work?" 并将它们作为两个独立的数据项注入到数据流中。

---

## 2. Sink Functions (数据汇聚)

数据汇聚是数据流的终点，用于消费或存储最终结果。

### 2.1 `TerminalSink`

用于将标准的问答（Q&A）对输出到控制台终端，并使用不同颜色高亮问题和答案。

* **核心功能**: 在终端打印格式化的问答对。
* **输入**: `Tuple[str, str]` - 一个包含 (问题, 答案) 的元组。
* **配置**: 无需特殊配置。

#### 输出示例

```bash
# 控制台输出效果
[TerminalSink]: [Q] Question :What is SAGE?
[TerminalSink]: [A] Answer :SAGE is a Stream Analytics and Graph Engine.
```

### 2.2 `RetriveSink`

用于将一个问题和其关联的检索块（chunks）列表打印到控制台。

* **核心功能**: 在终端打印问题和检索到的相关文本块。
* **输入**: `Tuple[str, List[str]]` - 一个包含 (问题, 文本块列表) 的元组。
* **配置**: 无需特殊配置。

#### 输出示例

```bash
# 控制台输出效果
[Q] Question :How does it work?
[A] Chunks :['It processes data in streams.', 'It uses operators to transform data.']
```

### 2.3 `FileSink`

将问答（Q&A）对以追加模式写入到本地文件中，并自动添加分隔符。

* **核心功能**: 将问答对持久化到日志文件。
* **输入**: `Tuple[str, str]` - 一个包含 (问题, 答案) 的元组。
* **配置**:
    * `file_path`: (可选) 输出文件的路径。
        * **默认值**: `qa_output.txt`。
        * **路径处理**: 如果提供的是相对路径，文件将被自动创建在项目根目录下的 `output/` 文件夹中（例如 `output/my_log.txt`）。如果提供的是绝对路径，则直接使用。

#### 输出文件示例 (`output/qa_output.txt`)

```text
=== QA Output Log ===
[Q] Question: What is SAGE?
[A] Answer  : SAGE is a Stream Analytics and Graph Engine.
----------------------------------------
[Q] Question: How does it work?
[A] Answer  : It processes data in streams using operators.
----------------------------------------
```

### 2.4 `MemWriteSink`

一个通用的文件写入 Sink，可以接收多种格式的数据，并将它们作为带编号的字符串逐行写入文件。

* **核心功能**: 将流中的任意数据项作为字符串记录到文件中，并自动编号。
* **输入**: `Union[str, List[str], Tuple[str, str]]` - 支持字符串、字符串列表或元组。输入会被自动解析并展平为字符串列表。
* **配置**:
    * `file_path`: (可选) 输出文件的路径。
        * **默认值**: `mem_output.txt`。

#### 输出文件示例 (`mem_output.txt`)

```text
=== Memory String Log ===
[1] This is the first string.
[2] This is the second.
[3] From a tuple
[4] Another item from a tuple
----------------------------------------
[5] A single string item
----------------------------------------
```

### 2.5 `PrintSink`

一个功能强大的、智能的打印 Sink，主要用于调试。它能自动识别输入数据的结构并以友好的格式进行打印，是 `datastream.print()` 功能的底层实现。

* **核心功能**: 以可读性高的方式在终端打印任意数据，支持多种数据结构和彩色输出。
* **输入**: `Any` - 任意类型的数据。

#### 配置 (初始化参数)

| 参数 | 类型 | 描述 | 默认值 |
| :--- | :--- | :--- | :--- |
| `prefix` | `str` | 在每条输出前添加的前缀。 | `""` (空字符串) |
| `separator` | `str` | 用于分隔 `prefix` 和主要内容。 | ` " | " ` |
| `colored` | `bool` | 是否启用彩色输出。 | `True` |

#### 智能格式化逻辑

`PrintSink` 会自动检测输入 `data` 的类型并应用不同的格式：

* **问答对** (`Tuple[str, str]`): 格式化为 `[Q]... [A]...`。
* **检索结果** (`Tuple[str, List[str]]`): 格式化为 `[Q]... [Chunks]...`。
* **字符串列表** (`List[str]`): 格式化为一个带项目符号的列表。
* **字典** (`dict`): 格式化为 `key: value` 对的列表。
* **其他类型**: 直接转换为字符串 (`str(data)`)。

#### 使用示例

```python
# 在 SAGE 数据流代码中使用
from sage.data_stream import DataStream

# 假设 stream 的数据项是 (question, answer) 元组
stream: DataStream = ... 
stream.print(prefix="QA_RESULT") 

# 控制台可能输出:
# QA_RESULT | [Q] What is SAGE?
# [A] It's an engine.