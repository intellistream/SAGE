# MemorySource 数据源文档

## 概述

`MemorySource` 是记忆实验的数据源组件，负责从多种数据集中逐个读取对话轮次数据。它是整个记忆测试 Pipeline 的起点，通过背压机制实现 one-by-one 的数据处理。

## 支持的数据集

### Locomo 数据集

长轮对话数据集，用于测试模型在长对话场景下的记忆能力。

**数据特点：**

- 包含多个会话（session）
- 每个会话包含多轮对话
- 对话以问答对的形式组织（每次读取 2 轮对话）

**读取机制：**

- `dialog_ptr` 从 0 开始，每次递增 2（对应一组问答）
- 自动遍历所有会话和对话轮次
- 内置背压控制（10ms 延迟），避免数据源产生过快

## 输出格式

每次调用 `execute()` 返回一个数据包，格式如下：

```python
{
    "task_id": str,        # 任务/样本ID
    "session_id": int,     # 会话ID
    "dialog_id": int,      # 对话索引（当前 dialog_ptr 值）
    "dialogs": [           # 对话列表
        {
            "speaker": str,         # 说话者
            "text": str,           # 对话内容
        },
        ...
    ],
    "dialog_len": int,     # 对话列表长度
    "packet_idx": int,     # 当前数据包序号（从0开始）
    "total_packets": int   # 总数据包数
}
```

## 配置说明

在配置文件中需要指定以下参数：

- `dataset`: 数据集类型（如 "locomo"）
- `task_id`: 任务/样本ID

示例：

```yaml
dataset: "locomo"
task_id: "conv26"
```

## 工作流程

### 初始化阶段

统一的初始化流程（所有数据集一致）：

1. **检查数据集和 task_id 合理性**：验证数据集类型是否支持
1. **创建数据加载器并获取数据集核心信息**：
   - 根据数据集类型创建对应的 DataLoader
   - 调用 loader 获取任务的核心数据（如会话列表、对话轮数等）
1. **打印当前任务信息**：输出统计信息（会话数、对话数、数据包数等）
1. **初始化任务指针**：设置遍历所需的指针变量

### 执行阶段

统一的执行流程（所有数据集一致）：

每次 `execute()` 调用：

1. 添加 10ms 延迟（背压控制）
1. 检查是否遍历完所有数据，是则返回 `None` 触发停止
1. 获取当前会话信息
1. 检查当前会话是否遍历完，若是则移动到下一个会话
1. 从数据加载器读取当前对话
1. 构造输出数据包（统一格式）
1. 移动指针到下一组对话
1. 返回数据包

### 终止条件

当所有会话的所有对话都遍历完毕时，返回 `None`，Pipeline 会收到停止信号。

## 添加新数据集

所有数据集使用统一的初始化和执行流程，添加新数据集只需：

### 1. 创建数据加载器

在 `sage.data` 包中创建对应的 DataLoader 类，需实现：

- `get_turn(task_id)`: 返回任务的会话列表和对话轮数信息
- `get_dialog(task_id, session_x, dialog_y)`: 返回指定会话和对话索引的对话内容

### 2. 在 `__init__` 中注册

在 `MemorySource.__init__()` 中添加数据集判断分支：

```python
if self.dataset == "new_dataset":
    self.loader = NewDatasetLoader()
elif self.dataset == "locomo":
    self.loader = LocomoDataLoader()
else:
    raise ValueError(f"不支持的数据集: {self.dataset}")
```

### 3. 确保数据格式一致

新数据集的加载器需要保证：

- `get_turn()` 返回格式与 Locomo 一致：`[(session_id, max_dialog_idx), ...]`
- `get_dialog()` 返回格式与 Locomo 一致：`[{"speaker": str, "text": str}, ...]`
- 对话索引从 0 开始，每次递增 2（对应问答对）

### 4. 更新文档

在本文档的"支持的数据集"部分添加新数据集的说明。

## 性能优化

### 背压机制

为避免数据源产生速度过快导致队列积压，在 `execute()` 方法中添加了小延迟：

```python
time.sleep(0.01)  # 10ms延迟
```

可根据实际情况调整延迟时间：

- 如果发现队列积压严重，可适当增加延迟
- 如果处理速度足够快，可适当减少延迟

### 内存管理

- 采用逐个读取方式，避免一次性加载所有数据
- 每次只返回一组对话，保持内存占用稳定

## 统计信息示例

```
📊 样本 conv26 统计信息:
   - 总会话数: 3
   - 总对话数: 20
   - 总数据包: 10
   - 会话 1 (session_id=0): 8 个对话 (max_dialog_idx=7)
   - 会话 2 (session_id=1): 6 个对话 (max_dialog_idx=5)
   - 会话 3 (session_id=2): 6 个对话 (max_dialog_idx=5)
```

## 设计原则

1. **统一的初始化流程**：所有数据集使用相同的初始化步骤，避免分散逻辑
1. **统一的执行流程**：所有数据集使用相同的 `execute()` 方法，确保行为一致
1. **统一的输出格式**：所有数据集返回相同结构的数据包，便于下游处理
1. **简单的扩展方式**：添加新数据集只需创建 DataLoader 并注册，无需修改核心逻辑

## 注意事项

1. **修改代码时请同步更新本文档**
1. `BatchFunction` 的 `execute()` 会被循环调用，返回 `None` 时表示数据源耗尽
1. `dialog_ptr` 每次递增 2，对应一组问答对
1. 数据包序号 `packet_idx` 从 0 开始，用于进度跟踪
1. 背压延迟时间可根据实际性能需求调整

## 相关文件

- 实现文件：`libs/memory_source.py`
- Pipeline 文档：`mem_docs/Pipeline_README.md`
- 数据加载器：`sage.data.locomo.dataloader.LocomoDataLoader`
