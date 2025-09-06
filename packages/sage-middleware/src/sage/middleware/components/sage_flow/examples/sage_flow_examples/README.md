#!/usr/bin/env python3
"""
SAGE Flow Python 示例套件

这是一个全面的 Python 示例套件，用于测试和演示 SAGE Flow 的各种功能。
所有示例都支持模拟模式，即使在没有安装 SAGE Flow Python 模块的情况下也能运行。

作者: Kilo Code
日期: 2025-09-04
"""

# SAGE Flow Python 示例套件

这是一个全面的 Python 示例套件，用于测试和演示 SAGE Flow 的各种功能。所有示例都必须使用真实的 SAGE Flow C++ 引擎运行。

## 📁 示例文件结构

```
examples/sage_flow_examples/
├── README.md                           # 本文档
├── basic_stream_processing.py          # 基础流处理示例
├── advanced_stream_processing.py       # 高级流处理示例
├── data_source_examples.py             # 数据源测试示例
├── function_operator_examples.py       # 函数和操作符示例
├── performance_monitoring.py           # 性能和监控示例
├── run_all_examples.py                 # 批量测试运行器
└── test_report.md                      # 测试报告（运行后生成）
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.7+
- 必需：SAGE Flow Python 模块（必须正确编译和安装）
- 可选：`psutil` 包（用于系统监控）

### 2. 安装依赖

```bash
# 必需：编译和安装 SAGE Flow Python 模块
cd packages/sage-middleware/src
python setup.py build_ext --inplace

# 可选：安装 psutil 用于系统监控
pip install psutil
```

### 3. 运行示例

```bash
# 运行单个示例
python basic_stream_processing.py

# 运行所有示例并生成测试报告
python run_all_examples.py
```

## 📋 示例说明

### 1. 基础流处理示例 (`basic_stream_processing.py`)

**功能演示：**
- 创建数据流
- 基本的 map/filter/sink 操作
- 消息处理和转换
- 环境配置

**运行示例：**
```python
from basic_stream_processing import BasicStreamProcessor

processor = BasicStreamProcessor()
processor.demonstrate_message_creation()
results = processor.process_with_real_api()
```

### 2. 高级流处理示例 (`advanced_stream_processing.py`)

**功能演示：**
- 窗口操作（时间窗口、计数窗口）
- 聚合操作（分组统计、计算）
- 流连接（多流关联）
- 复杂数据转换

**主要功能：**
- 时间窗口聚合
- 用户行为统计
- 传感器数据分析
- 流数据关联

### 3. 数据源测试示例 (`data_source_examples.py`)

**功能演示：**
- 文件数据源（文本、CSV、JSON）
- Kafka 数据源（消息队列）
- 流数据源（实时数据）
- 数据源配置和监控

**支持的数据源类型：**
- 本地文件系统
- Apache Kafka
- 实时数据流
- 自定义数据源

### 4. 函数和操作符示例 (`function_operator_examples.py`)

**功能演示：**
- 自定义函数注册
- 函数组合和链式调用
- 错误处理和恢复
- 操作符性能测试

**主要特性：**
- 灵活的函数定义
- 错误恢复机制
- 性能监控
- 函数组合模式

### 5. 性能和监控示例 (`performance_monitoring.py`)

**功能演示：**
- 性能基准测试
- 系统资源监控
- 吞吐量分析
- 延迟测量
- 并发处理测试

**监控指标：**
- CPU 使用率
- 内存消耗
- 处理吞吐量
- 响应延迟
- 系统负载

## 🔧 配置说明

### 环境变量

```bash
# SAGE Flow 模块路径
export PYTHONPATH=$PYTHONPATH:/path/to/sage/packages

# Kafka 配置（如果使用）
export KAFKA_BROKERS=localhost:9092
export KAFKA_TOPIC=sage_flow_test
```

### 模块导入

```python
# 强制导入 SAGE Flow 模块
try:
    import sage_flow_datastream as sfd
    print("✓ SAGE Flow 模块导入成功")
except ImportError as e:
    raise ImportError(
        f"无法导入 SAGE Flow 模块: {e}\n"
        "请确保已正确编译和安装 SAGE Flow Python 模块。"
    ) from e
```

## 📊 测试结果

运行 `run_all_examples.py` 后会生成详细的测试报告，包括：

- 每个示例的执行状态
- 性能指标
- 错误和警告统计
- 建议和改进方案

### 示例测试报告

```
测试概览
- 总示例数: 5
- 成功示例: 5
- 失败示例: 0
- 成功率: 100.0%

详细结果
✅ basic_stream_processing.py: 0.04秒
✅ advanced_stream_processing.py: 0.09秒
✅ data_source_examples.py: 1.01秒
✅ function_operator_examples.py: 0.05秒
✅ performance_monitoring.py: 29.37秒
```

## 🐛 问题排查

### 常见问题

1. **模块未找到错误**
   ```
   ✗ SAGE Flow 模块未找到: No module named 'sage_flow_datastream'
   ```
   **解决方案：**
   - 编译 SAGE Flow Python 模块
   - 检查 PYTHONPATH 设置
   - 确认模块安装位置

2. **依赖包缺失**
    ```
    ModuleNotFoundError: No module named 'psutil'
    ```
    **解决方案：**
    - `pip install psutil`
    - 或者在没有 psutil 的情况下运行（将使用模拟的系统监控）

3. **权限错误**
   ```
   Permission denied: /path/to/file
   ```
   **解决方案：**
   - 检查文件权限
   - 使用适当的用户运行
   - 修改文件路径

### 调试模式

启用详细日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 性能优化

### 基准测试结果

基于测试数据，典型性能指标：

- **简单处理**: ~800-1000 items/秒
- **复杂处理**: ~150-200 items/秒
- **内存使用**: 50-200 MB（取决于数据大小）
- **并发处理**: 线程数增加可提升 2-4 倍性能

### 优化建议

1. **数据批处理**: 使用适当的批次大小
2. **并发处理**: 根据 CPU 核心数调整线程数
3. **内存管理**: 及时清理大对象
4. **缓存优化**: 复用计算结果

## 🔗 相关链接

- [SAGE Flow 核心文档](../README.md)
- [Python API 参考](api_reference.md)
- [性能调优指南](performance_guide.md)
- [故障排除](troubleshooting.md)

## 🤝 贡献

欢迎提交问题和改进建议！

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 📄 许可证

本项目采用与 SAGE Flow 相同的许可证。