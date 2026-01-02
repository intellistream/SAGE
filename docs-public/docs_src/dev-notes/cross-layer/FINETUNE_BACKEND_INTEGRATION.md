# Finetune 模型接入对话后端完整流程

## 概述

本文档详细说明如何将微调后的模型接入到 Studio 对话页面的后端，以及整个技术架构。

## 技术架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户操作流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Finetune 页面                                                │
│     └─> 选择模型 → 上传数据 → 开始训练                            │
│                                                                 │
│  2. 训练完成后                                                    │
│     └─> 点击 "设为后端" 按钮                                      │
│                                                                 │
│  3. Chat 页面                                                    │
│     └─> 对话自动使用微调后的模型                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         后端技术栈                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend (React)                                               │
│     │                                                           │
│     │ POST /api/finetune/use-as-backend                        │
│     │ { task_id: "..." }                                       │
│     ▼                                                           │
│  Backend API (FastAPI)                                          │
│     │                                                           │
│     │ 1. 获取微调模型路径                                         │
│     │ 2. 调用 vllm_registry.register_model()                   │
│     │ 3. 调用 vllm_registry.switch_model()                     │
│     │ 4. 更新环境变量                                            │
│     ▼                                                           │
│  vLLM Registry (sage.platform.llm)                              │
│     │                                                           │
│     │ - 管理所有可用模型                                          │
│     │ - 动态切换当前模型                                          │
│     │ - 提供统一的推理接口                                        │
│     ▼                                                           │
│  vLLM Engine                                                    │
│     │                                                           │
│     │ - 加载模型到 GPU                                           │
│     │ - 执行推理请求                                             │
│     │ - 返回生成结果                                             │
│     ▼                                                           │
│  Chat Frontend                                                  │
│     │                                                           │
│     │ - 用户发送消息                                             │
│     │ - 自动使用当前激活的模型                                    │
│     │ - 显示回复                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 详细流程说明

### 步骤 1: 用户完成微调

在 Finetune 页面：

1. 选择基础模型（如 `Qwen/Qwen2.5-Coder-1.5B-Instruct`）
1. 上传训练数据或使用 SAGE 文档
1. 点击 "开始微调"
1. 等待训练完成（状态变为 "已完成"）

**微调输出**：

- 模型保存在：`~/.sage/studio_finetune/outputs/{task_id}/`
- 包含：
  - `adapter_model.bin` - LoRA 适配器权重
  - `adapter_config.json` - LoRA 配置
  - `tokenizer.json` - 分词器
  - `training_args.json` - 训练参数

### 步骤 2: 切换为对话后端

#### 2.1 前端操作

在微调任务列表中，找到已完成的任务，点击 **"设为后端"** 按钮：

```tsx
// FinetunePanel.tsx
<Button
    size="small"
    icon={<Settings className="w-3 h-3" />}
    onClick={() => handleUseAsBackend(task.id)}
>
    设为后端
</Button>
```

#### 2.2 确认对话框

弹出确认框：

```
切换为对话后端
确定要将此微调模型设置为 Studio 的对话后端吗？当前对话将使用此模型。
[取消] [确定]
```

#### 2.3 发送 API 请求

点击 "确定" 后，发送 POST 请求：

```tsx
const handleUseAsBackend = async (taskId: string) => {
    const response = await fetch(
        'http://localhost:8080/api/finetune/use-as-backend',
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId }),
        }
    )
}
```

### 步骤 3: 后端处理（关键逻辑）

#### 3.1 API 端点实现

```python
# api.py
@app.post("/api/finetune/use-as-backend")
async def use_finetuned_model_as_backend(request: UseAsBackendRequest):
    """将微调后的模型设置为 Studio 的对话后端"""

    # 1. 获取微调任务
    task = finetune_manager.get_task(request.task_id)
    if not task or task.status != "completed":
        raise HTTPException(status_code=404, detail="Task not found or not completed")

    # 2. 获取模型路径
    model_path = Path(task.output_dir)
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Model directory not found")

    # 3. 自动检测 GPU 配置
    import torch
    num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0

    config = {
        "trust_remote_code": True,
        "max_model_len": 2048,
    }

    if num_gpus > 0:
        config["gpu_memory_utilization"] = 0.8
        if num_gpus > 1:
            config["tensor_parallel_size"] = num_gpus

    # 4. 注册模型到 vLLM Registry
    from sage.platform.llm.vllm_registry import vllm_registry

    model_name = f"sage-finetuned-{request.task_id}"
    vllm_registry.register_model(
        model_name=model_name,
        model_path=str(model_path),
        config=config,
    )

    # 5. 切换到该模型（这是关键步骤！）
    vllm_registry.switch_model(model_name)

    # 6. 更新环境变量（供 RAG pipeline 使用）
    os.environ["SAGE_STUDIO_LLM_MODEL"] = model_name
    os.environ["SAGE_STUDIO_LLM_PATH"] = str(model_path)

    return {
        "status": "success",
        "message": f"已切换到微调模型: {model_name}",
        "model_name": model_name,
    }
```

#### 3.2 vLLM Registry 工作原理

`vllm_registry` 是 SAGE Platform 层的核心组件，负责管理所有 LLM 模型：

```python
# sage.platform.llm.vllm_registry

class VLLMRegistry:
    def __init__(self):
        self.models = {}  # 已注册的模型
        self.current_model = None  # 当前激活的模型
        self.engine = None  # vLLM 推理引擎

    def register_model(self, model_name, model_path, config):
        """注册一个新模型"""
        self.models[model_name] = {
            "path": model_path,
            "config": config,
        }

    def switch_model(self, model_name):
        """切换到指定模型（卸载旧模型，加载新模型）"""
        # 1. 卸载当前模型
        if self.engine:
            self.engine.shutdown()

        # 2. 加载新模型
        model_info = self.models[model_name]
        from vllm import LLM

        self.engine = LLM(
            model=model_info["path"],
            **model_info["config"]
        )

        self.current_model = model_name

    def generate(self, prompt, **kwargs):
        """使用当前模型生成文本"""
        if not self.engine:
            raise RuntimeError("No model loaded")

        return self.engine.generate(prompt, **kwargs)
```

### 步骤 4: Chat 页面自动使用新模型

#### 4.1 Chat 发送消息流程

当用户在 Chat 页面发送消息时：

```tsx
// ChatPanel.tsx
const sendMessage = async (message: string) => {
    const response = await fetch('http://localhost:8080/api/chat', {
        method: 'POST',
        body: JSON.stringify({ message }),
    })
}
```

#### 4.2 Chat API 使用 vLLM Registry

```python
# api.py
@app.post("/api/chat")
async def chat(request: ChatRequest):
    """处理对话请求"""
    from sage.platform.llm.vllm_registry import vllm_registry

    # 自动使用当前激活的模型（已被 switch_model 切换）
    response = vllm_registry.generate(
        prompt=request.message,
        max_tokens=1024,
        temperature=0.7,
    )

    return {"response": response}
```

**关键点**：

- ✅ Chat API 不需要修改任何代码
- ✅ `vllm_registry.generate()` 自动使用 `current_model`
- ✅ `current_model` 已被 `switch_model()` 设置为微调模型
- ✅ 用户发送的所有消息都会使用微调后的模型回复

## GPU 自动检测逻辑

### 检测代码

```python
import torch

# 检测 GPU 数量
num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0

# 获取单个 GPU 的显存（GB）
if num_gpus > 0:
    gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
else:
    gpu_memory_gb = 0
```

### 根据检测结果配置模型

```python
config = {
    "trust_remote_code": True,
    "max_model_len": 2048,
}

# 只有当有 GPU 时才设置 GPU 相关参数
if num_gpus > 0:
    config["gpu_memory_utilization"] = 0.8

    # 如果有多个 GPU 且模型较大，启用张量并行
    if num_gpus > 1:
        config["tensor_parallel_size"] = num_gpus
```

### 支持的场景

| GPU 数量 | 配置策略                        | 适用场景              |
| -------- | ------------------------------- | --------------------- |
| 0 (CPU)  | 不设置 GPU 参数                 | 测试/调试（非常慢）   |
| 1 GPU    | `gpu_memory_utilization=0.8`    | RTX 3060, RTX 4090 等 |
| 2+ GPU   | 额外设置 `tensor_parallel_size` | A100 x2, H100 集群    |

### GPU 显存自适应

```python
# 未来可扩展：根据显存大小选择模型参数
if gpu_memory_gb < 8:
    # RTX 3060 (6GB)
    config["max_model_len"] = 2048
elif gpu_memory_gb < 16:
    # RTX 4090 (24GB)
    config["max_model_len"] = 4096
else:
    # A100 (40GB/80GB)
    config["max_model_len"] = 8192
```

## 用户体验流程

### 完整操作步骤

1. **微调模型**

   - 进入 Finetune 页面
   - 选择 `Qwen/Qwen2.5-Coder-1.5B-Instruct`
   - 使用 SAGE 文档（一键准备）
   - 点击 "开始微调"
   - 等待 2-4 小时（取决于数据量）

1. **切换后端**

   - 训练完成后，任务状态显示 "已完成"
   - 点击任务旁边的 **"设为后端"** 按钮
   - 确认对话框点击 "确定"
   - 看到提示：`✅ 已切换到微调模型: sage-finetuned-{task_id}`

1. **测试模型**

   - 切换到 Chat 页面
   - 发送测试消息，例如：
     ```
     什么是 SAGE？请简单介绍一下。
     ```
   - 观察回复是否包含 SAGE 文档中的知识
   - 对比切换前后的回复差异

### 预期效果

**切换前（使用原始模型）**：

```
用户: 什么是 SAGE？
模型: SAGE 可能指多个含义...（通用回答）
```

**切换后（使用微调模型）**：

```
用户: 什么是 SAGE？
模型: SAGE 是一个用于构建 AI/LLM 数据处理流水线的 Python 框架，
      支持声明式数据流... (基于 SAGE 文档的专业回答)
```

## 验证切换是否成功

### 方法 1: 观察日志

```bash
# 查看 Studio 后端日志
tail -f ~/.sage/studio.log

# 应该看到类似输出：
# INFO: Registered model: sage-finetuned-{task_id}
# INFO: Switched to model: sage-finetuned-{task_id}
# INFO: Loading model from /home/user/.sage/studio_finetune/outputs/{task_id}
```

### 方法 2: 检查环境变量

```python
# 在 Python 中检查
import os
print(os.environ.get("SAGE_STUDIO_LLM_MODEL"))
# 输出: sage-finetuned-{task_id}

print(os.environ.get("SAGE_STUDIO_LLM_PATH"))
# 输出: /home/user/.sage/studio_finetune/outputs/{task_id}
```

### 方法 3: 发送测试对话

在 Chat 页面发送特定问题，检查模型是否使用微调后的知识回答。

## 常见问题

### Q1: 切换后 Chat 仍使用旧模型？

**可能原因**：

- 浏览器缓存未刷新
- 后端未正确重启

**解决方案**：

```bash
# 1. 重启 Studio
sage studio restart

# 2. 浏览器硬刷新
# Ctrl+Shift+R (Windows/Linux)
# Cmd+Shift+R (Mac)
```

### Q2: 切换时报错 "Model directory not found"？

**原因**：微调输出目录不存在或被删除

**解决方案**：

```bash
# 检查模型是否存在
ls -la ~/.sage/studio_finetune/outputs/{task_id}/

# 如果不存在，需要重新微调
```

### Q3: 模型加载速度慢？

**原因**：

- 模型文件大
- GPU 显存不足需要卸载旧模型

**优化**：

- 使用更小的基础模型（1.5B vs 7B）
- 增加 GPU 显存
- 使用量化技术（未来支持）

### Q4: 如何切换回原始模型？

**方法 1**: 重启 Studio

```bash
sage studio restart
```

**方法 2**: 手动切换（未来支持）

```python
from sage.platform.llm.vllm_registry import vllm_registry
vllm_registry.switch_model("original-model-name")
```

## 技术细节

### vLLM Registry 单例模式

```python
# vllm_registry 是全局单例
from sage.platform.llm.vllm_registry import vllm_registry

# 所有代码共享同一个实例
assert id(vllm_registry) == id(another_import.vllm_registry)
```

### 模型切换的内存管理

切换模型时的内存流程：

1. 调用 `engine.shutdown()` 卸载旧模型
1. 等待 GPU 显存释放
1. 加载新模型到 GPU
1. 更新 `current_model` 指针

### LoRA 适配器加载

微调使用 LoRA（Low-Rank Adaptation），加载时：

```python
# vLLM 自动检测并加载 LoRA 适配器
engine = LLM(
    model="/path/to/base/model",
    enable_lora=True,
    lora_modules=[
        LoRARequest(
            lora_name="sage-finetuned",
            lora_path="/path/to/adapter",
        )
    ]
)
```

## 未来改进

### 1. 模型管理 UI

在 Settings 页面添加 "模型管理" 面板：

- 查看所有已注册模型
- 一键切换模型
- 删除不需要的模型
- 查看当前激活的模型

### 2. 多模型对比

支持同时加载多个模型，对话时选择使用哪个：

```tsx
<Select>
    <Option value="original">原始模型</Option>
    <Option value="sage-finetuned-001">微调模型 1</Option>
    <Option value="sage-finetuned-002">微调模型 2</Option>
</Select>
```

### 3. A/B 测试

同一个问题发送给多个模型，对比回复质量。

### 4. 模型性能监控

显示模型的：

- 推理速度（tokens/s）
- GPU 使用率
- 显存占用
- 平均响应时间

## 相关文件

**前端**：

- `packages/sage-studio/src/sage/studio/frontend/src/components/FinetunePanel.tsx`

**后端**：

- `packages/sage-studio/src/sage/studio/config/backend/api.py`
- `packages/sage-platform/src/sage/platform/llm/vllm_registry.py`

**服务**：

- `packages/sage-studio/src/sage/studio/services/finetune_manager.py`

## 总结

整个流程的核心是 **vLLM Registry**：

1. **Finetune** → 训练模型，保存到 `~/.sage/studio_finetune/outputs/`
1. **"设为后端"** → 调用 `vllm_registry.register_model()` + `switch_model()`
1. **Chat** → 自动使用 `vllm_registry.current_model` 生成回复

用户只需点击一次 "设为后端" 按钮，后续所有对话都会自动使用微调后的模型，无需任何额外配置。
