# Task 6: 测试和验证

## 目标

验证重构后的 `sage bench` CLI 所有命令正常工作。

## 测试清单

### 1. 帮助信息测试

```bash
# 顶层帮助
sage bench --help
# 预期: 显示 agent, control-plane 等子命令，以及 run/eval/train 快捷方式

# Agent 帮助
sage bench agent --help
# 预期: 显示 paper1, paper2, list 子命令

# Paper 1 帮助
sage bench agent paper1 --help
# 预期: 显示 run, eval, train, list, figures, tables, llm 命令

# Paper 2 帮助
sage bench agent paper2 --help
# 预期: 显示 status 命令

# Control Plane 帮助
sage bench control-plane --help
# 预期: 显示 run, compare, sweep 等命令
```

### 2. Paper 1 命令测试

```bash
# 运行实验 (完整路径)
sage bench agent paper1 run --help
sage bench agent paper1 run --quick --skip-llm  # 实际运行需要环境

# 评测
sage bench agent paper1 eval --help

# 训练
sage bench agent paper1 train --help
sage bench agent paper1 train --dry-run

# 列出资源
sage bench agent paper1 list experiments
sage bench agent paper1 list datasets
sage bench agent paper1 list methods

# 图表和表格
sage bench agent paper1 figures --help
sage bench agent paper1 tables --help

# LLM 服务
sage bench agent paper1 llm status
sage bench agent paper1 llm start --help
sage bench agent paper1 llm stop --help
```

### 3. 快捷方式测试

```bash
# 快捷方式应等同于 paper1 命令
sage bench run --help
sage bench eval --help
sage bench train --help
sage bench list experiments
sage bench figures --help
sage bench tables --help
```

### 4. Agent list 命令测试

```bash
sage bench agent list
# 预期: 显示 paper1, paper2 的表格
```

### 5. Paper 2 占位测试

```bash
sage bench agent paper2
# 预期: 显示 Coming Soon 信息

sage bench agent paper2 status
# 预期: 显示实现状态表格
```

### 6. Control Plane 测试

```bash
sage bench control-plane run --help
sage bench cp run --help  # 别名
```

### 7. 别名测试

```bash
# paper1 别名 (如果保留)
sage bench paper1 run --help  # 应该能用，隐藏命令

# cp 别名
sage bench cp --help
```

## 错误场景测试

```bash
# 无效命令
sage bench invalid
# 预期: 错误提示 + 帮助信息

# 无效选项
sage bench agent paper1 run --invalid-option
# 预期: 错误提示

# 缺少必需参数 (如果有)
sage bench agent paper1 eval --dataset
# 预期: 提示缺少值
```

## 自动化测试 (可选)

创建测试文件 `packages/sage-cli/tests/test_bench_cli.py`:

```python
import pytest
from typer.testing import CliRunner
from sage.cli.commands.apps.bench import app

runner = CliRunner()

def test_bench_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "agent" in result.output
    assert "control-plane" in result.output

def test_agent_help():
    result = runner.invoke(app, ["agent", "--help"])
    assert result.exit_code == 0
    assert "paper1" in result.output
    assert "paper2" in result.output

def test_paper1_help():
    result = runner.invoke(app, ["agent", "paper1", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "eval" in result.output

def test_agent_list():
    result = runner.invoke(app, ["agent", "list"])
    assert result.exit_code == 0
    assert "paper1" in result.output

def test_paper2_info():
    result = runner.invoke(app, ["agent", "paper2"])
    assert result.exit_code == 0
    assert "SAGE-Agent" in result.output or "Coming" in result.output
```

## 验收标准

- [ ] 所有帮助命令正确显示
- [ ] Paper 1 所有命令可访问 (完整路径和快捷方式)
- [ ] Agent list 显示所有 papers
- [ ] Paper 2 显示占位信息
- [ ] Control Plane 命令不受影响
- [ ] 无 Python 错误或异常
- [ ] 帮助文本清晰准确
