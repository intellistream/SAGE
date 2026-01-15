# isage-finetune Copilot Instructions

## Package Identity

| 属性          | 值                                               |
| ------------- | ------------------------------------------------ |
| **PyPI 包名** | `isage-finetune`                                 |
| **导入名**    | `sage_libs.sage_finetune`                        |
| **SAGE 层级** | L3 (Algorithms & Libraries)                      |
| **版本格式**  | `0.1.x.y` (四段式)                               |
| **仓库**      | `https://github.com/intellistream/sage-finetune` |

## 层级定位

### ✅ 允许的依赖

```
L3 及以下:
├── sage-common (L1)      # 基础工具、类型、配置
├── sage-platform (L2)    # 平台服务抽象
├── Python stdlib         # 标准库
├── torch                 # PyTorch
├── transformers          # HuggingFace Transformers
├── peft                  # Parameter-Efficient Fine-Tuning
├── datasets              # HuggingFace Datasets
├── accelerate            # 分布式训练
└── bitsandbytes          # 量化 (可选)
```

### ❌ 禁止的依赖

```
L4+ 组件 (绝对禁止):
├── sage-middleware       # ❌ 中间件层
├── isage-vdb / SageVDB   # ❌ 向量数据库
├── isage-neuromem        # ❌ 内存系统
├── FastAPI / uvicorn     # ❌ 网络服务
├── Redis / RocksDB       # ❌ 外部存储
├── vLLM / LMDeploy       # ❌ 推理引擎
└── isagellm              # ❌ LLM 服务（通过注入）
```

**原则**: Finetune 库提供微调训练器和数据加载器，不涉及推理服务。

## 与 SAGE 主仓库的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                 SAGE 主仓库 (sage.libs.finetune)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Interface Layer                         │  │
│  │  • FineTuner (ABC)         • DatasetLoader (ABC)          │  │
│  │  • TrainingConfig          • LoRAConfig                   │  │
│  │  • TrainingCallback (ABC)                                  │  │
│  │  • create_trainer(), create_loader() (工厂函数)            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ▲                                   │
│                              │ 注册                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                  isage-finetune (独立 PyPI 包)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Implementation Layer                       │  │
│  │  Trainers:                                                 │  │
│  │  • LoRATrainer, QLoRATrainer, FullTrainer                 │  │
│  │  • DoRATrainer, LoRAPlusTrainer                           │  │
│  │  • AgentTrainer (Agent SFT)                               │  │
│  │  Loaders:                                                  │  │
│  │  • HFDatasetLoader, JSONLLoader, ParquetLoader            │  │
│  │  • TrajectoryLoader (Agent 轨迹)                           │  │
│  │  • InstructionLoader (指令数据)                            │  │
│  │  Callbacks:                                                │  │
│  │  • WandbCallback, TensorBoardCallback, EarlyStopCallback  │  │
│  │  • _register.py (自动注册到 SAGE 工厂)                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 自动注册机制

```python
# sage_libs/sage_finetune/_register.py
from sage.libs.finetune import register_trainer, register_loader

from .trainers import LoRATrainer, QLoRATrainer, FullTrainer, DoRATrainer
from .loaders import HFDatasetLoader, JSONLLoader, TrajectoryLoader

# 注册 Trainers
register_trainer("lora", LoRATrainer)
register_trainer("qlora", QLoRATrainer)
register_trainer("full", FullTrainer)
register_trainer("dora", DoRATrainer)
register_trainer("lora_plus", LoRAPlusTrainer)

# 注册 Loaders
register_loader("huggingface", HFDatasetLoader)
register_loader("jsonl", JSONLLoader)
register_loader("trajectory", TrajectoryLoader)
```

## 功能模块

### 1. LoRA Fine-tuning (低秩适应微调)

```python
from sage.libs.finetune import create_trainer, TrainingConfig, LoRAConfig

# LoRA 配置
lora_config = LoRAConfig(
    r=8,                          # 低秩矩阵秩
    lora_alpha=16,                # 缩放因子
    target_modules=["q_proj", "v_proj"],  # 目标模块
    lora_dropout=0.05,
    bias="none"
)

# 训练配置
training_config = TrainingConfig(
    model_name_or_path="Qwen/Qwen2.5-7B-Instruct",
    output_dir="./output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=2e-4,
    fp16=True
)

# 创建训练器
trainer = create_trainer("lora",
    training_config=training_config,
    lora_config=lora_config
)

# 训练
metrics = trainer.train(
    train_dataset=train_data,
    eval_dataset=eval_data
)

# 保存
trainer.save_model("./finetuned_model")
```

### 2. QLoRA (量化 LoRA)

```python
from sage.libs.finetune import create_trainer

# QLoRA：4-bit 量化 + LoRA
trainer = create_trainer("qlora",
    training_config=training_config,
    lora_config=lora_config,
    quantization_config={
        "load_in_4bit": True,
        "bnb_4bit_compute_dtype": "float16",
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_use_double_quant": True
    }
)

# 8-bit 量化
trainer = create_trainer("qlora",
    training_config=training_config,
    lora_config=lora_config,
    quantization_config={"load_in_8bit": True}
)
```

### 3. DoRA & LoRA+ (高级 LoRA 变体)

```python
# DoRA (Weight-Decomposed Low-Rank Adaptation)
trainer = create_trainer("dora",
    training_config=training_config,
    lora_config=lora_config
)

# LoRA+ (不同学习率)
trainer = create_trainer("lora_plus",
    training_config=training_config,
    lora_config=lora_config,
    lora_plus_config={
        "lora_lr_ratio": 16.0  # B 矩阵学习率是 A 矩阵的 16 倍
    }
)
```

### 4. Full Fine-tuning (全参数微调)

```python
# 全参数微调（需要更多 GPU 内存）
trainer = create_trainer("full",
    training_config=training_config
)

# 使用 DeepSpeed ZeRO
trainer = create_trainer("full",
    training_config=training_config,
    deepspeed_config="./ds_config_zero3.json"
)
```

### 5. Agent SFT (Agent 监督微调)

```python
from sage.libs.finetune import create_trainer, create_loader

# 加载 Agent 轨迹数据
loader = create_loader("trajectory")
train_data = loader.load("./agent_trajectories.jsonl")

# Agent 微调
trainer = create_trainer("lora",
    training_config=training_config,
    lora_config=lora_config,
    formatting_func=format_agent_trajectory  # 轨迹格式化函数
)

# 轨迹格式示例
"""
{
    "task": "搜索最新的 AI 新闻",
    "trajectory": [
        {"thought": "我需要搜索网页", "action": "search", "input": {"query": "AI news 2024"}},
        {"observation": "Found 10 results..."},
        {"thought": "找到相关结果", "action": "finish", "input": {"answer": "..."}}
    ]
}
"""
```

### 6. Dataset Loaders (数据加载器)

```python
from sage.libs.finetune import create_loader

# HuggingFace 数据集
loader = create_loader("huggingface")
dataset = loader.load("tatsu-lab/alpaca", split="train")
processed = loader.preprocess(dataset, tokenizer)

# JSONL 文件
loader = create_loader("jsonl")
dataset = loader.load("./data/instructions.jsonl")

# Parquet 文件
loader = create_loader("parquet")
dataset = loader.load("./data/training_data.parquet")

# 流式加载（大数据集）
for sample in loader.stream("./large_dataset.jsonl"):
    yield sample

# 指令数据格式
"""
{"instruction": "翻译成英文", "input": "你好", "output": "Hello"}
{"instruction": "写一首诗", "input": "", "output": "春眠不觉晓..."}
"""
```

### 7. Callbacks (训练回调)

```python
from sage.libs.finetune import create_trainer
from sage_libs.sage_finetune.callbacks import (
    WandbCallback, TensorBoardCallback, EarlyStopCallback
)

# 创建回调
callbacks = [
    WandbCallback(project="my-finetune", run_name="lora-exp1"),
    TensorBoardCallback(log_dir="./tb_logs"),
    EarlyStopCallback(patience=3, metric="eval_loss")
]

# 使用回调
trainer = create_trainer("lora",
    training_config=training_config,
    lora_config=lora_config,
    callbacks=callbacks
)
```

## 目录结构

```
sage-finetune/                      # 独立仓库根目录
├── pyproject.toml                  # 包配置 (name = "isage-finetune")
├── README.md
├── COPILOT_INSTRUCTIONS.md         # 本文件
├── LICENSE
├── src/
│   └── sage_libs/                  # 命名空间包
│       └── sage_finetune/
│           ├── __init__.py         # 主入口
│           ├── _version.py         # 版本信息
│           ├── _register.py        # 自动注册
│           ├── trainers/           # 训练器实现
│           │   ├── __init__.py
│           │   ├── lora.py         # LoRA Trainer
│           │   ├── qlora.py        # QLoRA Trainer
│           │   ├── dora.py         # DoRA Trainer
│           │   ├── lora_plus.py    # LoRA+ Trainer
│           │   ├── full.py         # Full Fine-tuning
│           │   └── agent.py        # Agent SFT Trainer
│           ├── loaders/            # 数据加载器实现
│           │   ├── __init__.py
│           │   ├── huggingface.py  # HF Datasets
│           │   ├── jsonl.py        # JSONL 格式
│           │   ├── parquet.py      # Parquet 格式
│           │   ├── trajectory.py   # Agent 轨迹
│           │   └── instruction.py  # 指令数据
│           ├── callbacks/          # 回调实现
│           │   ├── __init__.py
│           │   ├── wandb.py
│           │   ├── tensorboard.py
│           │   └── early_stop.py
│           └── utils/              # 工具函数
│               ├── __init__.py
│               ├── formatting.py   # 数据格式化
│               └── quantization.py # 量化工具
├── tests/
│   ├── conftest.py
│   ├── test_trainers.py
│   ├── test_loaders.py
│   └── test_callbacks.py
└── examples/
    ├── lora_finetune.py
    ├── qlora_finetune.py
    ├── agent_sft.py
    └── distributed_training.py
```

## 常见问题修复指南

### 1. OOM (显存不足)

```python
# ❌ 问题：全参数微调 OOM
trainer = create_trainer("full", ...)  # 7B 模型需要 ~60GB

# ✅ 修复方案 1：使用 LoRA
trainer = create_trainer("lora", ...)  # ~8GB

# ✅ 修复方案 2：使用 QLoRA
trainer = create_trainer("qlora",
    quantization_config={"load_in_4bit": True}
)  # ~6GB

# ✅ 修复方案 3：减小批量大小 + 梯度累积
training_config = TrainingConfig(
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16  # 等效批量 = 16
)
```

### 2. LoRA 目标模块选择

```python
# ❌ 问题：LoRA 应用到错误的模块
lora_config = LoRAConfig(
    target_modules=["embedding"]  # Embedding 层通常不用 LoRA
)

# ✅ 修复：选择注意力层
lora_config = LoRAConfig(
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]  # QKV + 输出投影
)

# ✅ 更全面的配置
lora_config = LoRAConfig(
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",  # 注意力
        "gate_proj", "up_proj", "down_proj"       # FFN
    ]
)
```

### 3. 数据格式错误

```python
# ❌ 问题：数据格式不符合预期
data = {"text": "Hello"}  # 缺少 instruction/output

# ✅ 修复：使用正确的格式
# 格式 1: Alpaca 格式
data = {
    "instruction": "翻译成英文",
    "input": "你好",
    "output": "Hello"
}

# 格式 2: ShareGPT 格式
data = {
    "conversations": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "Hello"}
    ]
}

# 格式 3: 自定义格式 + 格式化函数
def format_func(example):
    return f"User: {example['question']}\nAssistant: {example['answer']}"

trainer = create_trainer("lora", formatting_func=format_func)
```

### 4. 学习率问题

```python
# ❌ 问题：学习率过高导致不稳定
training_config = TrainingConfig(learning_rate=1e-3)  # 太高

# ✅ 修复：使用合适的学习率
# LoRA: 1e-4 ~ 2e-4
# QLoRA: 1e-4 ~ 5e-5
# Full: 1e-5 ~ 5e-6
training_config = TrainingConfig(
    learning_rate=2e-4,  # LoRA 推荐
    warmup_steps=100,    # 预热
    lr_scheduler_type="cosine"  # 余弦退火
)
```

### 5. 模型保存格式

```python
# ❌ 问题：保存的是 adapter 但想要合并
trainer.save_model("./adapter")  # 只保存 adapter

# ✅ 修复：合并后保存
trainer.merge_and_save("./merged_model")

# 或手动合并
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained("base_model")
peft_model = PeftModel.from_pretrained(base_model, "./adapter")
merged = peft_model.merge_and_unload()
merged.save_pretrained("./merged_model")
```

### 6. 多 GPU 训练

```python
# ❌ 问题：多 GPU 但只用了一张
trainer.train()  # 默认单 GPU

# ✅ 修复方案 1：使用 accelerate
# accelerate launch --num_processes=4 train.py

# ✅ 修复方案 2：DeepSpeed
training_config = TrainingConfig(
    deepspeed="./ds_config.json"
)

# ✅ 修复方案 3：FSDP
training_config = TrainingConfig(
    fsdp="full_shard auto_wrap"
)
```

## 关键设计原则

### 1. 配置分离

训练配置和模型配置分离：

```python
# ✅ 好：配置分离
training_config = TrainingConfig(...)  # 训练超参
lora_config = LoRAConfig(...)          # LoRA 配置

trainer = create_trainer("lora",
    training_config=training_config,
    lora_config=lora_config
)
```

### 2. 数据格式灵活

支持多种数据格式，通过格式化函数统一：

```python
class DatasetLoader:
    def preprocess(self, dataset, tokenizer, formatting_func=None):
        if formatting_func:
            dataset = dataset.map(formatting_func)
        return dataset.map(lambda x: tokenizer(x["text"]))
```

### 3. 回调扩展

通过回调机制扩展功能：

```python
class TrainingCallback(ABC):
    def on_train_begin(self, args, state, control): pass
    def on_epoch_begin(self, args, state, control): pass
    def on_step_end(self, args, state, control): pass
    def on_evaluate(self, args, state, control, metrics): pass
    def on_train_end(self, args, state, control): pass
```

### 4. 量化透明

量化配置独立于训练逻辑：

```python
# 量化是可选的附加配置
trainer = create_trainer("qlora",
    training_config=training_config,
    lora_config=lora_config,
    quantization_config={"load_in_4bit": True}  # 可选
)
```

### 5. 模型无关性

不绑定特定模型架构：

```python
# 支持任何 HuggingFace 兼容模型
training_config = TrainingConfig(
    model_name_or_path="Qwen/Qwen2.5-7B-Instruct"  # Qwen
    # model_name_or_path="meta-llama/Llama-3-8B"  # Llama
    # model_name_or_path="THUDM/chatglm3-6b"     # ChatGLM
)
```

## 测试规范

```bash
# 运行单元测试（不需要 GPU）
pytest tests/ -v -m "not gpu"

# 运行 GPU 测试
pytest tests/ -v -m "gpu" --gpu

# 运行小规模训练测试
pytest tests/test_trainers.py -v --run-training
```

## 与其他 L3 库的协作

```python
# isage-finetune + isage-eval 协作
from sage_libs.sage_finetune import create_trainer, create_loader
from sage_libs.sage_eval import create_metric

# 训练
trainer = create_trainer("lora", ...)
trainer.train(train_data)

# 评估微调效果
metric = create_metric("perplexity")
result = metric.compute(
    texts=test_texts,
    model=trainer.model
)
print(f"微调后困惑度: {result.value:.2f}")
```

## 发布流程

```bash
# 使用 sage-pypi-publisher
cd /path/to/sage-pypi-publisher
./publish.sh sage-finetune --auto-bump patch

# 或手动指定版本
./publish.sh sage-finetune --version 0.1.0.1
```
