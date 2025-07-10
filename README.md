# <div align="center">🧠 SAGE: A Dataflow-Native Framework for LLM Reasoning<div>


SAGE is a dataflow-native reasoning framework built from the ground up to support modular, controllable, and transparent workflows over Large Language Models (LLMs). It addresses common problems in existing LLM-augmented systems (like RAG and Agents), such as hard-coded orchestration logic, opaque execution paths, and limited runtime control. SAGE introduces a dataflow-centric abstraction, modeling reasoning workflows as directed acyclic graphs (DAGs) composed of typed operators.

![](./asset/framework.png)

## ✨ Features

- 🧩 **Declarative & Modular Composition**: Build complex reasoning pipelines from typed, reusable operators. The dataflow graph cleanly separates what to compute from how to compute it.

- 🔀 **Unified Data and Control Flow**: Express conditional branching, tool routing, and fallback logic declaratively within the graph structure, eliminating brittle, imperative control code.

- 💾 **Native Stateful Operators**: Memory is a first-class citizen. Model session, task, and long-term memory as stateful nodes directly within the graph for persistent, context-aware computation.

- ⚡ **Asynchronous & Resilient Runtime**: The engine executes DAGs asynchronously in a non-blocking, data-driven manner. It features stream-aware queues, event-driven scheduling, and built-in backpressure to handle complex workloads gracefully.

- 📊 **Built-in Observability & Introspection**: An interactive dashboard provides runtime instrumentation out-of-the-box. Visually inspect execution graphs, monitor operator-level metrics, and debug pipeline behavior in real-time.

## 🔧 Installation

To accommodate different user environments and preferences, we provide **comprehensive setup scripts** that support multiple installation modes. Simply run the top-level `./setup.sh` script and choose from the following four installation options:

```bash
./setup.sh
```

You will be prompted to select one of the following modes:

1. **Minimal Setup**  
   Set up only the Conda environment.

<!-- 2. **Setup with Ray**  
   Includes the minimal setup and additionally installs [Ray](https://www.ray.io/), a distributed computing framework. -->

2. **Setup with Docker**  
   Launches a pre-configured Docker container and sets up the Conda environment inside it.

3. **Full Setup**  
   Launches the Docker container, installs all required dependencies (including **CANDY**, our in-house vector database), and sets up the Conda environment.

---

Alternatively, you can install the project manually:

1. Create a new Conda environment with Python ≥ 3.11:

   ```bash
   conda create -n sage python=3.11
   conda activate sage
   ```

2. Install the package from the root directory:

   ```bash
   pip install .
   ```

This method is recommended for advanced users who prefer manual dependency management or wish to integrate the project into existing workflows.




## 🚀 Quick Start
### 🧠 Memory Toolkit

Memory provides a lightweight in-memory vector database (VDB) supporting text embeddings, vector indexing, multi-index management, metadata filtering, persistence to disk, and recovery.

---

#### (1). Initialize Vector DB and Embedding Model

```python
mgr = MemoryManager()
embedder = MockTextEmbedder(fixed_dim=16)
col = mgr.create_collection(
    name="test_vdb",
    backend_type="VDB",
    description="test VDB",
    embedding_model=embedder,
    dim=16
)
````


#### (2). Insert Text Entries with Metadata

```python
col.add_metadata_field("tag")
col.insert("Alpha", {"tag": "A"})
col.insert("Beta", {"tag": "B"})
col.insert("Gamma", {"tag": "A"})
```


#### (3). Create Indexes (e.g., Filtered by Metadata)

```python
col.create_index("global_index")
col.create_index("tag_A_index", metadata_filter_func=lambda m: m.get("tag") == "A")
```

#### (4). Retrieve Similar Vectors

```python
res1 = col.retrieve("Alpha", topk=1, index_name="global_index")
res2 = col.retrieve("Alpha", topk=5, index_name="tag_A_index")
```

#### (5). Persist Collection to Local Disk

```python
mgr.store_collection()
print("Saved to:", mgr.data_dir)
```

#### (6). Reload Persisted Collection (Requires Embedding Model)

```python
mgr2 = MemoryManager()
embedder2 = MockTextEmbedder(fixed_dim=16)
col2 = mgr2.connect_collection("test_vdb", embedding_model=embedder2)
```

#### (7). Delete All Persisted Data (Optional)

```python
VDBMemoryCollection.clear("test_vdb", mgr.data_dir)
manager_json = os.path.join(mgr.data_dir, "manager.json")
if os.path.exists(manager_json):
    os.remove(manager_json)
```

### 🔧 Step-by-Step: Build a Local RAG Pipeline
SAGE uses a **fluent-style API** to declaratively define RAG pipelines. Here's how to get started:

---


```python
from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.rag.retriever import DenseRetriever
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.io.sink import TerminalSink
from sage_utils.config_loader import load_config

config = load_config("config.yaml")

# Build pipeline using Fluent API
env = LocalEnvironment()
env.set_memory(config=None)

query_stream = (pipeline
   .from_source(FileSource, config["source"])
   .map(DenseRetriever, config["retriever"])
   .map(QAPromptor, config["promptor"])
   .map(OpenAIGenerator, config["generator"])
   .sink(TerminalSink, config["sink"])
)

# Submit and run the pipeline
try:
   env.submit()
   env.run_once() 
   time.sleep(5) 
   env.stop()
finally:
   env.close()

```

#### 📘 About config

Each operator in the pipeline requires a configuration dictionary config that provides runtime parameters. You can find example config.yaml under [config](./config).

#### 📘 About Ray
To enable distributed execution using Ray, you can use RemoteEnvironment.
```python
env = RemoteEnvironment()
```
#### 📘 About Long Running
If your pipeline is meant to run as a long-lived service, use:
```python
env.run_streaming() 
```

See more examples under [sage_examples](sage_examples)

## 🧩 Components
### Operator
SAGE follows a Flink-style pipeline architecture where each `Operator` acts as a modular and composable processing unit. Operators can be chained together using a fluent API to form a streaming data pipeline. Internally, each `Operator` wraps a stateless or stateful `Function` that defines its core logic.

#### 🔧 Supported Operators
| Operator Method | Description                                                                                                    |
| --------------- | -------------------------------------------------------------------------------------------------------------- |
| `from_source()` | Adds a `SourceFunction` to read input data from external systems.                                              |
| `map()`         | Applies a stateless `Function` to each element of the stream, one-to-one transformation.                       |
| `flatmap()`    | Similar to `map()`, but allows one input to emit zero or more outputs (many-to-many).                          |
| `sink()`        | Defines the terminal output of the stream, consuming the final data (e.g., write to terminal, file, database). |

#### 🔧 Supported Fuction
| Fuction Type        | Description                                                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `SourceOperator`     | Entry point of the pipeline. Ingests input data from external sources such as files, APIs, or user queries.        |
| `RetrievalOperator`  | Performs dense or hybrid retrieval from a vector database or document store based on the input query.              |
| `RerankOperator`     | Reorders retrieved documents using a reranker model (e.g., cross-encoder) to improve relevance.                    |
| `RefineOperator`     | Compresses or filters retrieved context to reduce input length for faster and more accurate model inference.       |
| `PromptOperator`     | Builds model-ready prompts by formatting the query and context into a specific template or structure.              |
| `GenerationOperator` | Generates answers using a large language model (e.g., OpenAI, LLaMA, vLLM) based on the constructed prompt.        |
| `SinkOperator`       | Terminal point of the pipeline. Outputs final results to various sinks like terminal, files, databases, or APIs.   |
| `AgentOperator`      | Enables multi-step decision-making agents that call tools or external APIs based on reasoning strategies.          |
| `EvaluateOperator`   | Calculates metrics like F1, ROUGE, BLEU for model output evaluation. Often used in test/evaluation pipelines.      |
| `RoutingOperator`    | Implements conditional branching or fallback logic within the pipeline (e.g., skip generation if retrieval fails). |

### Memory
![](./asset/Memory_framework.png)

## Engine（执行引擎）

Sage Engine is the core execution component that orchestrates the compilation and execution of data flow pipelines. It uses a layered architecture to transform logical pipelines into physical execution graphs and efficiently execute them across different runtime environments, supporting both local multi-thread accleration or execution on distributed platrofms.

### How It Works

The Engine operates in four main phases:

1. **Pipeline Collection**: Gathers user-defined logical pipelines built through DataStream API and validates pipeline integrity
2. **Compilation & Optimization**: Uses Compiler to transform logical pipelines into optimized physical execution graphs with parallelism expansion
3. **Runtime Scheduling**: Selects appropriate Runtime (local/distributed) and converts execution graphs into concrete DAG nodes
4. **Execution Monitoring**: Monitors pipeline execution status, collects performance metrics, and handles fault recovery

### Key Features

- **Declarative Programming**: Users describe "what to do", Engine handles "how to do it"
- **Auto-Parallelization**: Automatically determines parallel execution strategies based on data dependencies
- **Platform Agnostic**: Same logical pipeline runs on both local and distributed environments
- **Performance Optimization**: Combines compile-time optimization with runtime tuning
- **Fault Tolerance**: Comprehensive error handling and recovery mechanisms (Under development)

## 🎨 SAGE-Dashboard
<p>With the <strong>SAGE-Dashboard</strong>, you can quickly orchestrate a large model application and run it with one click. Our meticulously designed visual interface will help you efficiently build, monitor, and manage complex workflows!</p>



### ✨: Features
- **DAG Visualization**
  - In the dashboard, the running DAG (Directed Acyclic Graph) is rendered in real-time, making your application workflow clear at a glance.</li>
  - Intuitively displays data flows and component dependencies, simplifying the process of understanding complex applications.</li>
- **Live Monitoring**
  - During execution, you can observe the resource usage of various components, including operators and memory, in real-time through the built-in dashboard.</li>
  - Operators are annotated with latency heatmaps, queue occupancy, and runtime statistics. Developers can observe the execution flow in real time, trace performance bottlenecks, and monitor memory behavior.</li>
- **Drag-and-Drop DAG Construction**
  - Quickly assemble a complete DAG workflow by simply arranging and connecting nodes on the canvas, with no need to write complex configuration files.</li>
  - Intuitively define your workflow by dragging and dropping from a rich library of built-in component nodes.</li>

<details>
<summary>Show more</summary>

 <!-- ![](./asset/UI.png) -->
 <img src="./asset/UI.png" alt="sage-dashboard" width="505"/>
</details>

#### Experience our meticulously designed Sage -Dashboard both user-friendly and powerful::
```bash
cd sage_frontend/sage_server
python main.py --host 127.0.0.1 --port 8080 --log-level debug

cd ../dashboard
npm i 
npm start
```

## 🔖 License
SAGE is licensed under the [MIT License](./LICENSE).
