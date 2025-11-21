# DyFlow: Dynamic Workflow Framework

DyFlow 是一个动态工作流框架，用于代理推理任务。采用 Designer-Executor 双层架构，能够根据执行反馈动态调整工作流。

## 🎯 核心特性

- **动态工作流**: 根据中间反馈自适应调整推理流程
- **双核心组件**:
  - **Designer**: 高层任务分解和规划
  - **Executor**: 底层执行和工具调用
- **跨域评估**: 支持多种任务类型和领域

## 📦 安装

```bash
cd /home/gyy/SAGE/packages/sage-libs/src/sage/libs/workflow_generation/DyFlow
pip install -r requirements.txt
```

## 🚀 快速开始

### 基本使用

```python
from sage.libs.workflow_generation.DyFlow.dyflow import ModelService, WorkflowExecutor

# 创建模型服务
designer = ModelService(model='local', temperature=0.1)
executor = ModelService(model='local', temperature=0.01)

# 创建工作流执行器
workflow = WorkflowExecutor(
    problem_description="你的任务描述",
    designer_service=designer,
    executor_service=executor
)

# 执行工作流
result = workflow.execute()
print(result)
```

### 使用本地模型

```python
import os

# 设置本地 LLM 端点
os.environ["LOCAL_LLM_BASE_URL"] = "http://localhost:8000/v1/"

# 创建服务
designer = ModelService(model='local', temperature=0.1)
executor = ModelService(model='local', temperature=0.01)
```

## 📁 项目结构

```
DyFlow/
├── dyflow/                      # 核心代码
│   ├── core/                    # 核心组件
│   │   ├── workflow.py          # 工作流执行
│   │   ├── state.py             # 状态管理
│   │   └── operator.py          # 操作符
│   ├── model_service/           # 模型服务
│   │   ├── model_service.py     # 服务接口
│   │   └── clients.py           # LLM 客户端
│   └── llms/                    # LLM 集成
│       └── clients.py           # 统一客户端
├── examples/                    # 示例代码
│   └── basic_usage.py
├── benchmarks/                  # 基准测试
└── tests/                       # 测试代码
```

## 🔧 配置

编辑 `config/default.yaml`:

```yaml
designer:
  model: "local"
  temperature: 0.1

executor:
  model: "local"
  temperature: 0.01

local:
  base_url: "http://localhost:8000/v1/"
```

## 📚 更多文档

- **项目架构**: [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md)
- **示例代码**: `examples/` 目录
- **基准测试**: `benchmarks/` 目录

## 📄 引用

```bibtex
@article{dyflow2025,
  title={DyFlow: Dynamic Workflow Framework for Agentic Reasoning},
  author={DyFlow Team},
  journal={NeurIPS},
  year={2025}
}
```

## 📜 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🔗 相关链接

- **Benchmark Integration**: 在 `benchmark_workflow/` 中查看如何集成 DyFlow
- **SAGE Framework**: https://github.com/intellistream/SAGE
