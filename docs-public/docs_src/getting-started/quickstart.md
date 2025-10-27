# 快速开始

> 5 分钟内运行你的第一个 SAGE Pipeline

## 前置要求

- Python 3.9+
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

## 3. 第一个 Pipeline

创建文件 `hello_sage.py`:

```python
from sage.kernel.api import LocalEnvironment
from sage.libs.io import FileSource, TerminalSink
from sage.kernel.api.function import MapFunction


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

## 4. 构建 RAG Pipeline

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

## 5. 使用 Web UI

启动 SAGE Studio（可视化界面）：

```bash
sage studio start
```

访问 http://localhost:8000 即可使用图形界面构建 Pipeline。

## 6. 探索示例

SAGE 提供了丰富的示例：

```bash
# 查看所有示例
ls examples/tutorials/

# 运行 Agent 示例
python examples/tutorials/agents/basic_agent.py

# 运行 RAG 示例
python examples/tutorials/rag/simple_rag.py
```

## 📚 下一步

- [教程](../tutorials/) - 深入学习各个功能
- [架构文档](../architecture/) - 了解系统设计
- [API 参考](../reference/) - 查看完整 API
- [开发指南](../developers/) - 参与贡献

## 🆘 获取帮助

- [常见问题](./faq.md)
- [GitHub Issues](https://github.com/intellistream/SAGE/issues)
- [社区讨论](https://github.com/intellistream/SAGE/discussions)

## ⚡ 快速参考

### 常用命令

```bash
# 启动服务
sage studio start
sage llm start

# 开发工具
sage-dev test           # 运行测试
sage-dev format         # 格式化代码
sage-dev check          # 代码检查

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
from sage.libs.agents.bots import AnswerBot, QuestionBot

# RAG
from sage.middleware.operators.rag import ChromaRetriever, OpenAIGenerator

# 配置
from sage.common.config import load_config
```

开始构建你的 AI Agent 应用吧！ 🚀
