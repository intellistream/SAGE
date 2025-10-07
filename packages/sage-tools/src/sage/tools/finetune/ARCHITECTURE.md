# Finetune 模块架构说明

## 📁 目录结构（模块化设计）

```
packages/sage-tools/src/sage/tools/finetune/
├── __init__.py          # 模块入口（导出核心类和 CLI app）
├── README.md            # 用户文档
├── ARCHITECTURE.md      # 本文档（架构说明）
├── cli.py               # CLI 命令处理（466 行）
├── config.py            # 训练配置类（230 行）
├── core.py              # 核心逻辑：数据准备、配置生成（223 行）
├── data.py              # 数据处理（249 行）
├── models.py            # 数据模型和枚举（26 行）
├── service.py           # 服务管理：训练、合并、部署（216 行）
├── trainer.py           # LoRA 训练器（299 行）
└── utils.py             # 工具函数（104 行）

总计：~1868 行（vs 原来的 1270 行单文件）
```

## 🎯 设计原则

### 1. **统一管理**
- 所有 finetune 相关代码集中在 `sage.tools.finetune` 模块
- CLI 主入口直接导入：`from sage.tools.finetune import app`
- 不再有重复的目录结构

### 2. **模块化职责**

| 文件 | 职责 | 行数 |
|------|------|------|
| `cli.py` | CLI 命令处理、用户交互 | 466 |
| `trainer.py` | LoRA 训练器实现 | 299 |
| `data.py` | 数据加载和预处理 | 249 |
| `config.py` | 配置类定义 | 230 |
| `core.py` | 数据准备、配置生成 | 223 |
| `service.py` | 训练执行、模型合并、服务部署 | 216 |
| `utils.py` | 通用工具函数 | 104 |
| `__init__.py` | 模块导出 | 55 |
| `models.py` | 枚举和数据模型 | 26 |

### 3. **清晰的依赖关系**

```
cli.py
  ├─> models.py      (枚举定义)
  ├─> utils.py       (工具函数)
  ├─> core.py        (核心逻辑)
  └─> service.py     (服务管理)

service.py
  └─> (使用外部库: transformers, peft, vllm)

core.py
  ├─> models.py
  └─> utils.py

trainer.py
  ├─> config.py
  └─> data.py
```

## 🔄 与之前的对比

### 之前（v0）
```
packages/sage-tools/src/sage/tools/cli/commands/
└── finetune.py          # 1270 行单文件，难以维护

问题：
- ❌ 代码过长，职责混乱
- ❌ 难以测试和维护
- ❌ 无法独立发布
```

### 之前（v1 - 临时方案）
```
packages/sage-tools/src/sage/tools/finetune/
├── trainer.py
├── config.py
└── data.py

packages/sage-tools/src/sage/tools/cli/commands/finetune/
├── commands.py
├── core.py
├── service.py
└── utils.py

问题：
- ❌ 两个 finetune 目录，结构重复
- ❌ 职责不清晰
- ❌ 导入路径混乱
```

### 现在（v2 - 最终方案）
```
packages/sage-tools/src/sage/tools/finetune/
├── __init__.py          # 统一入口
├── cli.py               # CLI 命令
├── trainer.py           # 训练器
├── config.py            # 配置
├── data.py              # 数据
├── core.py              # 核心逻辑
├── service.py           # 服务管理
├── utils.py             # 工具
└── models.py            # 模型定义

优势：
- ✅ 统一目录，清晰明了
- ✅ 模块化设计，职责分明
- ✅ 易于测试和维护
- ✅ 可独立发布到 PyPI
- ✅ 代码行数合理（最大 466 行）
```

## 📦 模块导出

### 作为 Python 库使用

```python
# 导入训练相关类
from sage.tools.finetune import (
    LoRATrainer,
    TrainingConfig,
    LoRAConfig,
    PresetConfigs,
    prepare_dataset,
    load_training_data,
)

# 使用
config = PresetConfigs.rtx_3060()
trainer = LoRATrainer(config)
trainer.train(dataset)
```

### 作为 CLI 使用

```python
# CLI 主入口导入
from sage.tools.finetune import app as finetune_app

# 注册到主 CLI
main_app.add_typer(finetune_app, name="finetune")
```

```bash
# 命令行使用
sage finetune quickstart code
sage finetune start --task qa --data data.json
sage finetune run finetune_output/code
sage finetune merge code
sage finetune serve code --port 8000
```

## 🚀 未来规划

### v3.0 - Pipeline 组件化
- [ ] 将微调改造为 SAGE Pipeline 组件
- [ ] 支持完整的 dataflow 编排和可视化
- [ ] 集成 SAGE 统一监控和资源管理
- [ ] 支持分布式训练

### v4.0 - 高级特性
- [ ] 支持增量微调和持续学习
- [ ] 支持多模态微调 (vision + language)
- [ ] 支持 RLHF 和 DPO
- [ ] 自动化超参数搜索

## 📝 开发指南

### 添加新命令

1. 在 `cli.py` 中添加新的 `@app.command()`
2. 如需新逻辑，在对应模块中添加函数
3. 更新 `examples` 命令

### 添加新的训练模式

1. 在 `models.py` 中添加新枚举
2. 在 `core.py` 中添加数据准备逻辑
3. 在 `trainer.py` 中实现训练逻辑
4. 在 `cli.py` 中添加 CLI 支持

### 测试

```bash
# 单元测试
pytest packages/sage-tools/src/sage/tools/finetune/

# CLI 测试
sage finetune --help
sage finetune examples
```

## 📊 代码质量

### 行数分布
- 最大文件：`cli.py` (466 行) - CLI 命令处理
- 平均文件：~208 行
- 总计：1868 行

### 优势
- ✅ 每个文件职责单一
- ✅ 便于代码审查
- ✅ 易于测试
- ✅ 支持增量开发

---

**维护者**: SAGE Team  
**最后更新**: 2025-10-07  
**版本**: v2.0 (模块化重构)
