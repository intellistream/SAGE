# 资源文件 (Resources)

本目录包含SAGE示例所需的所有资源文件，统一管理配置和数据。

## 📂 目录结构

```
resources/
├── config/         # 配置文件
│   ├── config.yaml                 # 主配置文件
│   ├── config_*.yaml              # 各种功能特定配置
│   └── README.md
└── data/           # 示例数据
    ├── sample/                     # 基础示例数据
    ├── neuromem_datasets/          # 神经记忆数据集
    └── README.md
```

## 🔧 配置管理

### 📄 配置文件说明
- `config.yaml` - 主配置文件，RAG基础配置
- `config_batch.yaml` - 批处理配置
- `config_hf.yaml` - HuggingFace模型配置
- `config_ray.yaml` - Ray分布式配置
- `multiagent_config.yaml` - 多智能体配置
- 更多配置文件详见 [config/README.md](config/README.md)

### 🎯 配置路径引用
从示例代码目录引用配置：
```python
# 从 src/rag/ 目录运行
config = load_config("../../resources/config/config.yaml")

# 从 src/agents/ 目录运行  
config = load_config("../../resources/config/multiagent_config.yaml")
```

## 📊 数据管理

### 📁 数据文件说明
- `sample/` - 测试问题和评估数据
- `neuromem_datasets/` - 专业实验数据集
- 详细说明见 [data/README.md](data/README.md)

### 🔗 数据路径引用
配置文件中的数据路径：
```yaml
# config.yaml 中的数据引用
source:
  data_path: "../data/sample/question.txt"  # 相对于config目录
```

## 🚀 使用指南

### 📝 添加新配置
1. 在 `config/` 目录创建新的YAML文件
2. 参考现有配置文件的格式
3. 在示例代码中使用相对路径引用

### 📄 添加新数据
1. 在 `data/sample/` 添加新的数据文件
2. 在相应的配置文件中更新 `data_path`
3. 确保路径相对于config目录正确

## 🔍 故障排除

### 路径问题
如果遇到配置或数据文件找不到的错误：
1. 检查当前工作目录
2. 验证相对路径是否正确
3. 确认文件是否存在于预期位置

### 配置验证
```python
# 验证配置文件加载
from sage.utils.config_loader import load_config
config = load_config("../../resources/config/config.yaml")
print("配置加载成功:", config.keys())
```
