# Task 5: 更新文档和帮助文本

## 目标

更新所有相关的文档字符串和帮助文本，反映新的命令层级结构。

## 需要更新的内容

### 1. bench.py 模块文档

```python
"""
SAGE Bench CLI - 统一 Benchmark 命令入口

提供所有 Benchmark 的统一子命令：

命令结构:
    sage bench agent paper1 run --quick    # Paper 1 Agent Benchmark
    sage bench agent paper2                # Paper 2 (Coming Soon)
    sage bench control-plane run ...       # Control Plane Benchmark

快捷方式 (向后兼容):
    sage bench run --quick                 # 等同于 sage bench agent paper1 run
    sage bench eval --dataset sage         # 等同于 sage bench agent paper1 eval

Benchmark 类型:
    - agent: Agent 能力评测 (工具选择/规划/时机判断)
    - control-plane: 调度策略评测 (LLM/Hybrid)
    - rag: RAG 评测 (预留)
    - memory: 内存管理评测 (预留)
"""
```

### 2. Typer 应用帮助文本

```python
app = typer.Typer(
    name="bench",
    help="🧪 Benchmark - 统一评测入口 (Agent, Control Plane, RAG, ...)",
    no_args_is_help=True,
)

agent_app = typer.Typer(
    name="agent",
    help="🤝 Agent Benchmarks - 多篇论文的 Agent 能力评测",
    no_args_is_help=True,
)

paper1_app = typer.Typer(
    name="paper1",
    help="📊 Paper 1: SAGE-Bench - 工具选择/规划/时机判断评测框架",
    no_args_is_help=True,
)

paper2_app = typer.Typer(
    name="paper2",
    help="📝 Paper 2: SAGE-Agent - Streaming Adaptive Learning",
    no_args_is_help=False,
)
```

### 3. 命令示例更新

更新所有命令的 docstring 中的示例：

```python
def run_experiments(...):
    """
    运行 Paper 1 Benchmark 实验

    示例:
        sage bench agent paper1 run --quick         # 快速测试
        sage bench agent paper1 run --section 5.2   # 主要评测
        sage bench run --quick                      # 快捷方式
    """
```

### 4. README 更新

文件: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/README.md`

添加新的 CLI 使用说明：

```markdown
## CLI 使用

### 完整命令路径
```bash
sage bench agent paper1 run --quick
sage bench agent paper1 eval --dataset sage
sage bench agent paper1 train --dry-run
sage bench agent paper1 llm status
```

### 快捷方式 (向后兼容)
```bash
sage bench run --quick
sage bench eval --dataset sage
```

### 其他 Benchmark
```bash
sage bench agent list              # 列出所有 Agent papers
sage bench agent paper2            # Paper 2 状态
sage bench control-plane --help    # Control Plane Benchmark
```
```

## 文件位置

1. `/home/shuhao/SAGE/packages/sage-cli/src/sage/cli/commands/apps/bench.py`
2. `/home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/README.md`

## 验证

```bash
sage bench --help
sage bench agent --help
sage bench agent paper1 --help
sage bench agent paper1 run --help
```

确保所有帮助文本清晰、一致、准确。
