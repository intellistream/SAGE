# SAGE 开发工具包 (SAGE Development Toolkit)

🛠️ **统一的SAGE框架开发工具集合**

## 概述

SAGE开发工具包将原本分散在`scripts/`目录中的各种开发工具整合为一个统一的Python应用，提供一致的命令行接口和强大的功能集成。

## 功能特性

### ✅ 已实现功能

- **🧪 智能测试运行**: 支持全量测试、增量测试（基于git diff）和单包测试
- **🔍 依赖关系分析**: 分析包依赖、检测循环依赖、生成依赖报告
- **📦 包管理**: 列出、安装、卸载、构建SAGE包
- **📊 综合报告生成**: 自动生成JSON和Markdown格式的开发报告
- **⚙️ 配置文件支持**: YAML格式的灵活配置管理
- **📝 结构化日志**: 多级别日志输出，支持文件和控制台
- **🔧 动态工具加载**: 自动发现和加载scripts中的工具模块

### 🚧 规划中功能

- **💬 交互模式优化**: 改进交互式命令行体验
- **🎨 彩色输出**: 更友好的终端显示
- **📈 性能监控**: 代码质量和性能分析
- **🔄 CI/CD集成**: 与持续集成流程集成

## 快速开始

### 1. 安装依赖

确保安装了PyYAML：
```bash
pip install pyyaml
```

### 2. 基础使用

```bash
# 显示工具包信息
python sage_dev_toolkit.py info

# 列出所有SAGE包
python sage_dev_toolkit.py package list

# 运行智能测试（基于代码变更）
python sage_dev_toolkit.py test --diff

# 分析依赖关系
python sage_dev_toolkit.py analyze deps

# 生成综合报告
python sage_dev_toolkit.py report
```

### 3. 高级用法

```bash
# 详细模式运行
python sage_dev_toolkit.py --verbose test --all

# 使用自定义配置文件
python sage_dev_toolkit.py --config my_config.yaml package status

# 指定项目根目录
python sage_dev_toolkit.py --project-root /path/to/sage test --diff
```

## 配置说明

工具包使用`sage_dev_toolkit.yaml`配置文件进行配置管理：

```yaml
# 项目配置
project:
  name: "SAGE Framework"
  version: "1.0.0"

# 目录配置
directories:
  packages: "./packages"
  scripts: "./scripts"
  output: "./dev_reports"
  logs: "./test_logs"

# 测试配置
testing:
  default_mode: "diff"
  max_workers: 4
  timeout: 300

# 工具集成配置
tools:
  test_runner:
    module: "test_runner"
    class: "SAGETestRunner"
    enabled: true
  dependency_analyzer:
    module: "advanced_dependency_analyzer_with_sage_mapping"
    class: "SAGEDependencyAnalyzer"
    enabled: true
  package_manager:
    module: "sage-package-manager"
    class: "SagePackageManager"
    enabled: true
```

## 命令参考

### 测试命令
```bash
python sage_dev_toolkit.py test --all          # 运行所有测试
python sage_dev_toolkit.py test --diff         # 智能测试
python sage_dev_toolkit.py test --package NAME # 单包测试
python sage_dev_toolkit.py test --workers 8    # 指定并发数
```

### 分析命令
```bash
python sage_dev_toolkit.py analyze deps        # 完整依赖分析
python sage_dev_toolkit.py analyze summary     # 依赖摘要
python sage_dev_toolkit.py analyze circular    # 循环依赖检测
```

### 包管理命令
```bash
python sage_dev_toolkit.py package list        # 列出所有包
python sage_dev_toolkit.py package status      # 包状态检查
python sage_dev_toolkit.py package install NAME # 安装指定包
python sage_dev_toolkit.py package build       # 构建所有包
```

### 其他命令
```bash
python sage_dev_toolkit.py report              # 生成综合报告
python sage_dev_toolkit.py info                # 显示工具包信息
python sage_dev_toolkit.py interactive         # 交互模式（开发中）
```

## 集成的工具

当前工具包集成了以下scripts中的工具：

1. **test_runner.py** → 测试运行器
   - 智能测试基于git diff
   - 并发测试执行
   - 测试报告生成

2. **advanced_dependency_analyzer_with_sage_mapping.py** → 依赖分析器
   - SAGE包路径映射
   - 循环依赖检测
   - 依赖关系可视化

3. **sage-package-manager.py** → 包管理器
   - 包安装/卸载
   - 依赖关系解析
   - 构建自动化

## 输出和报告

### 报告存储位置
- **输出目录**: `./dev_reports/`
- **日志目录**: `./test_logs/`

### 报告格式
- **JSON格式**: 结构化数据，便于程序处理
- **Markdown格式**: 人类可读的报告文档

### 报告类型
- `test_results_YYYYMMDD_HHMMSS.json` - 测试结果
- `dependency_analysis_YYYYMMDD_HHMMSS.json` - 依赖分析
- `comprehensive_report_YYYYMMDD_HHMMSS.json` - 综合报告
- `comprehensive_report_YYYYMMDD_HHMMSS.md` - Markdown报告

## 开发和扩展

### 添加新工具

1. 在`sage_dev_toolkit.yaml`中添加工具配置：
```yaml
tools:
  my_new_tool:
    module: "my_tool_script"
    class: "MyToolClass"
    enabled: true
```

2. 确保工具脚本在`scripts/`目录中

3. 工具类需要遵循统一的接口约定

### 日志级别

支持以下日志级别：
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息

### 性能考虑

- 使用并发执行提高测试速度
- 动态工具加载减少启动时间
- 配置缓存优化重复操作

## 故障排除

### 常见问题

1. **工具加载失败**
   ```
   解决方案: 检查scripts目录中是否存在对应的脚本文件
   ```

2. **配置文件错误**
   ```
   解决方案: 验证YAML语法，确保必要字段存在
   ```

3. **权限问题**
   ```
   解决方案: 确保有足够权限访问packages和scripts目录
   ```

### 调试模式

使用`--verbose`参数启用详细日志：
```bash
python sage_dev_toolkit.py --verbose info
```

## 版本历史

- **v1.0.0** (2025-08-04)
  - 初始版本发布
  - 集成测试运行器、依赖分析器、包管理器
  - 支持配置文件和结构化日志
  - 实现基础命令行界面

## 贡献

欢迎提交issue和pull request来改进SAGE开发工具包！

## 许可证

MIT License - 详见LICENSE文件
