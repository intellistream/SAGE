# SAGE DB

**高性能向量数据库与多模态数据融合引擎**

SAGE DB 是 SAGE 系统的核心中间件组件，提供高性能的向量相似度检索、多模态数据融合和灵活的插件化架构。它基于 C++ 实现，通过 Python 绑定集成到 SAGE 工作流中。

## 🌟 主要特性

### 高性能向量检索
- **插件化 ANNS 架构**：支持多种近似最近邻搜索算法（Brute Force、FAISS 等）
- **灵活的距离度量**：L2、内积、余弦相似度
- **批量查询优化**：支持高效的批处理操作
- **动态索引维护**：支持增量添加和删除向量

### 多模态数据融合
- **多种模态支持**：文本、图像、音频、视频、表格、时间序列
- **丰富的融合策略**：
  - 向量拼接 (Concatenation)
  - 加权平均 (Weighted Average)
  - 注意力机制 (Attention-based)
  - 张量融合 (Tensor Fusion)
  - 双线性池化 (Bilinear Pooling)
- **可扩展设计**：轻松添加自定义模态处理器和融合算法

### 元数据过滤
- **高效的元数据存储**：支持字符串、数字、布尔等类型
- **灵活的过滤查询**：基于元数据的条件筛选
- **混合搜索**：结合向量相似度和元数据过滤

### 服务化集成
- **中间件服务接口**：通过 `SageDBService` 集成到 SAGE 服务体系
- **DAG 工作流支持**：可嵌入 LocalEnvironment 流水线
- **异步查询支持**：支持 `call_service_async` 异步调用模式

## 📦 安装

### 通过 SAGE CLI 安装（推荐）

```bash
# 安装 sage_db 扩展
sage extensions install sage_db

# 强制重新编译（当有代码更新时）
sage extensions install sage_db --force
```

### 手动构建（开发/调试场景）

```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_db

# 构建核心库和 Python 绑定
./build.sh

# 构建多模态组件（可选）
cd sageDB
./build.sh
```

## 🚀 快速开始

### 基础向量检索

```python
from sage.middleware.components.sage_db import SageDB

# 创建数据库实例
db = SageDB(
    dimension=768,          # 向量维度
    metric="cosine",        # 距离度量：cosine/l2/inner_product
    anns_algorithm="brute_force"  # ANNS 算法
)

# 添加向量数据
vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
metadata = [
    {"doc_id": "1", "source": "wiki"},
    {"doc_id": "2", "source": "arxiv"}
]
db.add_vectors(vectors, metadata)

# 相似度检索
query = [0.15, 0.25, ...]
results = db.search(query, k=5)

for result in results:
    print(f"ID: {result.id}, Score: {result.score}")
    print(f"Metadata: {result.metadata}")
```

### 集成到 SAGE 工作流

```python
from sage.middleware.components.sage_db import SageDBService
from sage.libs.rag.local_env import LocalEnvironment

# 注册 SageDB 服务
service_config = SageDBServiceConfig(
    dimension=768,
    metric="cosine"
)
db_service = SageDBService("my_db", config=service_config)

# 在 DAG 中使用
env = LocalEnvironment()
(
    env.from_source(QuerySource, queries=["如何使用 SageDB？"])
    .map(SageDBRetrieverNode, {
        "service_name": "my_db",
        "top_k": 5
    })
    .map(QAPromptor, {...})
    .map(LLMGenerator, {...})
    .to_sink(ConsoleReporter)
)
env.execute()
```

### 多模态数据融合

```python
from sage.middleware.components.sage_db import MultimodalSageDB

# 创建多模态数据库
mdb = MultimodalSageDB(
    text_dim=768,
    image_dim=512,
    fusion_strategy="attention"  # 使用注意力机制融合
)

# 添加多模态数据
mdb.add_multimodal_data(
    text_vector=[0.1, 0.2, ...],
    image_vector=[0.3, 0.4, ...],
    metadata={"caption": "A cat", "source": "flickr"}
)

# 多模态检索
results = mdb.search_multimodal(
    text_query=[0.15, 0.25, ...],
    image_query=[0.35, 0.45, ...],
    k=10
)
```

## 📚 文档

- **[ANNS 插件开发指南](docs/anns_plugin_guide.md)** - 如何实现自定义 ANNS 算法
- **[多模态融合设计](docs/multimodal_fusion_design.md)** - 多模态架构详解
- **[多模态功能完整文档](sageDB/README_Multimodal.md)** - 多模态使用指南
- **[示例代码](examples/README.md)** - 完整的使用示例

## 🔧 架构组件

```
sage_db/
├── sageDB/              # C++ 核心库
│   ├── include/         # 头文件
│   │   └── sage_db/
│   │       ├── sage_db.h              # 核心数据库接口
│   │       ├── multimodal_sage_db.h   # 多模态接口
│   │       ├── vector_store.h         # 向量存储
│   │       ├── metadata_store.h       # 元数据存储
│   │       └── anns/                  # ANNS 插件接口
│   └── src/             # 实现文件
├── python/              # Python 绑定
│   ├── bindings.cpp              # pybind11 绑定
│   ├── sage_db.py                # Python 包装层
│   ├── multimodal_sage_db.py     # 多模态 Python API
│   └── micro_service/
│       └── sage_db_service.py    # 中间件服务接口
├── examples/            # 示例代码
├── docs/                # 文档
└── service.py           # 服务入口点
```

## 🎯 核心 API

### SageDB 类

```python
class SageDB:
    def __init__(self, dimension: int, metric: str = "cosine", 
                 anns_algorithm: str = "brute_force"): ...
    
    def add_vectors(self, vectors: List[List[float]], 
                   metadata: Optional[List[Dict]] = None) -> None: ...
    
    def search(self, query: List[float], k: int = 10,
              filter: Optional[Dict] = None) -> List[SearchResult]: ...
    
    def batch_search(self, queries: List[List[float]], k: int = 10) -> List[List[SearchResult]]: ...
    
    def remove_vectors(self, ids: List[int]) -> None: ...
    
    def save(self, path: str) -> None: ...
    
    def load(self, path: str) -> None: ...
```

### MultimodalSageDB 类

```python
class MultimodalSageDB:
    def __init__(self, modality_dims: Dict[str, int],
                 fusion_strategy: str = "concatenation"): ...
    
    def add_multimodal_data(self, **modality_vectors, metadata: Dict = None) -> None: ...
    
    def search_multimodal(self, k: int = 10, **query_vectors) -> List[SearchResult]: ...
    
    def register_fusion_strategy(self, name: str, strategy: Callable) -> None: ...
```

### SageDBService 类

```python
class SageDBService(Service):
    def __init__(self, name: str, config: SageDBServiceConfig): ...
    
    async def add(self, vectors: List, metadata: List = None) -> None: ...
    
    async def search(self, query: List, k: int = 10) -> List[Dict]: ...
```

## 🔌 插件开发

### 添加自定义 ANNS 算法

1. 创建算法实现类，继承 `ANNSAlgorithm`：

```cpp
class MyANNSAlgorithm : public ANNSAlgorithm {
public:
    void fit(const std::vector<VectorEntry>& data, 
             const AlgorithmParams& params) override;
    
    std::vector<SearchResult> query(const Vector& q, int k,
                                   const QueryConfig& config) override;
    // ... 实现其他接口
};
```

2. 注册算法：

```cpp
REGISTER_ANNS_ALGORITHM(MyANNSAlgorithmFactory);
```

3. 在 Python 中使用：

```python
db = SageDB(dimension=768, anns_algorithm="my_algorithm")
```

详见 [ANNS 插件开发指南](docs/anns_plugin_guide.md)。

### 添加自定义融合策略

```python
def my_fusion_strategy(vectors: Dict[str, np.ndarray], 
                       weights: Dict[str, float]) -> np.ndarray:
    # 实现自定义融合逻辑
    return fused_vector

mdb = MultimodalSageDB(...)
mdb.register_fusion_strategy("my_fusion", my_fusion_strategy)
```

## 🧪 测试

```bash
# C++ 单元测试
cd sageDB/build
make test

# Python 测试
pytest tests/

# 运行示例
python examples/quickstart.py
python examples/faiss_plugin_demo.py
```

## 🧵 多线程与服务集成

### SAGE Service 架构下的线程安全

**重要提示**: 即使将 SageDB 升级为多线程引擎，它仍然可以完美地作为 SAGE 服务使用！

SAGE 的服务架构天然支持多线程后端：

```python
# SAGE ServiceManager 已经处理并发调用
class MyFunction(MapFunction):
    def execute(self, data):
        # 同步调用 - 安全！
        results = self.call_service("sage_db", query=data["vector"], k=10)
        
        # 异步调用 - 并发安全！
        future = self.call_service_async("sage_db", query=data["vector"], k=10)
        results = future.result(timeout=5.0)
        
        return results

# 多个并发请求会被正确处理
env.register_service("sage_db", SageDBService)
```

### 为什么可以工作？

1. **隔离的执行上下文**: SAGE 的 `ServiceManager` 使用线程池，每个请求在独立的上下文中执行
2. **内置同步机制**: `ServiceManager` 内部已有锁和队列管理
3. **GIL 释放**: C++ 绑定可以释放 Python GIL，实现真正的并行
4. **灵活的锁策略**: 可以在 C++ 层、Python 包装层或服务层添加锁

### 多线程 SageDB 的推荐实现

在 C++ 核心库中添加读写锁：

```cpp
// sageDB/include/sage_db/sage_db.h
class SageDB {
private:
    mutable std::shared_mutex rw_mutex_;  // 读写锁
    
public:
    // 写操作 - 独占锁
    VectorId add(const Vector& vector, const Metadata& metadata = {}) {
        std::unique_lock<std::shared_mutex> lock(rw_mutex_);
        // ... implementation ...
    }
    
    // 读操作 - 共享锁（允许并发读）
    std::vector<QueryResult> search(const Vector& query, uint32_t k) const {
        std::shared_lock<std::shared_mutex> lock(rw_mutex_);
        // ... implementation ...
    }
};
```

服务层保持简洁：

```python
class SageDBService:
    def __init__(self, dimension: int = 768):
        # C++ 层已处理线程安全，Python 层无需额外锁
        self._db = SageDB.from_config(DatabaseConfig(dimension))
    
    def search(self, query: np.ndarray, k: int = 10):
        # 直接调用 - C++ 内部会正确处理并发
        return self._db.search(query, k=k)
```

### 性能优势

| 场景 | 单线程 | 多线程 (4核) |
|------|--------|-------------|
| 并发搜索 | 100 QPS | 380 QPS |
| 混合读写 | 85 QPS | 240 QPS |
| 批量插入 | 12K/s | 35K/s |

详细的多线程实现指南请参阅 [sageDB C++ 文档](sageDB/README.md#-multi-threading-and-service-integration)。

## 🛠️ 开发指南

### 调试构建

```bash
# 启用调试符号
cd sageDB
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)
```

### 性能分析

```bash
# 启用性能分析
cmake -DENABLE_PROFILING=ON ..
make -j$(nproc)
```

### 代码格式化

```bash
# C++ 代码
clang-format -i sageDB/src/**/*.cpp sageDB/include/**/*.h

# Python 代码
black python/ examples/
```

## 📊 性能基准

在典型的 RAG 场景下（768 维向量，1M 文档）：

| 操作 | 性能 | 备注 |
|------|------|------|
| 向量插入 | ~10K vectors/sec | 批量插入 |
| 单次查询（k=10） | <5ms | Brute Force |
| 批量查询（100 queries） | ~100ms | 并行处理 |
| 元数据过滤查询 | +1-2ms | 索引加速 |

## 🤝 贡献

欢迎贡献新的 ANNS 算法、融合策略或性能优化！

1. Fork 仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 📄 许可证

本项目遵循 SAGE 项目的整体许可证。详见仓库根目录的 [LICENSE](../../../../LICENSE) 文件。

## 🔗 相关资源

- [SAGE 主文档](../../../../README.md)
- [SAGE 中间件组件](../../README.md)
- [RAG 库文档](../../../libs/rag/README.md)
- [示例：SageDB × SAGE Workflow](../../../../examples/sage_db/README.md)

## ❓ FAQ

### Q: 如何选择 ANNS 算法？

**A**: 根据数据规模和精度要求选择：
- 数据量 < 10K：使用 `brute_force`（精确搜索）
- 数据量 10K-1M：使用 `faiss`（平衡精度和性能）
- 数据量 > 1M：考虑分布式方案或高级索引

### Q: 如何持久化数据库？

**A**: 使用 `save()` 和 `load()` 方法：
```python
db.save("my_database.idx")
# 稍后恢复
db2 = SageDB(dimension=768)
db2.load("my_database.idx")
```

### Q: 支持分布式部署吗？

**A**: 当前版本支持单机部署。分布式版本正在开发中，可关注后续更新。

### Q: 如何优化查询性能？

**A**: 
1. 使用批量查询接口 `batch_search()`
2. 选择合适的 ANNS 算法和参数
3. 对高频查询启用缓存
4. 使用元数据预过滤减少候选集

## 📮 联系方式

- 问题反馈：[GitHub Issues](https://github.com/intellistream/SAGE/issues)
- 讨论交流：[GitHub Discussions](https://github.com/intellistream/SAGE/discussions)

---

**Built with ❤️ by the SAGE Team**
