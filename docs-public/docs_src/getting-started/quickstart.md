# 快速开始

> 5 分钟内运行你的第一个 SAGE Pipeline

## 前置要求

- Python 3.10+（推荐 3.11）
- conda 或 virtualenv (推荐)
- Git

## 1. 安装 SAGE

### 使用快速安装脚本（推荐）

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 切换到开发分支
git checkout main-dev

# 快速安装（包含依赖、submodules、hooks）
./quickstart.sh --dev --yes
```

### 手动安装

```bash
# 创建虚拟环境
conda create -n sage python=3.11
conda activate sage

# 安装 SAGE
pip install -e packages/sage-common
pip install -e packages/sage-platform
pip install -e packages/sage-kernel
pip install -e packages/sage-libs
pip install -e packages/sage-middleware
pip install -e packages/sage-studio
pip install -e packages/sage-tools
```

## 2. 验证安装

```bash
# 检查版本
sage --version

# 运行系统诊断
sage doctor
```

## 3. 配置运行环境

安装完成后，先完成 API Key 与本地 LLM 服务的配置，以便后续命令可以直接调用：

```bash
# 复制 .env.template → .env 并交互式补齐 OPENAI_API_KEY / HF_TOKEN 等变量
sage env setup

# 查看当前 .env / API Key 状态
sage env check
```

`.env.template` 会随着仓库更新自动包含最新的必填项；`sage env setup` 会在缺失时帮你生成 `.env`
并提示常用变量（`OPENAI_API_KEY`、`SILICONCLOUD_API_KEY`、`HF_TOKEN` 等）。

若需要将本地 vLLM / Ollama 服务写入 `config/config.yaml` 的 `generator.*` 配置段，可运行：

```bash
# 自动探测本地 LLM 服务并写入 config/config.yaml
sage llm-config auto --config-path config/config.yaml --prefer vllm --yes
```

命令会备份原文件（`config/config.yaml.bak`），再根据检测到的服务填充 `base_url`、`model_name` 等字段；若未指定 `--config-path`，会自动在
`config/`, `examples/config/`, `~/.sage/` 等位置寻找。

## 4. 第一个 Pipeline

创建文件 `hello_sage.py`:

```python
from sage.kernel.api import LocalEnvironment
from sage.libs.io import FileSource, TerminalSink
from sage.common.core.functions import MapFunction


# 创建简单的处理函数
class UpperCaseMap(MapFunction):
    def map(self, record):
        record.data = record.data.upper()
        return record


# 构建 Pipeline
env = LocalEnvironment("hello_sage")

(
    env.from_source(FileSource, {"file_path": "input.txt"})
    .map(UpperCaseMap)
    .sink(TerminalSink)
)

# 执行
env.submit()
```

创建测试数据 `input.txt`:

```
hello sage
streaming ai agent
```

运行：

```bash
python hello_sage.py
```

输出：

```
HELLO SAGE
STREAMING AI AGENT
```

## 5. 使用统一推理客户端

SAGE 提供 `UnifiedInferenceClient` 统一访问 LLM 和 Embedding 服务：

```python
from sage.llm import UnifiedInferenceClient

# 自动检测可用的 LLM 和 Embedding 服务
client = UnifiedInferenceClient.create_auto()

# 聊天补全
response = client.chat([
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": "什么是流式处理？"}
])
print(response)

# 文本生成
text = client.generate("从前有座山，山上有座庙，")
print(text)

# 文本嵌入
vectors = client.embed(["文本1", "文本2", "文本3"])
print(f"向量维度: {len(vectors[0])}")
```

**环境变量配置**（在 `.env` 文件中）:

```bash
# 本地 LLM 服务
SAGE_CHAT_BASE_URL=http://localhost:8001/v1

# 或使用云端 API
SAGE_CHAT_API_KEY=sk-your-api-key
SAGE_CHAT_BASE_URL=https://api.openai.com/v1
```

## 6. 构建 RAG Pipeline

```python
from sage.kernel.api import LocalEnvironment
from sage.libs.io import FileSource, TerminalSink
from sage.middleware.operators.rag import ChromaRetriever, QAPromptor, OpenAIGenerator

env = LocalEnvironment("rag_pipeline")

(
    env.from_source(FileSource, {"file_path": "questions.txt"})
    .map(ChromaRetriever, {"collection": "my_docs", "top_k": 3})
    .map(QAPromptor, {"template": "Context: {context}\n\nQ: {query}\nA:"})
    .map(OpenAIGenerator, {"model": "gpt-3.5-turbo", "api_key": "your-api-key"})
    .sink(TerminalSink)
)

env.submit()
```

## 7. 使用 Web UI

启动 SAGE Studio（可视化界面）：

```bash
sage studio start
```

访问 http://localhost:8000 即可使用图形界面构建 Pipeline。

## 8. 探索示例

SAGE 提供了按照 L1-L6 架构分层的教程与应用示例：

```bash
# 查看分层目录（L1-L6）
ls examples/tutorials/

# L3-libs: Agent 示例
python examples/tutorials/L3-libs/agents/basic_agent.py

# L3-libs: RAG 示例
python examples/tutorials/L3-libs/rag/simple_rag.py

# L5 应用入口（调用 sage-apps 实现）
python examples/apps/run_article_monitoring.py --help
```

## 📚 下一步

- [教程](../tutorials/) - 深入学习各个功能
- [架构文档](../concepts/architecture/overview.md) - 了解系统设计
- [API 参考](../api-reference/index.md) - 查看完整 API
- [开发指南](../developers/development-setup.md) - 参与贡献

## 🆘 获取帮助

- [GitHub Issues](https://github.com/intellistream/SAGE/issues)
- [社区讨论](https://github.com/intellistream/SAGE/discussions)

## ⚡ 快速参考

### 常用命令

```bash
# 启动服务
sage studio start
sage llm run --model Qwen/Qwen2.5-0.5B-Instruct

# 开发工具
sage-dev project test   # 运行测试
sage-dev quality fix    # 格式化代码
sage-dev quality check  # 代码检查

# Pipeline 构建
sage pipeline create    # 创建新 pipeline
sage pipeline list      # 列出所有 pipelines
```

### 常用导入

```python
# 核心 API
from sage.kernel.api import LocalEnvironment
from sage.libs.io import FileSource, TerminalSink

# Agents
from sage.libs.agentic.agents.bots import AnswerBot, QuestionBot

# RAG
from sage.middleware.operators.rag import ChromaRetriever, OpenAIGenerator

# 配置
from sage.common.config import load_config
```

开始构建你的 AI Agent 应用吧！ 🚀
