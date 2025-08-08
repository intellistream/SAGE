# SAGE Scripts Directory

本目录包含SAGE项目的各种自动化脚本和工具，采用模块化架构设计。

## 📦 模块化架构

### 核心模块

#### 📝 logging.sh
提供统一的彩色日志输出功能。

**主要功能：**
- 彩色日志输出（INFO、SUCCESS、WARNING、ERROR）
- 带时间戳的日志记录
- 调试日志支持
- 进度条显示
- 用户确认提示

#### 🐍 conda_utils.sh
提供 Conda 环境管理功能。

**主要功能：**
- 自动安装 Miniconda（多平台支持）
- Conda 环境创建和管理
- 包安装和依赖管理
- 环境激活和初始化

#### 🛠️ common_utils.sh
提供通用工具函数。

**主要功能：**
- 命令存在性检查
- 文件和目录验证
- 项目结构验证
- 环境变量设置

#### ⚙️ config.sh
配置文件，定义默认设置。

### 使用示例

```bash
#!/bin/bash

# 引入模块
source scripts/logging.sh
source scripts/common_utils.sh
source scripts/conda_utils.sh

# 使用功能
print_header "开始执行任务"
check_command "git"
setup_sage_environment
```

## 🚀 部署脚本

### `deployment_setup.py`
**主要的部署自动化脚本**

- **功能**: 一键部署SAGE项目，包括Git submodule初始化、依赖安装、文档构建等
- **使用方法**:
  ```bash
  # 快速安装
  python3 scripts/deployment_setup.py install
  
  # 开发环境完整安装
  python3 scripts/deployment_setup.py full --dev
  
  # 检查项目状态
  python3 scripts/deployment_setup.py status
  
  # 初始化Git submodule
  python3 scripts/deployment_setup.py init
  
  # 运行测试
  python3 scripts/deployment_setup.py test
  ```

- **特性**:
  - 🎨 彩色输出和进度指示
  - 🔍 智能状态检查
  - 📦 自动依赖管理（包括sage-tools包）
  - 📚 文档构建集成
  - 🧪 测试运行支持
  - 🔄 Git submodule自动化
  - 🛠️ 完整包检查（sage, sage-kernel, sage-middleware, sage-apps, sage-dev-toolkit, sage-frontend）

## 🛠️ 构建脚本

### `build_with_license.sh`
- **功能**: 带许可证的构建脚本
- **用途**: 企业版本构建

### `cleanup_build_artifacts.sh` 
- **功能**: 清理构建产物
- **使用**: `./scripts/cleanup_build_artifacts.sh`

### `create_dual_repository.sh`
- **功能**: 创建双仓库结构
- **用途**: 管理公共/私有代码分离

## 🧪 测试脚本

### `test_all_packages.sh`
**一键运行所有包测试的脚本**

- **功能**: 使用 `sage-dev test` 命令对所有或指定的包进行测试
- **使用方法**:
  ```bash
  # 测试所有包
  ./scripts/test_all_packages.sh
  
  # 只测试指定包
  ./scripts/test_all_packages.sh sage-core sage-kernel
  
  # 并行测试配置
  ./scripts/test_all_packages.sh -j 8 -t 600
  
  # 重新运行失败的测试
  ./scripts/test_all_packages.sh --failed -v
  
  # 只显示摘要结果
  ./scripts/test_all_packages.sh --summary
  
  # 遇到错误继续执行
  ./scripts/test_all_packages.sh --continue-on-error
  ```

- **特性**:
  - 🚀 并行测试执行，可配置worker数量
  - 📊 详细的测试结果摘要和统计
  - 🎯 支持指定特定包或测试所有包
  - ⏱️ 可配置的超时控制
  - 📝 个别包的详细日志记录
  - 🔄 失败测试重新运行支持
  - 🛡️ 错误处理和继续执行选项

### `quick_test.sh`
**快速测试主要包的脚本**

- **功能**: 快速测试核心包，适用于日常开发验证
- **使用方法**:
  ```bash
  # 快速测试主要包
  ./scripts/quick_test.sh
  
  # 传递额外参数
  ./scripts/quick_test.sh --verbose
  ```

- **特性**:
  - 🎯 只测试有测试的主要包（sage-frontend, sage-core, sage-kernel）
  - 🚀 自动并行执行（3个worker）
  - ⚡ 较短的超时时间（2分钟）
  - 🛡️ 自动继续执行，即使某个包失败

## 📋 最佳实践

1. **脚本执行权限**: 确保脚本有执行权限
   ```bash
   chmod +x scripts/*.sh
   ```

2. **推荐使用顺序**:
   ```bash
   # 1. 新用户快速开始
   ./quickstart.sh
   
   # 2. 或者手动步骤
   python3 scripts/deployment_setup.py init
   python3 scripts/deployment_setup.py install --dev
   
   # 3. 检查状态
   python3 scripts/deployment_setup.py status
   ```

3. **开发工作流**:
   ```bash
   # 日常开发
   python3 scripts/deployment_setup.py status  # 检查环境
   
   # 更新依赖
   python3 scripts/deployment_setup.py install --dev
   
   # 清理构建
   ./scripts/cleanup_build_artifacts.sh
   ```

## 🆘 故障排除

- **权限问题**: 确保脚本有执行权限
- **Python路径**: 确保使用正确的Python环境
- **Git权限**: 检查Git submodule访问权限
- **依赖冲突**: 使用虚拟环境隔离依赖

## 📖 相关文档

- [开发者指南](../DEVELOPER_GUIDE.md)
- [安装说明](../README.md)
- [文档构建指南](../docs-public/README.md)
