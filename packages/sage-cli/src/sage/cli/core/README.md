# SAGE CLI Core Module

SAGE CLI 核心模块提供了一套统一的基础设施，用于解耦和标准化各个CLI命令的共有逻辑。

## 📁 模块结构

```
sage/cli/core/
├── __init__.py          # 模块入口，导出主要接口
├── base.py              # 基础命令类和装饰器
├── output.py            # 统一输出格式化
├── ssh.py               # SSH连接和远程执行
├── config.py            # 配置验证和管理
├── exceptions.py        # 自定义异常类
├── utils.py             # 通用工具函数
├── validation.py        # 输入验证功能
└── refactor_example.py  # 重构示例代码
```

## 🎯 主要功能

### 1. 基础命令类 (base.py)

提供了三个主要的基类：

- **BaseCommand**: 所有CLI命令的基类
- **ServiceCommand**: 需要连接服务的命令基类
- **RemoteCommand**: 需要远程执行的命令基类
- **JobManagerCommand**: JobManager相关命令的基类

#### 使用示例：

```python
from sage.cli.core import BaseCommand, cli_command


class DoctorCommand(BaseCommand):
    def execute(self):
        self.print_section_header("🔍 System Diagnosis")
        self.formatter.print_success("All systems operational")


@app.command("doctor")
@cli_command(require_config=False)
def doctor():
    cmd = DoctorCommand()
    cmd.execute()
```

### 2. 统一输出格式化 (output.py)

提供了一致的输出格式和颜色支持：

```python
from sage.cli.core import OutputFormatter, print_status

formatter = OutputFormatter(colors=True, format_type="table")
formatter.print_success("Operation completed")
formatter.print_error("Something went wrong")
formatter.print_data(data, headers=["Name", "Status"])

# 或使用便捷函数
print_status("success", "Task completed successfully")
```

### 3. SSH连接管理 (ssh.py)

统一的SSH连接和远程命令执行：

```python
from sage.cli.core.ssh import SSHConfig, SSHManager

ssh_config = SSHConfig(user="sage", key_path="~/.ssh/id_rsa", connect_timeout=10)

ssh_manager = SSHManager(ssh_config)
result = ssh_manager.execute_command("worker1", 22, "ps aux")
```

### 4. 配置验证 (config.py)

标准化的配置文件加载和验证：

```python
from sage.cli.core.config import load_and_validate_config

config = load_and_validate_config("~/.sage/config.yaml")
head_config = config.get("head", {})
```

### 5. 输入验证 (validation.py)

通用的输入验证功能：

```python
from sage.cli.core import validate_host, validate_port, ValidationError

try:
    host = validate_host("192.168.1.100")
    port = validate_port(22)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### 6. 自定义异常 (exceptions.py)

统一的异常处理：

```python
from sage.cli.core import CLIException, ConfigurationError, ConnectionError

try:
    # some operation
    pass
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    exit(e.exit_code)
```

## 🔄 重构指南

### 重构现有命令的步骤：

1. **确定命令类型**：

   - 简单命令 → 使用 `BaseCommand`
   - 需要连接服务 → 使用 `ServiceCommand`
   - 需要远程操作 → 使用 `RemoteCommand`
   - JobManager操作 → 使用 `JobManagerCommand`

1. **提取共有逻辑**：

   - 配置加载 → 使用基类的配置功能
   - 输出格式化 → 使用 `OutputFormatter`
   - SSH连接 → 使用 `SSHManager`
   - 验证逻辑 → 使用 `validation` 模块

1. **应用装饰器**：

   ```python
   @cli_command(require_config=True)
   def command_function():
       pass
   ```

### 重构前后对比：

#### 重构前 (deploy.py):

```python
def load_config():
    config_file = Path.home() / ".sage" / "config.yaml"
    if not config_file.exists():
        typer.echo(f"❌ Config file not found: {config_file}")
        raise typer.Exit(1)
    # ... 复杂的配置解析逻辑


@app.command("start")
def start_system():
    config = load_config()
    typer.echo("🚀 Starting SAGE system...")
    # ... 启动逻辑
```

#### 重构后:

```python
from sage.cli.core import BaseCommand, cli_command


class DeployStartCommand(BaseCommand):
    def execute(self):
        self.validate_config_exists()
        self.formatter.print_info("Starting SAGE system...")
        # ... 启动逻辑使用 self.config


@app.command("start")
@cli_command()
def start_system():
    cmd = DeployStartCommand()
    cmd.execute()
```

## 🌟 核心优势

### 1. **代码复用**

- 消除重复的配置加载、错误处理、输出格式化代码
- 统一的SSH连接管理
- 标准化的验证逻辑

### 2. **一致性**

- 统一的错误消息格式
- 一致的配置文件结构
- 标准化的命令行选项

### 3. **可维护性**

- 集中的配置验证逻辑
- 统一的异常处理
- 清晰的模块分离

### 4. **可扩展性**

- 基于继承的命令架构
- 可插拔的输出格式化器
- 灵活的配置验证器

## 📝 最佳实践

### 1. 命令设计

```python
# ✅ 推荐：使用基类
class MyCommand(BaseCommand):
    def execute(self, param1, param2):
        self.validate_config_exists()
        # 业务逻辑

# ❌ 不推荐：直接在函数中处理
def my_command(param1, param2):
    # 重复的配置加载和错误处理
```

### 2. 错误处理

```python
# ✅ 推荐：使用自定义异常
if not config_valid:
    raise ConfigurationError("Invalid configuration")

# ❌ 不推荐：直接退出
if not config_valid:
    typer.echo("❌ Invalid configuration")
    raise typer.Exit(1)
```

### 3. 输出格式化

```python
# ✅ 推荐：使用OutputFormatter
self.formatter.print_success("Operation completed")
self.formatter.print_data(results, headers)

# ❌ 不推荐：直接打印
print("✅ Operation completed")
print(tabulate(results, headers))
```

## 🔧 迁移步骤

1. **分析现有命令**：

   ```bash
   # 查看命令文件
   find packages/sage-cli/src/sage/cli/commands/ -name "*.py"
   ```

1. **确定重构优先级**：

   - 高重复度的命令优先
   - 核心功能命令优先
   - 复杂SSH操作命令优先

1. **逐步重构**：

   - 一次重构一个命令文件
   - 保持向后兼容性
   - 添加测试验证

1. **清理遗留代码**：

   - 移除重复的工具函数
   - 统一配置文件结构
   - 更新文档

## 📚 参考示例

查看 `refactor_example.py` 了解完整的重构示例，包括：

- 简单命令重构 (`DoctorCommand`)
- 服务连接命令重构 (`JobListCommand`)
- 远程命令重构 (`ClusterStatusCommand`)
- 装饰器使用示例
- 验证功能示例

通过使用这个核心模块，可以大大简化CLI命令的实现，提高代码质量和可维护性。
