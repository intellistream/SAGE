# SAGE Quickstart Script Improvements

## 修改概述

已成功修改 `quickstart.sh` 脚本，在执行SAGE安装逻辑之前集成了 Miniconda 安装和 SAGE 环境初始化功能。

## 主要改进

### 1. 新增功能函数

#### `check_command_optional()`
- 可选命令检查函数，不会在命令不存在时退出脚本
- 用于检查 conda、wget、curl 等可选依赖

#### `install_miniconda()`
- 自动检测操作系统和CPU架构（Linux/macOS, x86_64/aarch64/arm64）
- 支持 wget 和 curl 两种下载工具
- 跳过已安装的 Miniconda
- 自动初始化 conda 并配置环境

#### `setup_sage_environment()`
- 创建名为 "sage" 的 conda 环境（Python 3.11）
- 安装基础开发工具：pip, setuptools, wheel, build
- 安装科学计算包：numpy, pandas, matplotlib, jupyter, notebook
- 智能检测和激活现有环境

### 2. 执行流程优化

新的执行顺序：
1. **基础环境检查** - 检查 git 和下载工具（wget/curl）
2. **用户选择安装类型** - 快速/开发者/完整安装
3. **环境设置阶段**：
   - 安装 Miniconda（如需要）
   - 创建和配置 SAGE conda 环境
   - 验证 Python 和 pip 可用性
4. **执行安装** - 在 conda 环境中运行原有安装脚本
5. **显示使用指南** - 包含 conda 环境激活说明

### 3. 用户体验改进

- 增加了详细的环境信息显示
- 提供 conda 环境激活指引
- 在所有命令说明中加入环境激活提醒
- 改进了错误处理和用户提示

### 4. 兼容性增强

- 支持多种操作系统（Linux、macOS）
- 支持多种CPU架构（x86_64、aarch64、arm64）
- 支持多种下载工具（wget、curl）
- 向后兼容现有的安装流程

## 使用方法

用户只需运行：
```bash
./quickstart.sh
```

脚本会自动：
1. 安装 Miniconda（如果未安装）
2. 创建独立的 SAGE 开发环境
3. 安装所有必要的依赖
4. 执行原有的 SAGE 安装流程

## 注意事项

- 用户每次使用 SAGE 时需要先激活环境：`conda activate sage`
- 脚本会在 `$HOME/miniconda3` 安装 Miniconda
- 创建的 conda 环境名为 "sage"，使用 Python 3.11
- 如果 Miniconda 已安装，脚本会跳过安装步骤
- 支持重复运行，不会重复创建已存在的环境

## 验证安装

安装完成后，用户可以通过以下命令验证：
```bash
conda activate sage
python --version
pip list
jupyter --version
```

这些修改确保了新用户能够在任何支持的系统上快速、可靠地设置 SAGE 开发环境。
