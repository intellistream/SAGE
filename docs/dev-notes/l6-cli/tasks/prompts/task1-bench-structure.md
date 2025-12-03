# Task 1: 重构 sage bench CLI 基础结构

## 目标

重构 `packages/sage-cli/src/sage/cli/commands/apps/bench.py`，建立正确的命令层级：

```
sage bench
├── agent                    # Agent Benchmarks 总入口
│   ├── paper1              # Paper 1 实验
│   ├── paper2              # Paper 2 实验 (预留)
│   └── list                # 列出所有 papers
├── control-plane           # Control Plane Benchmark
└── run/eval/train          # 快捷方式 (兼容)
```

## 当前问题

当前 `agent_app` 直接包含 Paper 1 的所有命令，没有区分不同 paper。

## 修改要求

1. **创建三层 Typer 应用**:
   ```python
   # 顶层
   app = typer.Typer(name="bench", help="🧪 Benchmark - 统一入口")

   # Agent 层
   agent_app = typer.Typer(name="agent", help="🤝 Agent Benchmarks")

   # Paper 1 层
   paper1_app = typer.Typer(name="paper1", help="📊 Paper 1: SAGE-Bench 评测框架")

   # Paper 2 层 (预留)
   paper2_app = typer.Typer(name="paper2", help="📝 Paper 2: SAGE-Agent (Coming Soon)")
   ```

2. **注册层级关系**:
   ```python
   agent_app.add_typer(paper1_app, name="paper1")
   agent_app.add_typer(paper2_app, name="paper2")
   app.add_typer(agent_app, name="agent", rich_help_panel="Benchmarks")
   ```

3. **保持快捷方式**:
   - `sage bench run` → `sage bench agent paper1 run`
   - `sage bench eval` → `sage bench agent paper1 eval`
   - 等等

4. **Control Plane Benchmark 保持不变**

## 文件位置

`/home/shuhao/SAGE/packages/sage-cli/src/sage/cli/commands/apps/bench.py`

## 验证命令

```bash
sage bench --help
sage bench agent --help
sage bench agent paper1 --help
```

## 注意事项

- 不要删除任何现有功能
- 确保所有 import 正确
- 保持错误处理逻辑
