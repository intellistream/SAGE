# SAGE Applications Package

SAGE Applications 是基于 SAGE Framework 构建的应用示例和模板集合，提供了丰富的示例代码来帮助开发者快速上手和学习 SAGE 的各种功能。

## 📚 包含内容

### 🔰 教程示例 (tutorials)
- Hello World 入门示例
- Core API 使用教程
- 批处理和流处理对比

### 🧠 RAG 应用 (rag)  
- 简单 RAG 系统
- 稠密检索示例
- 稀疏检索 (BM25) 示例
- 混合检索策略
- 重排序和精化示例

### 🤖 智能体应用 (agents)
- 多智能体系统
- 工具调用示例
- 对话管理

### 🌊 流处理应用 (streaming)
- Kafka 集成示例
- 实时数据处理
- 多管道协同

### 💾 内存管理 (memory)
- 外部内存集成
- 知识库构建
- 持久化策略

### 📊 评估工具 (evaluation)
- QA 系统评估
- 性能基准测试
- 指标收集

## 🚀 快速开始

```python
from sage.apps.examples.rag import simple_rag
from sage.apps.examples.tutorials import hello_world

# 运行 Hello World 示例
hello_world.run()

# 运行简单 RAG 示例  
simple_rag.run()
```

## 📖 更多信息

详细的使用说明和示例代码请参考各个子目录中的 README 文件。
