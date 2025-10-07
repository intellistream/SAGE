# SAGE Finetune - 轻量级大模型微调工具

一个简单、高效、易于扩展的大模型微调工具，支持 LoRA、量化训练、混合精度等特性。

## ✨ 核心特性

- 🚀 **一键微调**: 无需复杂配置，快速开始
- 💾 **内存优化**: 支持 8-bit/4-bit 量化，RTX 3060 也能训练大模型
- 🔄 **无缝集成**: 微调后的模型可直接在 `sage chat` 中使用
- ⚡ **自动化**: 自动检测、启动、管理微调模型服务
- 📊 **可视化**: 集成 TensorBoard 和 Wandb

---

## 🎯 快速开始

### 1️⃣ 微调模型

```bash
# 快速微调一个代码理解模型（约 10-30 分钟）
sage finetune quickstart code

# 可用任务类型: code | qa | chat | instruction | custom
# 模型保存在: ~/.sage/finetune_output/<任务类型>/
```

### 2️⃣ 使用微调模型

```bash
# 方式 1: 统一命令（推荐）
sage chat --backend finetune --finetune-model code

# 方式 2: 快捷命令
sage finetune chat code

# 方式 3: 结合 RAG 检索
sage chat --backend finetune --finetune-model code --index docs-public
```

**查看可用模型**:
```bash
ls ~/.sage/finetune_output/  # 显示所有已微调的模型
```

---

## 🔧 高级用法

### 自定义配置微调

```python
from sage.tools.finetune import LoRATrainer, TrainingConfig, PresetConfigs

# 使用预设配置
config = PresetConfigs.rtx_3060()
config.model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
config.data_path = "./my_data.json"
config.output_dir = "./output"

# 创建训练器
trainer = LoRATrainer(config)
trainer.train()
```

### CLI 完整流程

```bash
# 1. 准备数据（JSON 格式）
# 2. 创建配置并开始训练
sage finetune start --task code --auto

# 3. 监控训练（在浏览器中打开）
tensorboard --logdir ~/.sage/finetune_output/code/logs

# 4. 合并 LoRA 权重
sage finetune merge code

# 5. 使用模型聊天
sage chat --backend finetune --finetune-model code
```

---

## 🛠️ Chat Backend 集成

### Backend 类型对比

| Backend | 用途 | 特点 |
|---------|------|------|
| `mock` | 测试 | 无需 API，返回检索摘要 |
| `openai` | OpenAI | 官方 API，高质量 |
| `finetune` | **微调模型** | **本地推理，自动管理** |
| `vllm` | vLLM | 连接现有服务 |
| `ollama` | Ollama | 本地小模型 |

### 自动化流程

使用 `finetune` backend 时，系统会自动：

1. ✅ 检查模型是否存在
2. ✅ 检查是否需要合并 LoRA 权重
3. ✅ 检测 vLLM 服务状态
4. ✅ 启动服务（如未运行）
5. ✅ 连接并开始对话
6. ✅ 退出时清理资源

### 配置选项

```bash
# 环境变量配置
export SAGE_CHAT_BACKEND="finetune"
export SAGE_CHAT_FINETUNE_MODEL="code"
export SAGE_CHAT_FINETUNE_PORT="8000"

# 然后直接运行
sage chat
```

---

## ⚙️ 配置与参数

### 预设配置

### 预设配置

根据显卡选择优化配置：

| 显卡 | 预设名称 | 特点 |
|------|---------|------|
| RTX 3060 (12GB) | `rtx_3060()` | 8-bit 量化，batch_size=1 |
| RTX 4090 (24GB) | `rtx_4090()` | 无量化，batch_size=4 |
| A100 (40GB+) | `a100()` | BF16，batch_size=8 |
| <8GB 显存 | `minimal()` | 4-bit 量化，rank=4 |

### 数据格式

支持以下格式，自动检测：

**Alpaca 格式**:
```json
[{"instruction": "...", "input": "...", "output": "..."}]
```

**QA 格式**:
```json
[{"question": "...", "answer": "...", "context": "..."}]
```

**对话格式**:
```json
[{"conversations": [{"role": "user", "content": "..."}, ...]}]
```

### 训练配置示例

```python
config = TrainingConfig(
    model_name="Qwen/Qwen2.5-Coder-7B-Instruct",
    data_path="./data.json",
    output_dir="./output",
    num_train_epochs=3,
    learning_rate=1e-4,
    load_in_8bit=True,
    lora=LoRAConfig(r=16, lora_alpha=32),
)
```

---

## 🐛 常见问题

### 显存不足 (OOM)

按优先级尝试：
1. 启用量化: `load_in_8bit=True` 或 `load_in_4bit=True`
2. 减小序列: `max_length=512`
3. 减小 batch: `per_device_train_batch_size=1`
4. 梯度检查点: `gradient_checkpointing=True`
5. 减小 rank: `lora.r=4`

### 模型未找到

```bash
# 查看已有模型
ls ~/.sage/finetune_output/

# 确保使用正确的模型名称
sage chat --backend finetune --finetune-model <实际模型名>
```

### 监控训练

```bash
# 实时监控显存
watch -n 1 nvidia-smi

# TensorBoard 可视化
tensorboard --logdir ~/.sage/finetune_output/*/logs
```

---

## 📚 开发者资源

- **开发者文档**: [docs/dev-notes/finetune/](../../../../../docs/dev-notes/finetune/)
- **API 扩展**: 支持自定义 Trainer、数据处理等
- **Issue**: https://github.com/intellistream/SAGE/issues

---

**MIT License** | SAGE 生态系统的一部分，也可作为独立包使用

