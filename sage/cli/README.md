# SAGE CLI

SAGE统一命令行工具，提供作业管理和系统部署功能。

## 🚀 快速开始

### 安装依赖
```bash
python sage/cli/setup.py
```

### 基本使用
```bash
# 查看帮助
sage --help

# 启动系统
sage deploy start

# 列出作业
sage job list

# 查看作业详情
sage job show 1

# 运行脚本
sage job run your_script.py

# 停止系统
sage deploy stop
```

## 📋 命令结构

### 作业管理 (`sage job`)
- `list` - 列出所有作业
- `show <job>` - 显示作业详情  
- `run <script>` - 运行Python脚本
- `stop <job>` - 停止作业
- `continue <job>` - 继续作业
- `delete <job>` - 删除作业
- `status <job>` - 获取作业状态
- `cleanup` - 清理所有作业
- `health` - 健康检查
- `info` - 系统信息
- `monitor` - 实时监控所有作业
- `watch <job>` - 监控特定作业

### 系统部署 (`sage deploy`)
- `start` - 启动SAGE系统
- `stop` - 停止SAGE系统
- `restart` - 重启SAGE系统
- `status` - 显示系统状态
- `health` - 健康检查
- `monitor` - 实时监控系统

## 🔧 配置

配置文件位于 `~/.sage/config.yaml`:

```yaml
daemon:
  host: "127.0.0.1"
  port: 19001

output:
  format: "table"
  colors: true

monitor:
  refresh_interval: 5

jobmanager:
  timeout: 30
  retry_attempts: 3
```

## 🔄 迁移指南

### 从旧CLI迁移

原来的命令 | 新命令
---|---
`sage-jm list` | `sage job list`
`sage-jm show 1` | `sage job show 1`
`sage-jm stop 1` | `sage job stop 1`
`sage-jm health` | `sage job health`
`sage-deploy start` | `sage deploy start`

### 向后兼容
- `sage-jm` 命令仍然可用，会自动重定向到新CLI
- 所有原有参数都保持兼容

## 🆕 新特性

1. **统一入口**: 所有命令通过 `sage` 统一访问
2. **更好的帮助**: 更详细的命令帮助和示例
3. **彩色输出**: 支持彩色状态显示
4. **作业编号**: 支持使用作业编号（1,2,3...）简化操作
5. **配置管理**: 支持配置文件自定义设置

## 🔍 故障排除

### 命令不存在
```bash
# 重新安装CLI
pip install -e .

# 或手动设置
python sage/cli/setup.py
```

### 连接失败
```bash
# 检查系统状态
sage deploy status

# 启动系统
sage deploy start

# 检查健康状态
sage job health
```

### 配置问题
```bash
# 查看当前配置
sage config

# 手动编辑配置
vi ~/.sage/config.yaml
```

## 📚 示例

### 完整工作流程
```bash
# 1. 启动系统
sage deploy start

# 2. 检查健康状态
sage job health

# 3. 运行脚本
sage job run my_analysis.py --input data.csv

# 4. 监控作业
sage job monitor

# 5. 查看特定作业
sage job show 1

# 6. 停止作业（如需要）
sage job stop 1

# 7. 停止系统
sage deploy stop
```

### 批量操作
```bash
# 清理所有作业
sage job cleanup --force

# 重启系统
sage deploy restart

# 批量监控
sage job monitor --refresh 2
```
