# SAGE - Streaming-Augmented Generative Execution

SAGE (Streaming-Augmented Generative Execution) 是一个强大的分布式流数据处理平台的 Meta 包。

## ⚠️ PEP 420 Namespace Package

**CRITICAL**: SAGE 使用 PEP 420 namespace packages 架构。

```python
# ❌ 错误：不能直接导入 sage 命名空间
import sage

# ✅ 正确：导入具体的子包
import sage.common
import sage.kernel
import sage.middleware
from sage.common.config import get_user_paths

# 注意: sage.llm 已移至独立仓库 isagellm
# pip install isagellm
```

**为什么不能直接 `import sage`?**

- SAGE 采用 PEP 420 原生命名空间（无 `__init__.py`）
- 允许多个独立 PyPI 包共享 `sage.*` 命名空间
- 防止"命名空间劫持"（首个安装包独占 `sage/`）
- 符合现代 Python 标准（Python 3.3+）

**相关**: #1388 多仓库拆分准备

## 简介

这是 SAGE 的主要元包，提供分层的安装选项以适应不同使用场景。

## 🧭 Governance / 团队协作制度

本包的团队安排、负责人制度、协作流程与质量门槛见：

- `docs/governance/TEAM.md`
- `docs/governance/MAINTAINERS.md`
- `docs/governance/DEVELOPER_GUIDE.md`
- `docs/governance/PR_CHECKLIST.md`
- `docs/governance/SELF_HOSTED_RUNNER.md`
- `docs/governance/TODO.md`

## 🎯 安装方式

### 标准安装（推荐）✅

日常应用开发，包含核心功能 + CLI + Web UI + RAG/LLM operators

```bash
pip install isage
```

**包含组件**：

- **L1-L4**: 核心运行时、算法库、领域算子
- **L5**: CLI 工具 (`sage` 命令) + 开发工具

**独立仓库** (不在 SAGE 核心架构中):

- sage-benchmark - 基准测试
- sage-examples - 应用示例
- sage-studio - Web UI
- sageLLM - LLM 推理引擎
- **科学计算库**: numpy, pandas, matplotlib, scipy, jupyter

**大小**: ~200MB | **适合**: 应用开发者、日常使用

______________________________________________________________________

### 其他安装选项

#### 核心运行时

仅用于运行已有 pipeline（生产环境、容器部署）

```bash
pip install isage[core]
```

**大小**: ~100MB | **适合**: 生产部署

#### 完整功能

包含示例应用（医疗、视频）和性能测试工具

```bash
pip install isage[full]
```

**大小**: ~300MB | **适合**: 学习示例、性能评估

#### 框架开发

修改 SAGE 框架源代码

```bash
pip install isage[dev]
```

**大小**: ~400MB | **适合**: 框架贡献者

## 📦 包含的组件

### 默认安装 (standard)

- **isage-common** (L1): 基础工具和公共模块
- **isage-platform** (L2): 平台服务（队列、存储）
- **isage-kernel** (L3): 核心运行时和任务执行引擎
- **isage-libs** (L3): 算法库和 Agent 框架
- **isage-middleware** (L4): RAG/LLM operators
- **isage-tools** (L5): CLI 工具 (`sage` 命令)
- **isage-cli** (L5): 生产 CLI 接口

### 额外组件 (独立仓库/PyPI 包)

- **isage-benchmark**: 性能基准测试工具 (独立仓库: sage-benchmark)
- **isagellm**: LLM 推理引擎 (独立仓库: sageLLM)
- **isage-edge**: 边缘聚合器 (独立仓库: sage-edge)

## 快速开始

### 安装

```bash
# 标准安装（推荐）
pip install isage

# 或从源码安装
git clone https://github.com/intellistream/SAGE.git
cd SAGE
pip install -e packages/sage
```

## 使用示例

```python
import sage

# 创建 SAGE 应用
app = sage.create_app()


# 定义数据流处理
@app.stream("user_events")
def process_events(event):
    return {
        "user_id": event["user_id"],
        "processed_at": sage.now(),
        "result": "processed",
    }


# 启动应用
if __name__ == "__main__":
    app.run()
```

## 命令行工具

安装后，你可以使用以下命令：

```bash
# 查看版本
sage --version

# 创建新项目
sage create my-project

# 启动服务
sage run

# 查看帮助
sage --help
```

## 文档

- [用户指南](https://intellistream.github.io/SAGE-Pub/)
- [API 文档](https://intellistream.github.io/SAGE-Pub/api/)
- [开发者指南](https://intellistream.github.io/SAGE-Pub/dev/)

## 许可证

MIT License

## 贡献

欢迎贡献代码！请查看我们的[贡献指南](CONTRIBUTING.md)。

## 支持

如果你遇到问题或有疑问，请：

1. 查看[文档](https://intellistream.github.io/SAGE-Pub/)
1. 搜索[已知问题](https://github.com/intellistream/SAGE/issues)
1. 创建[新问题](https://github.com/intellistream/SAGE/issues/new)
