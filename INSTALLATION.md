# SAGE 安装指南

## 📦 快速安装

### 一键安装（推荐）

```bash
pip install intsage
```

SAGE 框架采用模块化设计，您可以根据需要安装不同的组件：

| 包名 | 说明 |
|------|------|
| `intsage` | 完整框架（推荐） |
| `intsage-kernel` | 核心引擎 |
| `intsage-middleware` | 中间件服务 |
| `intsage-userspace` | 用户空间（含丰富示例） |
| `intsage-dev-toolkit` | 开发工具集 |
| `intsage-frontend` | Web前端界面 |

**便捷导入**: 安装后直接使用 `import sage` 即可开始使用

## 🚀 快速安装

### 完整安装（推荐）

```bash
# 安装主包
pip install intsage
```

### 按需安装

```bash
# 只安装核心组件
pip install intsage-kernel

# 安装中间件（包含 LLM 功能）
pip install intsage-middleware

# 安装用户空间库（包含高级 API）
pip install intsage-userspace

# 安装开发工具
pip install intsage-dev-toolkit

# 安装 Web 前端
pip install intsage-frontend
```

### 开发环境安装

```bash
# 安装带开发依赖的完整环境
pip install intsage[dev]

# 或者从源码安装（推荐开发者使用）
git clone https://github.com/intellistream/SAGE.git
cd SAGE
pip install -e ".[dev]"
```

## � 探索示例

安装后可以直接使用内置示例：

```python
# 访问示例代码
from sage.examples.tutorials import hello_world
from sage.examples.rag import qa_simple
from sage.examples.streaming import kafka_query

# 示例包含：
# - sage.examples.tutorials.*  # 基础教程
# - sage.examples.rag.*        # RAG 应用示例  
# - sage.examples.agents.*     # 多智能体示例
# - sage.examples.streaming.*  # 流处理示例
# - sage.examples.memory.*     # 记忆管理示例
# - sage.examples.evaluation.* # 评估工具示例
```

## �📝 使用示例

安装后的 Python 导入保持不变：

```python
# 导入路径没有变化
import sage
from sage.kernels import DataStream
from sage.middleware import LLMService
from sage.userspace import RAGPipeline

# 使用示例
env = sage.LocalEnvironment()
stream = env.from_collection([1, 2, 3, 4, 5])
result = stream.map(lambda x: x * 2).collect()
print(result)  # [2, 4, 6, 8, 10]
```

## 🔄 版本管理

SAGE 框架定期更新，建议保持最新版本：

```bash
# 升级到最新版本
pip install --upgrade intsage

# 查看当前版本
python -c "import sage; print(sage.__version__)"
```

## 🆘 故障排除

### 依赖问题

```bash
# 强制重新安装
pip install --force-reinstall intsage

# 或者创建新的虚拟环境
python -m venv venv_sage
source venv_sage/bin/activate  # Linux/Mac
# venv_sage\Scripts\activate  # Windows
pip install intsage
```

## 📞 获取帮助

- 📖 [官方文档](https://intellistream.github.io/SAGE-Pub/)
- 🐛 [问题反馈](https://github.com/intellistream/SAGE/issues)
- 📧 [联系我们](mailto:intellistream@outlook.com)

---

**现在 SAGE 安装更简单了！** 🎉

