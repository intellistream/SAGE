# SAGE CLI - 命令行界面工具

SAGE CLI提供统一的命令行界面，用于管理和操作SAGE框架的各种功能。

## 主要功能

### 项目管理
- **项目初始化**: 创建新的SAGE项目
- **依赖管理**: 安装和管理项目依赖
- **配置管理**: 项目配置文件管理

### 作业管理
- **作业提交**: 提交和管理数据流作业
- **状态监控**: 实时监控作业执行状态
- **日志查看**: 查看作业执行日志

### 服务管理
- **服务启动**: 启动各种SAGE服务
- **健康检查**: 检查服务运行状态
- **配置验证**: 验证服务配置

### 开发工具
- **代码生成**: 生成模板代码
- **测试运行**: 执行单元测试和集成测试
- **调试支持**: 调试模式和诊断工具

## 安装

```bash
pip install sage-cli
```

## 基本使用

### 创建新项目

```bash
# 创建新项目
sage init my-project

# 进入项目目录
cd my-project

# 安装依赖
sage install
```

### 运行作业

```bash
# 运行本地作业
sage run local my_job.py

# 运行分布式作业
sage run cluster my_job.py --nodes 4

# 查看作业状态
sage status

# 查看作业日志
sage logs job-123
```

### 服务管理

```bash
# 启动作业管理器
sage service start jobmanager

# 启动LLM服务
sage service start llm --model gpt-3.5-turbo

# 检查服务状态
sage service status

# 停止所有服务
sage service stop --all
```

### 开发工具

```bash
# 生成函数模板
sage generate function --name my_function

# 运行测试
sage test

# 运行代码质量检查
sage lint

# 生成文档
sage docs build
```

## 配置

CLI工具可以通过配置文件进行自定义：

```yaml
# ~/.sage/config.yaml
default:
  environment: local
  log_level: INFO

environments:
  local:
    jobmanager_url: "http://localhost:8080"
  
  cluster:
    jobmanager_url: "http://cluster.example.com:8080"
    
services:
  llm:
    default_model: "gpt-3.5-turbo"
    timeout: 30
```

## 命令参考

### 全局选项
- `--config`: 指定配置文件路径
- `--verbose`: 启用详细输出
- `--dry-run`: 只显示将要执行的操作，不实际执行

### 主要命令
- `sage init`: 初始化新项目
- `sage run`: 运行作业
- `sage service`: 服务管理
- `sage status`: 查看状态
- `sage logs`: 查看日志
- `sage test`: 运行测试
- `sage docs`: 文档管理

## 许可证

MIT License
