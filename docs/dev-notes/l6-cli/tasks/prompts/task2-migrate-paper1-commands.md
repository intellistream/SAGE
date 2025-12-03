# Task 2: 迁移 Paper 1 命令到 paper1_app

## 目标

将 `bench.py` 中现有的 Agent Benchmark 命令从 `agent_app` 迁移到 `paper1_app`。

## 需要迁移的命令

| 原装饰器 | 新装饰器 | 命令 |
|---------|---------|------|
| `@agent_app.command("run")` | `@paper1_app.command("run")` | 运行实验 |
| `@agent_app.command("eval")` | `@paper1_app.command("eval")` | 工具选择评测 |
| `@agent_app.command("train")` | `@paper1_app.command("train")` | 训练方法对比 |
| `@agent_app.command("list")` | `@paper1_app.command("list")` | 列出资源 |
| `@agent_app.command("figures")` | `@paper1_app.command("figures")` | 生成图表 |
| `@agent_app.command("tables")` | `@paper1_app.command("tables")` | 生成表格 |
| `agent_app.add_typer(llm_app)` | `paper1_app.add_typer(llm_app)` | LLM 服务管理 |

## 保留快捷方式

顶层 `app` 的快捷命令保持不变，仍然映射到 Paper 1：

```python
@app.command("run")
def run_default(...):
    """快捷方式：等同于 sage bench agent paper1 run"""
    _run_agent_experiments(...)
```

## 修改模式

**Before**:
```python
@agent_app.command("run")
@app.command("run")
def run_experiments(...):
    ...
```

**After**:
```python
@paper1_app.command("run")
@app.command("run")  # 保留顶层快捷方式
def run_experiments(...):
    ...
```

## 文件位置

`/home/shuhao/SAGE/packages/sage-cli/src/sage/cli/commands/apps/bench.py`

## 验证命令

```bash
# Paper 1 命令
sage bench agent paper1 run --help
sage bench agent paper1 eval --help
sage bench agent paper1 llm status

# 快捷方式仍有效
sage bench run --help
sage bench eval --help
```

## 注意事项

- LLM 子命令组需要从 `agent_app` 移到 `paper1_app`
- 确保 `_run_agent_experiments` 等内部函数不变
- 更新相关 docstring 中的命令示例
