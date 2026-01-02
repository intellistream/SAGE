# Finetune 任务持久化 - Studio 重启后继续训练

## 问题描述

**用户问题**：

> "我刚刚已经启动了一个微调任务，但是 studio 重启了，这个微调任务还会继续执行吗？"

**原始实现的问题**：

```python
# ❌ 旧实现：使用 daemon 线程
thread = threading.Thread(target=self._train_worker, args=(task_id,))
thread.daemon = True  # 主进程退出时，线程被强制终止
thread.start()
```

**问题**：

- 微调任务运行在 Python 后台线程中
- `daemon=True` 意味着当 Studio 后端进程退出时，所有 daemon 线程会被强制杀死
- **Studio 重启 = 后端进程退出 = 微调任务被终止** ❌

## 解决方案

### 架构改进

将微调任务从 **后台线程** 改为 **独立进程**：

```
旧架构：
┌─────────────────────────────────┐
│  Studio Backend (FastAPI)      │
│  ├─ API Thread                  │
│  ├─ Training Thread (daemon) ←──┼─ Studio 重启 → 线程被杀死 ❌
│  └─ ...                         │
└─────────────────────────────────┘

新架构：
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│  Studio Backend (FastAPI)      │     │  Independent Training Process │
│  ├─ API Thread                  │     │  (独立进程，脱离父进程)         │
│  ├─ Monitor Thread (监控)       │────→│  PID: 12345                  │
│  └─ ...                         │     │  执行: train.py               │
└─────────────────────────────────┘     └──────────────────────────────┘
                                                ↓
                                        Studio 重启 → 进程继续运行 ✅
```

### 关键技术点

#### 1. 使用独立进程

```python
# ✅ 新实现：启动独立进程
with open(log_file, "w") as f:
    process = subprocess.Popen(
        ["python", str(script_path)],
        stdout=f,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # 创建新的进程组，完全脱离父进程
    )

# 保存进程 ID 到任务配置
task.process_id = process.pid
```

**`start_new_session=True` 的作用**：

- 创建新的进程会话（session）
- 使子进程成为会话领导者（session leader）
- **父进程退出时，子进程不会收到 SIGHUP 信号**
- 子进程完全独立，可以继续运行

#### 2. 生成独立训练脚本

为每个任务动态生成 Python 脚本：

```python
def _create_training_script(self, task: FinetuneTask) -> Path:
    """创建独立的训练脚本"""
    script_path = Path(task.output_dir) / "train.py"

    script_content = f'''
from sage.tools.finetune import LoRATrainer, TrainingConfig

config = TrainingConfig(
    model_name="{task.model_name}",
    data_path=Path("{task.dataset_path}"),
    output_dir=Path("{task.output_dir}"),
    num_train_epochs={task.config.get("num_epochs", 3)},
    # ... 其他配置
)

trainer = LoRATrainer(config)
trainer.train()
print("Training completed successfully!")
'''

    with open(script_path, "w") as f:
        f.write(script_content)

    return script_path
```

**输出示例**：

```
~/.sage/studio_finetune/finetune_1732270800_0/
├── train.py          ← 自动生成的训练脚本
├── training.log      ← 训练日志
├── adapter_model.bin ← LoRA 权重
└── adapter_config.json
```

#### 3. 进程状态持久化

在任务数据中保存进程 ID：

```python
@dataclass
class FinetuneTask:
    # ... 其他字段
    process_id: int | None = None  # 新增：进程 ID

def to_dict(self) -> dict[str, Any]:
    return {
        # ... 其他字段
        "process_id": self.process_id,  # 保存到 JSON
    }
```

**任务文件示例** (`~/.sage/studio_finetune/tasks.json`)：

```json
{
  "tasks": [
    {
      "task_id": "finetune_1732270800_0",
      "status": "training",
      "process_id": 12345,  ← 保存的进程 ID
      "model_name": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
      // ... 其他信息
    }
  ]
}
```

#### 4. Studio 重启后自动恢复

```python
def _recover_running_tasks(self):
    """恢复 Studio 重启前正在运行的任务"""
    for task_id, task in self.tasks.items():
        # 检查状态为 training/preparing 的任务
        if task.status in (FinetuneStatus.TRAINING, FinetuneStatus.PREPARING):
            if task.process_id and self._is_process_running(task.process_id):
                # 进程还在运行！恢复监控
                print(f"✅ 恢复任务 {task_id}，进程 PID={task.process_id}")
                self.active_task_id = task_id

                # 启动监控线程
                thread = threading.Thread(target=self._monitor_process, args=(task_id,))
                thread.daemon = True
                thread.start()
            else:
                # 进程已停止（异常情况）
                print(f"❌ 任务 {task_id} 进程已停止，标记为失败")
                self.update_task_status(
                    task_id,
                    FinetuneStatus.FAILED,
                    error="Training process terminated unexpectedly",
                )

def _is_process_running(self, pid: int) -> bool:
    """检查进程是否还在运行"""
    try:
        os.kill(pid, 0)  # 信号 0：只检查进程是否存在，不发送信号
        return True
    except OSError:
        return False
```

#### 5. 进程监控

使用监控线程定期检查进程状态和日志：

```python
def _monitor_process(self, task_id: str):
    """监控独立进程的状态"""
    log_file = Path(task.output_dir) / "training.log"
    last_position = 0

    while self._is_process_running(task.process_id):
        # 读取新的日志内容
        if log_file.exists():
            with open(log_file) as f:
                f.seek(last_position)
                new_logs = f.read()
                last_position = f.tell()

                # 解析进度信息
                if "epoch" in line.lower():
                    # 更新进度条
                    self.update_task_status(task_id, progress=...)

        time.sleep(2)  # 每 2 秒检查一次

    # 进程结束，检查是否成功
    if "training completed" in log_content:
        self.update_task_status(task_id, FinetuneStatus.COMPLETED)
    else:
        self.update_task_status(task_id, FinetuneStatus.FAILED)
```

## 完整流程

### 场景 1：正常训练（无重启）

```
1. 用户点击 "开始微调"
   ↓
2. finetune_manager.start_training(task_id)
   ↓
3. 生成 train.py 脚本
   ↓
4. 启动独立进程: subprocess.Popen()
   ↓
5. 保存进程 PID 到 tasks.json
   ↓
6. 启动监控线程，定期读取 training.log
   ↓
7. 训练完成，进程退出
   ↓
8. 监控线程检测到进程结束，更新状态为 "completed"
```

### 场景 2：训练中重启 Studio（关键！）

```
1. 训练进程运行中 (PID=12345, 状态=training)
   ↓
2. 用户执行 sage studio restart
   ↓
3. Studio 后端进程退出
   ├─ 监控线程被杀死 ✅（没关系，daemon 线程）
   ├─ API 服务停止 ✅
   └─ 训练进程继续运行！✅（独立进程，start_new_session=True）
   ↓
4. Studio 后端重新启动
   ↓
5. FinetuneManager.__init__()
   ├─ 加载 tasks.json
   ├─ 发现任务 status=training, process_id=12345
   └─ 调用 _recover_running_tasks()
   ↓
6. _recover_running_tasks()
   ├─ 检查进程 12345 是否还在运行
   ├─ os.kill(12345, 0) → True ✅
   ├─ 重新启动监控线程
   └─ 继续读取 training.log
   ↓
7. 训练正常完成！✅
```

### 场景 3：异常中断（机器重启）

```
1. 训练进程运行中 (PID=12345)
   ↓
2. 机器重启或崩溃
   ↓
3. 所有进程被杀死（包括训练进程）
   ↓
4. Studio 重新启动
   ↓
5. _recover_running_tasks()
   ├─ 检查进程 12345 是否还在运行
   ├─ os.kill(12345, 0) → OSError（进程不存在）
   └─ 标记任务为 FAILED
   ↓
6. 用户看到任务状态：失败 ❌
   ├─ 错误信息："Training process terminated unexpectedly"
   └─ 可以选择重新训练
```

## 用户体验

### 启动训练

```bash
# 在 Finetune 页面点击 "开始微调"
```

**后台执行**：

```bash
# Studio 后端创建训练脚本
$ cat ~/.sage/studio_finetune/finetune_1732270800_0/train.py

# 启动独立进程
$ python ~/.sage/studio_finetune/finetune_1732270800_0/train.py \
  > ~/.sage/studio_finetune/finetune_1732270800_0/training.log 2>&1 &
[1] 12345  ← 进程 ID

# 监控日志
$ tail -f ~/.sage/studio_finetune/finetune_1732270800_0/training.log
```

### Studio 重启期间

```bash
# 用户在终端执行
$ sage studio restart
🔄 重启 SAGE Studio...
✅ 后端API已停止
🧹 清理前端构建缓存...
✅ 缓存清理完成
正在启动后端API...
✅ 后端API启动成功

# 后台：训练进程继续运行（用户无感知）
$ ps aux | grep train.py
user  12345  ... python ...train.py  ← 进程仍在运行！

# FinetuneManager 自动恢复
[FinetuneManager] ✅ 恢复任务 finetune_1732270800_0，进程 PID=12345
```

### 前端显示

在 Finetune 页面，任务状态持续更新：

```
┌────────────────────────────────────────────────────┐
│ 任务 ID: finetune_1732270800_0                     │
│ 状态: 训练中 🔄                                     │
│ 进度: 45% [████████████░░░░░░░░░░░░░░]            │
│ Epoch: 2/3                                         │
│                                                    │
│ 最新日志:                                           │
│ [17:30:15] Epoch 2/3, Step 150/300               │
│ [17:30:17] Loss: 0.234                           │
│ [17:30:19] Epoch 2/3, Step 155/300               │
│                                                    │
│ ⚠️ Studio 刚刚重启，训练进程仍在运行中...           │
└────────────────────────────────────────────────────┘
```

**关键特点**：

- ✅ 进度条继续更新
- ✅ 日志继续追加
- ✅ 用户无需任何操作
- ✅ Studio 重启对训练无影响

## 验证方法

### 测试 1：启动训练并检查进程

```bash
# 1. 在 Finetune 页面启动训练
# 观察任务状态变为 "训练中"

# 2. 在终端检查进程
ps aux | grep train.py
# 应该看到独立的 Python 进程

# 3. 检查日志文件
tail -f ~/.sage/studio_finetune/finetune_*/training.log
# 应该看到训练日志实时输出
```

### 测试 2：重启 Studio

```bash
# 1. 确认训练进程正在运行
ps aux | grep train.py
# 记录 PID，例如 12345

# 2. 重启 Studio
sage studio restart

# 3. 再次检查训练进程
ps aux | grep train.py
# 应该看到相同的 PID 仍在运行！

# 4. 检查 Finetune 页面
# 任务状态应该仍然是 "训练中"
# 进度条继续更新
```

### 测试 3：查看任务恢复日志

```bash
# 查看 Studio 后端日志
tail -f ~/.sage/studio.log | grep Finetune

# 应该看到类似输出：
# [FinetuneManager] 恢复任务 finetune_1732270800_0，进程 PID=12345
```

## 技术优势

### 对比旧实现

| 特性        | 旧实现（线程）  | 新实现（进程）    |
| ----------- | --------------- | ----------------- |
| Studio 重启 | ❌ 任务被杀死   | ✅ 任务继续运行   |
| 进度恢复    | ❌ 无法恢复     | ✅ 自动恢复监控   |
| 日志持久化  | ❌ 丢失         | ✅ 完整保存到文件 |
| 独立性      | ❌ 依赖父进程   | ✅ 完全独立       |
| 调试便利性  | ❌ 难以单独调试 | ✅ 可直接运行脚本 |
| 资源隔离    | ❌ 共享内存     | ✅ 独立内存空间   |

### 额外好处

1. **可调试性**：

   ```bash
   # 可以直接运行生成的脚本进行调试
   python ~/.sage/studio_finetune/finetune_*/train.py
   ```

1. **可监控性**：

   ```bash
   # 可以直接查看日志
   tail -f ~/.sage/studio_finetune/finetune_*/training.log

   # 可以用 htop/top 监控进程资源使用
   htop -p 12345
   ```

1. **可中断性**：

   ```bash
   # 如果需要手动停止训练
   kill 12345

   # FinetuneManager 会检测到进程终止并更新状态
   ```

1. **可恢复性**：

   - 即使 Studio 多次重启
   - 只要机器不重启，训练就会继续
   - 自动恢复监控和进度追踪

## 未来改进

### 1. 支持暂停/恢复训练

```python
def pause_training(self, task_id: str):
    """暂停训练（发送 SIGSTOP）"""
    task = self.tasks.get(task_id)
    if task and task.process_id:
        os.kill(task.process_id, signal.SIGSTOP)
        task.status = FinetuneStatus.PAUSED

def resume_training(self, task_id: str):
    """恢复训练（发送 SIGCONT）"""
    task = self.tasks.get(task_id)
    if task and task.process_id:
        os.kill(task.process_id, signal.SIGCONT)
        task.status = FinetuneStatus.TRAINING
```

### 2. 支持分布式训练

```python
# 在多个 GPU 或多台机器上运行
process = subprocess.Popen(
    ["torchrun", "--nproc_per_node=4", str(script_path)],
    # ... 其他参数
)
```

### 3. 检查点（Checkpoint）恢复

```python
# 如果训练进程意外终止，从最后的检查点恢复
config = TrainingConfig(
    # ... 其他参数
    resume_from_checkpoint=True,
)
```

### 4. 训练资源限制

```python
# 限制 GPU 使用
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 只使用 GPU 0

# 限制内存使用（通过 cgroup）
subprocess.Popen(
    ["cgexec", "-g", "memory:finetune", "python", "train.py"],
    # ...
)
```

## 常见问题

### Q: 如果机器重启了怎么办？

A: 机器重启会导致所有进程终止，包括训练进程。Studio 重启后会检测到进程不存在，自动将任务标记为 "失败"。用户可以选择重新开始训练。

未来可以通过**检查点恢复**功能，从最后保存的检查点继续训练。

### Q: 如何查看训练进程的资源使用？

A:

```bash
# 1. 获取进程 ID
cat ~/.sage/studio_finetune/tasks.json | grep process_id

# 2. 监控资源使用
htop -p <PID>
# 或
nvidia-smi  # 查看 GPU 使用
```

### Q: 训练日志在哪里？

A: 每个任务的日志保存在：

```
~/.sage/studio_finetune/{task_id}/training.log
```

可以用 `tail -f` 实时查看。

### Q: 如何手动停止训练？

A:

```bash
# 方法 1: 通过前端（即将支持）
# 在 Finetune 页面点击 "取消" 按钮

# 方法 2: 手动杀死进程
kill <PID>

# FinetuneManager 会检测到进程终止并更新状态
```

## 总结

**核心改进**：

- ✅ 训练进程完全独立于 Studio 后端
- ✅ Studio 重启不影响训练
- ✅ 自动恢复监控和进度追踪
- ✅ 日志持久化到文件
- ✅ 可独立调试和监控

**用户体验**：

- 🎯 启动训练后，可以随意重启 Studio
- 🎯 无需担心意外中断
- 🎯 训练进度自动保存和恢复
- 🎯 可以关闭浏览器，训练继续进行

**技术保障**：

- 🔒 使用独立进程而非线程
- 🔒 `start_new_session=True` 确保进程独立
- 🔒 进程 ID 持久化到 JSON
- 🔒 重启后自动检测并恢复监控
