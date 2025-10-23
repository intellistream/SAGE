# SAGE TSDB - Time Series Database Component

**高性能时序数据库中间件组件**

SAGE TSDB 是 SAGE 系统的时序数据库中间件组件，提供高性能的时间序列数据存储、查询和流处理能力。

## 🏗️ 架构

本组件采用 **C++ 核心 + Python 服务层** 的混合架构：

- **C++ 核心** (`sageTSDB/`): 独立的 C++ 项目，包含高性能的时序数据处理引擎
- **Python 服务层** (`python/`): Python 包装层，提供 SAGE 集成和微服务接口

```
sage_tsdb/
├── sageTSDB/          # C++ 核心 (Git submodule)
│   ├── include/       # C++ 头文件
│   ├── src/           # C++ 实现
│   ├── python/        # pybind11 绑定
│   └── CMakeLists.txt
├── python/            # Python 服务层
│   ├── sage_tsdb.py           # Python 包装
│   ├── algorithms/            # 算法接口
│   └── micro_service/         # 微服务接口
├── examples/          # 使用示例
└── README.md          # 本文档
```

## 🌟 主要特性

### C++ 核心特性
- **高性能存储**: 优化的时序数据索引结构
- **乱序处理**: 自动缓冲和水印机制处理延迟数据
- **线程安全**: 使用读写锁保证并发安全
- **可插拔算法**: 扩展性强的算法框架

### Python 服务层特性
- **SAGE 集成**: 无缝集成到 SAGE 工作流
- **微服务接口**: 标准化的服务调用接口
- **灵活配置**: 支持多种配置选项
- **算法封装**: 易用的 Python API

## 📦 安装

### 1. 初始化 Submodule

由于 C++ 核心是独立的 Git 仓库（submodule），首次使用需要初始化：

```bash
# 在 SAGE 根目录
git submodule update --init --recursive

# 或者克隆时直接包含 submodule
git clone --recursive https://github.com/intellistream/SAGE.git
```

### 2. 构建 C++ 核心与 Python 绑定

#### 方法 1: 使用 Makefile（推荐）

```bash
# 在 SAGE 根目录
make build-extensions
```

#### 方法 2: 使用构建脚本

```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb
./build_tsdb.sh
```

#### 方法 3: 手动构建（调试用）

```bash
cd sageTSDB/build
cmake .. -DBUILD_PYTHON_BINDINGS=ON
make -j$(nproc)

# 复制 Python 扩展到包目录
cp python/_sage_tsdb*.so ../../python/
```

构建完成后，验证扩展状态：

```bash
sage extensions status
```

应该显示:
```
✅ 时序数据库扩展 (C++) ✓
```

**重要**: C++ 扩展提供 10-100x 的性能提升。如果不可用，系统会降级到纯 Python 实现。

### 3. 使用 Python 服务

Python 服务层无需额外安装，直接导入即可：

```python
from sage.middleware.components.sage_tsdb import SageTSDB, SageTSDBService
```

## 🚀 快速开始

### 基础使用

```python
from sage.middleware.components.sage_tsdb import SageTSDB, TimeRange
from datetime import datetime

# 创建数据库
db = SageTSDB()

# 添加数据
timestamp = int(datetime.now().timestamp() * 1000)
db.add(timestamp=timestamp, value=42.5,
       tags={"sensor": "temp_01", "location": "room_a"})

# 查询数据
time_range = TimeRange(
    start_time=timestamp - 10000,
    end_time=timestamp + 10000
)
results = db.query(time_range=time_range,
                  tags={"sensor": "temp_01"})

print(f"Found {len(results)} data points")
```

### 流连接 (Stream Join)

```python
from sage.middleware.components.sage_tsdb import OutOfOrderStreamJoin

# 创建连接算法
join_algo = OutOfOrderStreamJoin({
    "window_size": 5000,    # 5秒窗口
    "max_delay": 3000,      # 最大3秒延迟
})

# 处理两个流
joined = join_algo.process(
    left_stream=left_data,
    right_stream=right_data
)

print(f"Joined {len(joined)} pairs")
```

### 窗口聚合

```python
from sage.middleware.components.sage_tsdb import WindowAggregator

# 创建聚合器
aggregator = WindowAggregator({
    "window_type": "tumbling",
    "window_size": 60000,   # 60秒窗口
    "aggregation": "avg"
})

# 聚合数据
aggregated = aggregator.process(time_series_data)
```

### 服务集成

```python
from sage.middleware.components.sage_tsdb import SageTSDBService

# 创建服务实例
service = SageTSDBService()

# 通过服务添加数据
service.add(timestamp=timestamp, value=42.5,
           tags={"sensor": "temp_01"})

# 通过服务查询
results = service.query(
    start_time=start_time,
    end_time=end_time,
    tags={"sensor": "temp_01"},
    aggregation="avg",
    window_size=5000
)

# 流连接
joined = service.stream_join(
    left_stream=left_data,
    right_stream=right_data,
    window_size=5000
)
```

## 📚 核心 API

### SageTSDB 类

```python
class SageTSDB:
    def add(timestamp, value, tags=None, fields=None) -> int
    def add_batch(timestamps, values, tags_list=None, fields_list=None) -> list[int]
    def query(time_range, tags=None, aggregation=None, window_size=None) -> list[TimeSeriesData]
    def register_algorithm(name, algorithm)
    def apply_algorithm(name, data, **kwargs) -> Any
```

### SageTSDBService 类

```python
class SageTSDBService:
    def add(timestamp, value, tags=None, fields=None) -> int
    def add_batch(timestamps, values, tags_list=None, fields_list=None) -> list[int]
    def query(start_time, end_time, tags=None, aggregation=None, window_size=None) -> list[dict]
    def stream_join(left_stream, right_stream, window_size=None, join_key=None) -> list[dict]
    def window_aggregate(start_time, end_time, window_type="tumbling",
                        window_size=None, aggregation="avg") -> list[dict]
```

### 算法接口

```python
class TimeSeriesAlgorithm:
    def process(data: list[TimeSeriesData], **kwargs) -> Any
    def reset()
    def get_stats() -> dict
```

## 🔌 自定义算法

### Python 算法

```python
from sage.middleware.components.sage_tsdb.python.algorithms import TimeSeriesAlgorithm

class MyAlgorithm(TimeSeriesAlgorithm):
    def __init__(self, config=None):
        super().__init__(config)

    def process(self, data, **kwargs):
        # 实现算法逻辑
        results = []
        for point in data:
            # 处理数据点
            results.append(processed_point)
        return results

# 注册算法
db = SageTSDB()
db.register_algorithm("my_algo", MyAlgorithm())

# 使用算法
results = db.apply_algorithm("my_algo", data)
```

### C++ 算法 (高性能场景)

```cpp
#include <sage_tsdb/algorithms/algorithm_base.h>

class MyAlgorithm : public sage_tsdb::TimeSeriesAlgorithm {
public:
    MyAlgorithm(const AlgorithmConfig& config)
        : TimeSeriesAlgorithm(config) {}

    std::vector<TimeSeriesData> process(
        const std::vector<TimeSeriesData>& input) override {
        // 实现高性能算法
        return output;
    }
};

// 注册算法
REGISTER_ALGORITHM("my_algo", MyAlgorithm);
```

## 🔧 开发指南

### 更新 C++ 核心

1. 进入 submodule 目录：
```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
```

2. 进行修改并测试：
```bash
# 修改 C++ 代码
vim src/core/time_series_db.cpp

# 重新构建
./build.sh --test
```

3. 提交到 sageTSDB 仓库：
```bash
git add .
git commit -m "Update: feature description"
git push origin main
```

4. 更新 SAGE 中的 submodule 引用：
```bash
cd /path/to/SAGE
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Update sageTSDB submodule"
git push
```

### 添加新算法

#### Python 算法
1. 在 `python/algorithms/` 创建新文件
2. 继承 `TimeSeriesAlgorithm` 基类
3. 实现 `process()` 方法
4. 在 `__init__.py` 中导出

#### C++ 算法
1. 在 `sageTSDB/include/sage_tsdb/algorithms/` 添加头文件
2. 在 `sageTSDB/src/algorithms/` 添加实现
3. 使用 `REGISTER_ALGORITHM` 宏注册
4. 更新 `CMakeLists.txt`

## 📊 性能

### C++ 核心性能 (Intel i7, 16GB RAM)

| 操作 | 吞吐量 | 延迟 |
|------|--------|------|
| 单次插入 | 1M ops/sec | < 1 μs |
| 批量插入 (1000) | 5M ops/sec | < 200 ns/op |
| 查询 (1000条) | 500K queries/sec | 2 μs |
| 流连接 | 300K pairs/sec | 3 μs |
| 窗口聚合 | 800K windows/sec | 1.2 μs |

### Python 服务层性能

由于 Python 调用开销，性能约为 C++ 核心的 60-80%，但仍能满足大多数应用场景。

## 🧪 测试

```bash
# C++ 测试
cd sageTSDB/build
ctest -V

# Python 测试
cd examples
python basic_usage.py
python stream_join_demo.py
python service_demo.py
```

## 📖 文档

- [C++ 核心文档](sageTSDB/README.md)
- [算法开发指南](docs/ALGORITHMS_GUIDE.md)
- [性能优化指南](docs/PERFORMANCE.md)
- [示例代码](examples/README.md)

## 🔗 相关资源

- **sageTSDB C++ 仓库**: https://github.com/intellistream/sageTSDB
- **SAGE 主项目**: https://github.com/intellistream/SAGE
- **问题反馈**: https://github.com/intellistream/SAGE/issues

## 🤝 贡献

欢迎贡献！请遵循以下流程：

1. Fork 相应的仓库（SAGE 或 sageTSDB）
2. 创建特性分支
3. 提交更改
4. 开启 Pull Request

## 📄 许可证

Apache License 2.0 - 详见 [LICENSE](../../../../LICENSE)

## 📮 联系方式

- Email: shuhao_zhang@hust.edu.cn
- GitHub Issues: https://github.com/intellistream/SAGE/issues

---

**Built with ❤️ by the IntelliStream Team**
