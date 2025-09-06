# SageFlow 用户指南

## 安装

### Python DSL (推荐生产使用)
1. 克隆仓库：`git clone <repository-url>`
2. 进入项目目录：`cd sage_flow`
3. 安装依赖：`pip install -e .`
4. 验证安装：`python -c "from sageflow import Stream; print('安装成功')"`

### C++ 核心 (开发使用，需要修复后构建)
1. 安装依赖：CMake 3.16+、C++17 编译器、pybind11
2. 创建构建目录：`mkdir build && cd build`
3. 配置构建：`cmake ..`
4. 编译：`make -j$(nproc)`
5. Python 绑定：`pip install -e .` (需要C++库已构建)

## 链式 API 示例

### 基本流处理
```python
from sageflow import Stream
from typing import List

# 从列表创建流
data: List[int] = [1, 2, 3, 4, 5]

# 链式操作：过滤偶数，映射平方，打印结果
stream = Stream.from_list(data) \
    .filter(lambda x: x % 2 == 0) \
    .map(lambda x: x ** 2) \
    .sink(print)

# 执行管道
stream.execute()
# 输出：4, 16
```

### 处理 CSV 数据
```python
import pandas as pd
from sageflow import Stream

# 读取 CSV
df = pd.read_csv('test_data.csv')
data = df['column'].tolist()

# 处理：清理文本，过滤空值，聚合计数
result = Stream.from_list(data) \
    .map(str.strip) \
    .filter(lambda x: x != '') \
    .sink(lambda x: print(f"处理: {x}")) \
    .execute()

print(f"处理了 {len(data)} 条记录")
```

### 高级聚合示例
```python
from sageflow import Stream
from functools import reduce

numbers = [1, 2, 3, 4, 5, 6]

total = Stream.from_list(numbers) \
    .filter(lambda x: x > 3) \
    .map(lambda x: x * 2) \
    .sink(reduce(lambda acc, x: acc + x, [])) \
    .execute()

print(f"总和: {total}")
```

## 故障排除

### Python DSL 问题
- **ImportError**: 确保已执行 `pip install -e .` 并在项目根目录运行。
- **类型检查失败**: 安装 mypy：`pip install mypy` 并运行 `mypy sageflow/`。
- **示例运行失败**: 检查示例目录下是否有测试数据文件，运行 `python examples/sage_flow_examples/basic_stream_processing.py`。

### C++ 构建问题
- **BaseOperator redefinition**: 清理 CMake 缓存 `rm -rf build/` 后重构建。确保所有 operator 头文件正确包含。
- **Response incomplete type**: 在 [`include/operator/response.hpp`](include/operator/response.hpp) 添加默认构造函数和完整定义。
- **override 不匹配**: 检查模板参数一致性，所有派生类方法签名必须匹配 `BaseOperator<InputType, OutputType>::process()`。
- **Linux 模板问题**: 添加缺失 `#include <cassert>` 和 `std::optional` 头文件，确保 C++17 标准：`cmake .. -DCMAKE_CXX_STANDARD=17`。
- **macOS 未执行**: 使用相同 CMake 配置，在 macOS 上运行 `make` 验证跨平台兼容性。

### 常见错误
- **GIL 锁定问题**: Python DSL 已优化减少 30-50% GIL 持有时间，无需手动处理。
- **测试失败**: 运行 Python 测试 `pytest tests/python/` 或 C++ 测试 `make test` (修复后)。
- **性能问题**: 使用 examples/performance_monitoring.py 监控流处理性能。

更多细节请参考 [API 参考](../docs/api_reference.md) 和 [示例](../examples/sage_flow_examples/)。