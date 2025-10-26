# C++扩展安装卡住问题修复

## 问题描述

在运行`./quickstart.sh`安装SAGE时，C++扩展安装阶段会卡住很久，看起来像是失败了，但实际上可能已经成功安装。日志文件的最后一行显示：

```
运行 'sage extensions status' 验证安装
```

用户不知道这是正常的还是程序卡住了。

## 根本原因

1. **输出缓冲问题**：Python的stdout和stderr可能被缓冲，导致最后的消息没有立即显示
1. **后台线程未清理**：构建进度显示的后台线程可能没有被正确清理
1. **超时机制不可靠**：`status`命令使用`signal.SIGALRM`进行超时控制，这在Windows上不可用，且在某些环境下可能失效

## 解决方案

### 1. 添加输出刷新

在关键位置添加`sys.stdout.flush()`和`sys.stderr.flush()`，确保所有输出立即显示：

```python
def _print_install_summary(success_count: int, total_count: int) -> None:
    import sys

    typer.echo(f"\n{Colors.BOLD}安装完成{Colors.RESET}")
    typer.echo(f"成功: {success_count}/{total_count}")

    if success_count == total_count:
        print_success("🎉 所有扩展安装成功！")
        typer.echo("\n运行 'sage extensions status' 验证安装")
    else:
        failures = total_count - success_count
        print_warning(f"⚠️ 部分扩展安装失败 ({failures}个)")

    # 确保所有输出都被刷新
    sys.stdout.flush()
    sys.stderr.flush()
```

### 2. 改进进度线程清理

增加线程等待超时时间，并添加输出刷新：

```python
finally:
    # 停止进度显示
    progress_state["running"] = False
    # 等待线程结束，但不要无限等待
    if progress_thread.is_alive():
        progress_thread.join(timeout=2.0)
    typer.echo()  # 换行

    # 确保输出被刷新
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
```

### 3. 使用跨平台的超时机制

将`status`命令中基于信号的超时机制替换为基于线程的超时机制：

**旧方案（有问题）**：

```python
import signal


def timeout_handler(signum, frame):
    raise TimeoutError("Module import timeout")


# 设置5秒超时
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)

try:
    __import__(module_name)
    signal.alarm(0)  # 取消超时
    print_success(f"{description} ✓")
    available_count += 1
except TimeoutError:
    signal.alarm(0)
    print_warning(f"{description} ✗")
```

**新方案（可靠）**：

```python
import threading
import queue

result_queue = queue.Queue()


def try_import():
    try:
        __import__(module_name)
        result_queue.put(("success", None))
    except Exception as e:
        result_queue.put(("error", e))


import_thread = threading.Thread(target=try_import, daemon=True)
import_thread.start()

# 等待5秒超时
import_thread.join(timeout=5.0)

if import_thread.is_alive():
    # 线程仍在运行，说明超时了
    print_warning(f"{description} ✗")
    typer.echo("  原因: 导入超时（可能存在初始化问题）")
else:
    # 检查结果
    try:
        status, error = result_queue.get_nowait()
        if status == "success":
            print_success(f"{description} ✓")
            available_count += 1
        else:
            print_warning(f"{description} ✗")
            typer.echo(f"  原因: {error}")
    except queue.Empty:
        print_warning(f"{description} ✗")
        typer.echo("  原因: 无法获取导入结果")
```

## 优势

### 旧方案的问题：

- ❌ `signal.SIGALRM`在Windows上不可用
- ❌ 在多线程环境中可能不可靠
- ❌ 信号处理可能被其他代码干扰

### 新方案的优势：

- ✅ 跨平台兼容（Linux、macOS、Windows）
- ✅ 在多线程环境中可靠工作
- ✅ 使用daemon线程，即使超时也不会阻止程序退出
- ✅ 显式的输出刷新确保消息立即显示

## 测试验证

### 测试1：status命令超时保护

```bash
# 应该在5秒内完成，不会卡住
timeout 10 sage extensions status
```

### 测试2：输出缓冲

```bash
# 输出应该立即显示，不会延迟
sage extensions status 2>&1 | cat
```

### 测试3：安装脚本集成

```bash
# 应该正常完成，不会卡住
./quickstart.sh --dev --yes
```

## 相关文件

- `packages/sage-tools/src/sage/tools/cli/commands/extensions.py` - 修复了输出缓冲和超时机制
- `tools/install/installation_table/main_installer.sh` - 调用扩展安装的脚本

## 建议

如果用户在安装过程中仍然遇到卡住的问题，可以：

1. **检查日志文件**：

   ```bash
   tail -f /home/shuhao/SAGE/.sage/logs/extensions/sage_db_build.log
   tail -f /home/shuhao/SAGE/.sage/logs/extensions/sage_flow_build.log
   ```

1. **手动测试扩展**：

   ```bash
   sage extensions status
   ```

1. **重新安装扩展**：

   ```bash
   sage extensions install all --force
   ```

1. **查看完整日志**：

   ```bash
   cat install.log
   ```

## 未来改进

1. 添加更详细的进度显示（显示正在编译哪个文件）
1. 添加估计剩余时间
1. 提供"详细模式"开关，允许用户选择查看完整编译输出
1. 在安装脚本中添加心跳检测，定期显示"仍在安装中..."消息
