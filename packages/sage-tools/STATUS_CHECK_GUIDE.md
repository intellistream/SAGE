# SAGE 开发工具状态检查功能

## 概述

SAGE 开发工具现在提供了全面的项目状态检查功能，帮助开发者快速了解项目的当前状态，识别潜在问题。

## 功能特性

### 检查项目
- **环境检查**: Python版本、执行路径、工作目录、环境变量
- **包状态检查**: SAGE包的安装状态、配置文件、测试文件
- **依赖检查**: 关键依赖包的可用性和导入状态
- **服务状态检查**: Ray集群、JobManager等服务的运行状态
- **配置检查**: 配置文件存在性、SAGE_HOME设置

### 输出格式
- **summary** (默认): 简要摘要，显示关键问题和建议
- **full**: 详细显示所有检查结果，带有格式化面板
- **json**: 结构化JSON输出，适合程序化处理

## 使用方法

### 1. 基本用法 (推荐)
```bash
# 使用新的统一CLI
python -m sage.tools.cli dev status

# 简要摘要输出，显示关键问题
```

### 2. 详细输出
```bash
# 查看所有检查项目的详细结果
python -m sage.tools.cli dev status --output-format full
```

### 3. JSON输出
```bash
# 获取结构化数据，适合脚本处理
python -m sage.tools.cli dev status --output-format json
```

### 4. 向后兼容
```bash
# 仍然可以使用旧命令 (会显示deprecation警告)
sage-dev status
```

### 5. 自定义项目路径
```bash
# 检查指定目录的项目状态
python -m sage.tools.cli dev status --project-root /path/to/project
```

## 状态检查结果说明

### 常见问题及解决方案

#### ⚠️ SAGE_HOME 环境变量未设置
```bash
# 设置SAGE_HOME环境变量
export SAGE_HOME=/path/to/sage/home
```

#### ⚠️ SAGE 包尚未安装
```bash
# 运行快速安装脚本
./quickstart.sh
```

#### ⚠️ 缺少依赖包
```bash
# 安装缺少的Python包
pip install <package_name>

# 或者重新运行安装脚本
./quickstart.sh
```

#### ℹ️ Ray 集群未运行
```bash
# 启动Ray集群 (如果需要)
ray start --head
```

### 输出示例

#### 简要输出
```
📊 SAGE 项目状态报告
⏰ 检查时间: 2025-09-12T23:51:16
📁 项目路径: /home/user/SAGE
✅ 检查项目: 5/5
🎉 所有检查项目都通过了!

📋 需要注意的问题:
  ⚠️ SAGE_HOME 环境变量未设置
  ⚠️ SAGE 包尚未安装，请运行 ./quickstart.sh
```

#### 详细输出
```
╭──────────────────── ✅ 环境检查 ────────────────────╮
│ 🐍 Python: 3.11.13                              │
│ 🏠 工作目录: /home/user/SAGE                     │
│ 🌍 Conda环境: sage                              │
│ 🏠 SAGE_HOME: ❌ 未设置                         │
╰──────────────────────────────────────────────────────╯
```

## 集成到开发流程

### 1. 每日开发检查
将状态检查添加到开发流程中，确保环境配置正确：
```bash
# 开始工作前检查状态
python -m sage.tools.cli dev status
```

### 2. CI/CD集成
在持续集成中使用JSON输出进行自动化检查：
```bash
# 获取状态数据并解析
python -m sage.tools.cli dev status --output-format json > status.json
```

### 3. 问题诊断
当遇到问题时，使用详细输出进行诊断：
```bash
# 详细检查所有组件状态
python -m sage.tools.cli dev status --output-format full
```

## 扩展和自定义

状态检查器的实现位于 `packages/sage-tools/src/sage/tools/dev/tools/project_status_checker.py`，可以根据项目需要添加新的检查项目或修改现有检查逻辑。
