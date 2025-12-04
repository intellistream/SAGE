# L1: Common - 基础层示例

> 对应 SAGE 包：`sage-common`

## 📖 层级说明

**Common** 层是 SAGE 的基础设施层，提供所有其他层依赖的核心功能：

- 配置管理系统
- 日志系统
- 类型定义
- 工具函数
- **统一推理客户端** (UnifiedInferenceClient)

## 📚 包含示例

### 基础入门

- `hello_world.py` - 最简单的 SAGE 程序

### 统一推理客户端

- `unified_inference_client_example.py` - **推荐** 使用 UnifiedInferenceClient 进行 LLM 对话和 Embedding

### Embedding 服务

- `embedding_server_example.py` - 本地 Embedding 服务器使用示例

### 配置系统

- `config_demo.py` - 配置文件加载和管理

### 日志系统

- `logging_demo.py` - 日志配置和使用

## 🎯 学习目标

完成本层示例后，你将掌握：

1. SAGE 的基本概念和术语
2. 如何使用 **UnifiedInferenceClient** 进行 LLM 对话和 Embedding
3. 如何使用配置系统
4. 如何使用日志系统
5. 为后续学习 Kernel 层做好准备

## 🚀 快速开始 (UnifiedInferenceClient)

### 1. 启动服务

```bash
# 启动 Gateway（包含 Control Plane）
sage gateway start

# 启动 LLM 引擎
sage llm engine start Qwen/Qwen2.5-0.5B-Instruct

# (可选) 启动 Embedding 引擎
sage llm engine start BAAI/bge-m3 --engine-kind embedding
```

### 2. 运行示例

```bash
python examples/tutorials/L1-common/unified_inference_client_example.py
```

### 3. 或直接使用 Python

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 连接到 Gateway Control Plane
client = UnifiedInferenceClient.create(
    control_plane_url="http://localhost:8000/v1"
)

# 对话
response = client.chat([{"role": "user", "content": "Hello"}])
print(response)

# Embedding
vectors = client.embed(["text1", "text2"])
print(f"向量维度: {len(vectors[0])}")
```

## ⏭️ 下一步

学完基础层后，继续学习：

- **L2-platform/** - 平台服务
- **L3-kernel/** - 核心 API 和流处理引擎
