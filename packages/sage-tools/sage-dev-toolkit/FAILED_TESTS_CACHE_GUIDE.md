# SAGE Test Failure Cache 使用指南

## 概述

SAGE 开发工具包现在支持测试失败缓存功能，可以自动保存失败的测试路径并提供 `--failed` 选项来重新运行这些失败的测试。

## 功能特性

- **自动缓存失败测试**: 每次运行测试时，自动将失败的测试路径保存到 `~/.sage/test_logs/failed_tests.json`
- **快速重新运行失败测试**: 使用 `sage-dev test --failed` 只运行之前失败的测试
- **智能路径解析**: 自动解析缓存的测试路径，即使项目结构发生变化
- **测试历史记录**: 保留最近 10 次测试运行的历史记录
- **缓存管理**: 提供清理缓存、查看状态等管理功能

## 基本用法

### 1. 正常运行测试（自动缓存失败测试）

```bash
# 运行所有测试
sage-dev test --mode all

# 运行差异测试
sage-dev test --mode diff

# 运行特定包的测试
sage-dev test --mode package --package sage-kernel
```

失败的测试会自动保存到缓存中。

### 2. 重新运行失败的测试

```bash
# 使用 --failed 选项
sage-dev test --failed

# 或者明确指定模式
sage-dev test --mode failed
```

### 3. 查看缓存状态

```bash
# 查看缓存状态
sage-dev test --cache-status

# 或者使用专门的缓存命令
sage-dev test-cache --action status
```

### 4. 清理缓存

```bash
# 清理失败测试缓存
sage-dev test --clear-cache

# 或者使用专门的缓存命令
sage-dev test-cache --action clear
```

### 5. 查看测试历史

```bash
# 查看最近 5 次测试运行历史
sage-dev test-cache --action history

# 查看更多历史记录
sage-dev test-cache --action history --limit 10
```

## 命令详解

### sage-dev test 新选项

| 选项 | 描述 |
|------|------|
| `--failed` | 只运行之前失败的测试 |
| `--clear-cache` | 清理失败测试缓存 |
| `--cache-status` | 显示缓存状态信息 |

### sage-dev test-cache 命令

专门用于管理测试失败缓存的命令：

```bash
sage-dev test-cache [OPTIONS]
```

**选项：**
- `--action`: 执行的操作 (status, clear, history)
- `--limit`: 历史记录显示数量 (默认 5)

**示例：**
```bash
# 查看缓存状态
sage-dev test-cache --action status

# 清理缓存
sage-dev test-cache --action clear

# 查看测试历史
sage-dev test-cache --action history --limit 10
```

## 工作流示例

### 典型的开发工作流

1. **开发新功能时**：
   ```bash
   # 运行相关测试
   sage-dev test --mode diff
   ```

2. **如果有测试失败**：
   ```bash
   # 修复代码后，重新运行失败的测试
   sage-dev test --failed
   ```

3. **查看当前状态**：
   ```bash
   # 检查是否还有失败的测试
   sage-dev test --cache-status
   ```

4. **所有测试通过后**：
   ```bash
   # 可选：清理缓存
   sage-dev test --clear-cache
   ```

### CI/CD 集成

在持续集成环境中，可以利用这个功能进行增量测试：

```bash
# 运行所有测试
sage-dev test --mode all

# 如果有失败，记录失败的测试
# 后续可以针对性地重新运行
sage-dev test --failed
```

## 缓存文件结构

缓存文件位于 `~/.sage/test_logs/failed_tests.json`，包含以下信息：

```json
{
  "last_updated": "2025-01-01T12:00:00",
  "failed_tests": [
    {
      "test_file": "packages/sage-kernel/tests/test_job.py",
      "error": "AssertionError: ...",
      "duration": 5.2,
      "log_file": "/path/to/log",
      "failed_at": "2025-01-01T12:00:00"
    }
  ],
  "last_run_summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "execution_time": 25.5,
    "timestamp": "2025-01-01T12:00:00",
    "mode": "diff"
  },
  "history": [...]
}
```

## 注意事项

1. **路径解析**: 缓存会尝试智能解析测试路径，但如果项目结构大幅变化，可能需要清理缓存
2. **缓存大小**: 历史记录最多保留 10 次运行，缓存文件不会无限增长
3. **跨分支**: 缓存在不同分支间共享，建议在切换分支后运行完整测试
4. **权限**: 确保对 `~/.sage/` 目录有写权限

## 高级用法

### 结合其他选项使用

```bash
# 并行运行失败的测试
sage-dev test --failed --workers 4

# 详细显示失败测试的结果
sage-dev test --failed --show-details

# 快速运行失败测试（遇到第一个错误就停止）
sage-dev test --failed --quick
```

### 编程接口

也可以在 Python 代码中直接使用缓存功能：

```python
from sage_dev_toolkit.tools.test_failure_cache import TestFailureCache

# 创建缓存实例
cache = TestFailureCache("/path/to/project")

# 查看失败的测试
failed_tests = cache.get_failed_test_paths()

# 获取详细信息
details = cache.get_failed_test_details()

# 清理缓存
cache.clear_cache()
```

## 故障排除

### 常见问题

1. **缓存文件不存在**：
   - 第一次使用时会自动创建
   - 确保有写权限

2. **失败测试无法找到**：
   - 检查项目结构是否改变
   - 使用 `--cache-status` 查看详情
   - 必要时清理缓存重新开始

3. **缓存数据异常**：
   - 使用 `--clear-cache` 清理缓存
   - 重新运行测试

### 调试信息

使用 `--verbose` 选项可以获得更多调试信息：

```bash
sage-dev test --failed --verbose
```

这个功能将大大提高开发效率，特别是在处理大型测试套件时！
