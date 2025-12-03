# SAGE Bench CLI 重构任务

## 背景

当前 `sage bench` CLI 结构不合理：
- `sage bench agent` 直接等同于 Paper 1，但实际上 Agent 相关的 benchmark 包含多篇论文
- Paper 2 (SAGE-Agent 方法) 也属于 Agent Benchmark，但没有入口

## 目标结构

```
sage bench
├── agent                              # Agent 相关所有 Benchmarks
│   ├── paper1                         # Paper 1: SAGE-Bench 评测框架
│   │   ├── run --quick/--section/--exp
│   │   ├── eval --dataset
│   │   ├── train --methods
│   │   ├── llm start/stop/status
│   │   ├── list experiments/datasets/methods
│   │   ├── figures
│   │   └── tables
│   ├── paper2                         # Paper 2: SAGE-Agent 方法 (预留)
│   │   └── ...
│   └── list                           # 列出所有 agent papers
├── control-plane (cp)                 # Control Plane Benchmarks
│   ├── run/compare/sweep/experiment
│   └── visualize/config/validate
├── rag                                # RAG Benchmarks (预留)
├── memory                             # Memory Benchmarks (预留)
└── run/eval/train                     # 快捷方式 → agent paper1 (兼容)
```

## 现有资源

- `benchmark_agent/` - Agent 评测模块
  - `scripts/experiments/run_paper1_experiments.py` - Paper 1 实验入口
  - `scripts/experiments/exp_training_comparison.py` - 训练方法对比 (Paper 1 Section 5.5)
  - `adapter_registry.py` - 定义了 Paper 1 和 Paper 2 的方法
- `benchmark_control_plane/` - Control Plane 评测 (已有独立 CLI)
- `benchmark_rag/`, `benchmark_memory/` 等 - 其他 benchmark 模块

---

## 任务拆分

### Task 1: 重构 bench.py 基础结构

**文件**: `packages/sage-cli/src/sage/cli/commands/apps/bench.py`

**目标**:
- 将 `agent_app` 改为 Agent Benchmark 的总入口
- 创建 `paper1_app` 作为 Paper 1 的子命令
- 保持向后兼容：`sage bench run` 仍映射到 `sage bench agent paper1 run`

**修改点**:
1. 创建新的 Typer 应用层级:
   ```python
   app = typer.Typer(...)  # sage bench
   agent_app = typer.Typer(...)  # sage bench agent
   paper1_app = typer.Typer(...)  # sage bench agent paper1
   ```

2. 将现有 Agent Benchmark 命令移到 `paper1_app` 下

3. 在 `agent_app` 添加:
   - `list` 命令列出所有 papers
   - 预留 `paper2` 占位

---

### Task 2: 迁移 Paper 1 命令到 paper1_app

**目标**: 将现有 `@agent_app.command()` 装饰的命令改为 `@paper1_app.command()`

**涉及命令**:
- `run` - 运行实验
- `eval` - 工具选择评测
- `train` - 训练方法对比
- `list` - 列出资源
- `figures` - 生成图表
- `tables` - 生成表格
- `llm` 子命令组 (start/stop/status)

**注意**: 保留顶层快捷方式 `@app.command("run")` 等

---

### Task 3: 添加 agent list 命令

**目标**: 在 `agent_app` 添加 `list` 命令，列出所有可用的 Agent Benchmark papers

```bash
$ sage bench agent list
Available Agent Benchmarks:
  paper1    SAGE-Bench - Agent 能力评测框架 (工具选择/规划/时机判断)
  paper2    SAGE-Agent - Streaming Adaptive Learning (Coming Soon)
```

---

### Task 4: 添加 Paper 2 占位

**目标**: 预留 Paper 2 入口，显示 "Coming Soon" 或基本信息

```python
paper2_app = typer.Typer(
    name="paper2",
    help="📝 Paper 2: SAGE-Agent - Streaming Adaptive Learning (Coming Soon)",
)

@paper2_app.callback(invoke_without_command=True)
def paper2_info():
    console.print("[yellow]Paper 2 实验尚未完成，敬请期待...[/yellow]")
```

---

### Task 5: 更新文档和帮助文本

**文件**:
- `bench.py` 模块文档字符串
- 各命令的 help 文本
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/README.md`

**更新内容**:
- CLI 使用示例
- 命令层级说明

---

### Task 6: 测试和验证

**验证命令**:
```bash
sage bench --help
sage bench agent --help
sage bench agent list
sage bench agent paper1 --help
sage bench agent paper1 run --quick
sage bench agent paper2
sage bench run --help  # 应显示与 paper1 run 相同
sage bench control-plane --help
```

---

## 提示词模板

以下是每个任务的独立提示词文件，可以分别执行：

| 任务 | 文件 | 描述 | 预计时间 |
|------|------|------|----------|
| Task 1 | [task1-bench-structure.md](prompts/task1-bench-structure.md) | 重构基础结构 | 15 min |
| Task 2 | [task2-migrate-paper1-commands.md](prompts/task2-migrate-paper1-commands.md) | 迁移 Paper 1 命令 | 20 min |
| Task 3 | [task3-agent-list-command.md](prompts/task3-agent-list-command.md) | 添加 agent list | 10 min |
| Task 4 | [task4-paper2-placeholder.md](prompts/task4-paper2-placeholder.md) | Paper 2 占位 | 10 min |
| Task 5 | [task5-update-docs.md](prompts/task5-update-docs.md) | 更新文档 | 15 min |
| Task 6 | [task6-testing.md](prompts/task6-testing.md) | 测试验证 | 15 min |

**总预计时间**: ~1.5 小时

## 执行顺序

1. **Task 1** → 建立基础结构 (必须先做)
2. **Task 2** → 迁移命令 (依赖 Task 1)
3. **Task 3 & 4** → 可并行执行
4. **Task 5** → 更新文档
5. **Task 6** → 最终测试

## 快速开始

复制任意任务的提示词到 Copilot，让它帮你完成：

```
请帮我完成 /home/shuhao/SAGE/docs/dev-notes/tasks/prompts/task1-bench-structure.md 中描述的任务
```
