# 🔧 SAGE Utils 重构方案

## 📋 当前 sage-utils 内容分析

基于对 `/packages/sage-utils/src/sage/utils/` 的分析，当前包含以下模块：

### 🔍 现有模块分类

#### 🏗️ 系统基础工具
- `system/` - 系统级工具
  - `environment_utils.py` - 环境变量和系统环境
  - `process_utils.py` - 进程管理
  - `network_utils.py` - 网络工具
- `config.py` / `config_loader.py` - 配置管理
- `logging.py` / `logger/` - 日志系统
- `state_persistence.py` - 状态持久化

#### 🔄 运行时通信工具
- `queue.py` / `queue_adapter.py` / `queue_config.py` - 队列系统
- `queue_auto_fallback.py` / `queue_diagnostic.py` / `queue_tool.py` - 队列扩展
- `actor_wrapper.py` - Actor 包装器
- `ray_helper.py` - Ray 分布式支持
- `network/` - 网络通信

#### 🔄 序列化工具
- `serialization/` - 序列化系统
  - `universal_serializer.py` - 通用序列化
  - `dill_serializer.py` - Dill 序列化
  - `ray_trimmer.py` - Ray 对象修剪
  - `preprocessor.py` - 预处理器
  - `config.py` / `exceptions.py` - 配置和异常

#### 🤖 AI/ML 客户端
- `clients/` - 外部服务客户端
  - `openaiclient.py` - OpenAI 客户端
  - `generator_model.py` - 生成模型
  - `hf.py` - HuggingFace 客户端
- `embedding_methods/` - 嵌入方法

## 🎯 重构策略：按架构层级重新分配

### 📦 新的包分配方案

#### 1. 🔧 sage-kernel-utils (内核层基础工具)
**目标**: 为内核层提供最基础的系统工具，无外部依赖
```
packages/sage-kernel-utils/
├── src/sage/kernel/utils/
│   ├── config/              # 从 utils/config.py 迁移
│   │   ├── __init__.py
│   │   ├── loader.py        # config_loader.py
│   │   └── manager.py       # config.py
│   ├── logging/             # 从 utils/logging.py + logger/ 迁移
│   │   ├── __init__.py
│   │   ├── basic.py         # 基础日志功能
│   │   └── formatters.py    # 日志格式化
│   ├── system/              # 从 utils/system/ 迁移
│   │   ├── __init__.py
│   │   ├── environment.py   # environment_utils.py
│   │   ├── process.py       # process_utils.py
│   │   └── network.py       # network_utils.py (基础部分)
│   └── serialization/       # 从 utils/serialization/ 迁移 (基础部分)
│       ├── __init__.py
│       ├── basic.py         # 基础序列化
│       └── exceptions.py
├── tests/
└── pyproject.toml
```

#### 2. 🔄 sage-kernel-runtime-extended (内核层运行时扩展)
**目标**: 提供队列、通信、分布式支持等运行时功能
```
packages/sage-kernel-runtime-extended/
├── src/sage/kernel/runtime/
│   ├── queue/               # 从 utils/queue_*.py 迁移
│   │   ├── __init__.py
│   │   ├── base.py          # queue.py
│   │   ├── adapter.py       # queue_adapter.py
│   │   ├── config.py        # queue_config.py
│   │   ├── fallback.py      # queue_auto_fallback.py
│   │   └── diagnostic.py    # queue_diagnostic.py, queue_tool.py
│   ├── communication/       # 从 utils/network/ + actor_wrapper.py 迁移
│   │   ├── __init__.py
│   │   ├── actor.py         # actor_wrapper.py
│   │   └── network.py       # utils/network/ (高级部分)
│   ├── distributed/         # 从 utils/ray_helper.py 迁移
│   │   ├── __init__.py
│   │   └── ray.py           # ray_helper.py
│   └── serialization/       # 从 utils/serialization/ 迁移 (高级部分)
│       ├── __init__.py
│       ├── universal.py     # universal_serializer.py
│       ├── dill.py          # dill_serializer.py
│       ├── ray_trimmer.py   # ray_trimmer.py
│       └── preprocessor.py  # preprocessor.py
├── tests/
└── pyproject.toml
```

#### 3. 🤖 sage-middleware-llm (中间件层LLM服务)
**目标**: 提供AI/ML模型的客户端和服务接口
```
packages/sage-middleware-llm/
├── src/sage/middleware/llm/
│   ├── clients/             # 从 utils/clients/ 迁移
│   │   ├── __init__.py
│   │   ├── openai.py        # openaiclient.py
│   │   ├── huggingface.py   # hf.py
│   │   └── base.py          # generator_model.py
│   ├── embedding/           # 从 utils/embedding_methods/ 迁移
│   │   ├── __init__.py
│   │   ├── methods.py
│   │   └── cache.py
│   └── persistence/         # 从 utils/state_persistence.py 迁移
│       ├── __init__.py
│       └── state.py         # state_persistence.py
├── tests/
└── pyproject.toml
```

### 🔄 迁移脚本设计

我来创建一个自动化迁移脚本：
