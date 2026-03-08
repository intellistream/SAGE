# SAGE Zoo — 独立可选包

这些包原本是 SAGE 核心仓库的一部分，已拆分为**独立仓库**，拥有独立的版本号、CI 流水线和 PyPI 发布节奏。

- 它们**不随** `pip install isage` 默认安装
- 每个包均可单独安装、单独升级、单独贡献
- 若某个包足够成熟、被广泛使用，可再次纳入 SAGE 核心依赖

______________________________________________________________________

## 快速安装

```bash
# 算法与 AI 能力
pip install isage-agentic          # Agent 框架（ReAct / 规划 / 工作流）
pip install isage-rag              # RAG 管道
pip install isage-finetune         # LLM 微调
pip install isage-agentic-tooluse  # Agent 工具选择
pip install isage-intent           # 意图识别
pip install isage-refiner          # 上下文压缩与精炼
pip install isage-amms             # 近似矩阵乘法（C++/CUDA）
pip install isage-privacy          # 差分隐私 / 机器遗忘
pip install isage-safety           # 安全过滤 / 护栏

# 基础设施与引擎
pip install isage-flownet          # Python 原生动态数据流执行引擎（类 Ray 角色模型）
pip install isage-vdb              # 向量数据库（FAISS 兼容 API，C++）
pip install isage-neuromem         # RAG 记忆管理引擎

# 评估与数据
pip install isage-eval             # 评估框架（指标 / LLM 评判）
pip install isage-benchmark        # 综合评测套件
pip install isage-data             # 统一数据集管理

# 应用与工具
pip install isage-vida             # 24/7 持久化自主 Agent（三层记忆 + 周期反思 + 多源触发）
pip install isage-tools            # Agent 可调用数据获取工具集（搜索 / 爬取 / OCR）+ MCP Server
pip install isage-studio           # 可视化工作流构建器
pip install isage-edge             # 边缘推理服务器
pip install isage-examples         # 教程与示例代码

# MCP Server（将 SAGE 能力暴露给 AI 客户端）
pip install 'isage-tools[mcp]' && isage-tools-mcp  # 搜索 + 爬取工具 MCP 服务
```

______________________________________________________________________

## 包一览

### 算法与 AI 能力

| 包名                    | 仓库                                                                          | 一句话功能                                            | 安装命令                            |
| ----------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------- |
| `isage-agentic`         | [sage-agentic](https://github.com/intellistream/sage-agentic)                 | ReAct、PlanExecute Agent 框架，支持工具调用与多步规划 | `pip install isage-agentic`         |
| `isage-rag`             | [sage-rag](https://github.com/intellistream/sage-rag)                         | 文档加载 → 分块 → 向量检索 → 重排序的完整 RAG 管道    | `pip install isage-rag`             |
| `isage-finetune`        | [sage-finetune](https://github.com/intellistream/sage-finetune)               | LoRA / QLoRA 微调、数据加载器与训练流程               | `pip install isage-finetune`        |
| `isage-agentic-tooluse` | [sage-agentic-tooluse](https://github.com/intellistream/sage-agentic-tooluse) | Hybrid / DFS / Gorilla 工具选择与调用算法             | `pip install isage-agentic-tooluse` |
| `isage-intent`          | [sage-libs-intent](https://github.com/intellistream/sage-libs-intent)         | 关键词 + LLM 双路意图识别与路由                       | `pip install isage-intent`          |
| `isage-refiner`         | [sageRefiner](https://github.com/intellistream/sageRefiner)                   | LLM / RAG 上下文压缩、重计算提取与精炼算法            | `pip install isage-refiner`         |
| `isage-amms`            | [sage-amms](https://github.com/intellistream/sage-amms)                       | 近似矩阵乘法（C++/CUDA），统一接口对标 FAISS 风格     | `pip install isage-amms`            |
| `isage-privacy`         | [sage-privacy](https://github.com/intellistream/sage-privacy)                 | 差分隐私（Laplace / Gaussian）与机器遗忘算法          | `pip install isage-privacy`         |
| `isage-safety`          | [sage-safety](https://github.com/intellistream/sage-safety)                   | 毒性检测、关键词护栏、越狱防御等安全过滤组件          | `pip install isage-safety`          |

### 基础设施与引擎

| 包名             | 仓库                                                        | 一句话功能                                                                     | 安装命令                     |
| ---------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------- |
| `isage-flownet`  | [sageFlownet](https://github.com/intellistream/sageFlownet) | Python 原生动态数据流执行引擎，角色模型分布式调度（类 Ray，SAGE 可选 Runtime） | `pip install isage-flownet`  |
| `isage-vdb`      | [sageVDB](https://github.com/intellistream/sageVDB)         | 高性能向量数据库，FAISS 兼容 API，支持 IVF / HNSW（C++）                       | `pip install isage-vdb`      |
| `isage-neuromem` | [neuromem](https://github.com/intellistream/neuromem)       | RAG 持久化记忆管理引擎，支持 VDB / KV / 图后端                                 | `pip install isage-neuromem` |
| `isage-edge`     | [sage-edge](https://github.com/intellistream/sage-edge)     | 面向边缘设备的轻量推理服务器                                                   | `pip install isage-edge`     |

### 评估与数据

| 包名              | 仓库                                                              | 一句话功能                                                     | 安装命令                      |
| ----------------- | ----------------------------------------------------------------- | -------------------------------------------------------------- | ----------------------------- |
| `isage-eval`      | [sage-eval](https://github.com/intellistream/sage-eval)           | 任务指标、吞吐/延迟分析、LLM-as-Judge 评估框架                 | `pip install isage-eval`      |
| `isage-benchmark` | [sage-benchmark](https://github.com/intellistream/sage-benchmark) | 覆盖 RAG、Agent、记忆、控制面的综合评测套件                    | `pip install isage-benchmark` |
| `isage-data`      | [sageData](https://github.com/intellistream/sageData)             | 统一数据集管理（BBH / MMLU / GPQA 等），两层 Source/Usage 架构 | `pip install isage-data`      |

### 应用与工具

| 包名             | 仓库                                                            | 一句话功能                                                                                     | 安装命令                         |
| ---------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------- |
| `isage-vida`     | [sage-vida](https://github.com/intellistream/sage-vida)         | 24/7 持久化自主 Agent，三层记忆 + 周期反思 + 多源触发                                          | `pip install isage-vida`         |
| `isage-tools`    | [sage-tools](https://github.com/intellistream/sage-tools)       | Agent 可调用数据获取工具（DuckDuckGo / arXiv / URL 提取 / Nature 新闻 / OCR）+ 内置 MCP Server | `pip install 'isage-tools[mcp]'` |
| `isage-studio`   | [sage-studio](https://github.com/intellistream/sage-studio)     | React + FastAPI 可视化工作流构建器与 LLM Playground                                            | `pip install isage-studio`       |
| `isage-examples` | [sage-examples](https://github.com/intellistream/sage-examples) | 端到端示例应用与场景脚本                                                                       | `pip install isage-examples`     |

______________________________________________________________________

## MCP Server 支持

SAGE Zoo 包可以作为 **[Model Context Protocol (MCP)](https://modelcontextprotocol.io) 服务器**对外发布，让 Claude Desktop、VS Code Copilot、Cursor 等任意 MCP 客户端直接调用 SAGE 的能力，**无需编写集成代码**。

### 已支持 MCP 的包

| 包名          | MCP 工具                                                                                           | 启动命令          |
| ------------- | -------------------------------------------------------------------------------------------------- | ----------------- |
| `isage-tools` | `duckduckgo_search`, `arxiv_search`, `arxiv_paper_search`, `url_text_extract`, `nature_news_fetch` | `isage-tools-mcp` |

### 快速体验（Claude Desktop）

```bash
pip install 'isage-tools[mcp]'
```

在 Claude Desktop 配置文件中添加：

```json
{
  "mcpServers": {
    "sage-tools": {
      "command": "python",
      "args": ["-m", "sage.tools.mcp_server"]
    }
  }
}
```

或免安装方式（via uvx）：

```json
{
  "mcpServers": {
    "sage-tools": {
      "command": "uvx",
      "args": ["isage-tools"]
    }
  }
}
```

### VS Code / HTTP / SSE 模式

```bash
# 启动 HTTP/SSE 服务器
isage-tools-mcp --transport sse --port 8765
```

在 `.vscode/mcp.json` 中添加：

```json
{
  "mcp": {
    "servers": {
      "sage-tools": { "type": "sse", "url": "http://localhost:8765/sse" }
    }
  }
}
```

### 其他 Zoo 包的 MCP 扩展规划

每个 Zoo 包均按相同模式扩展：

- 安装对应的 `[mcp]` extra
- 运行 `i<package>-mcp` 命令
- 配置到任意 MCP 客户端

| 包名            | 规划中的 MCP 工具                | 状态      |
| --------------- | -------------------------------- | --------- |
| `isage-tools`   | search, arxiv, url_extract, news | ✅ 已实现 |
| `isage-rag`     | rag_search, index_document       | 🔜 规划中 |
| `isage-agentic` | run_agent, run_react_loop        | 🔜 规划中 |
| `isage-eval`    | evaluate_response, llm_judge     | 🔜 规划中 |
