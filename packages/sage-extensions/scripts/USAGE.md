# SAGE Extensions 使用示例

## 安装验证

我们的 SAGE Extensions 包现在可以正常工作了！以下是完整的使用流程：

## 1. 一键安装

```bash
cd /home/flecther/SAGE/packages/sage-extensions
./scripts/install.sh
```

这个脚本会自动：
- 检测操作系统（Ubuntu/Debian/CentOS/macOS）
- 安装系统依赖（cmake, gcc, pkg-config, blas, lapack 等）
- 安装 Python 依赖（numpy, pybind11, faiss 等）
- 编译 C++ 扩展
- 验证安装

## 2. 开发安装

```bash
cd /home/flecther/SAGE/packages/sage-extensions
pip install -e .
```

这会调用 `setup.py`，自动检查依赖并运行构建脚本。

## 3. 使用示例

### 基本使用

```python
import numpy as np
from sage.extensions.sage_db import SageDB, IndexType, DistanceMetric

# 创建向量数据库
db = SageDB(dimension=128, 
           index_type=IndexType.FLAT, 
           metric=DistanceMetric.L2)

# 准备一些测试数据
vectors = np.random.random((1000, 128)).astype(np.float32)

# 批量添加向量
ids = db.add_batch(vectors.tolist())
print(f"Added {len(ids)} vectors")

# 搜索相似向量
query = vectors[0]  # 使用第一个向量作为查询
results = db.search(query.tolist(), k=10)

print(f"Found {len(results)} similar vectors:")
for result in results:
    print(f"  ID: {result.id}, Score: {result.score:.4f}")
```

### 带元数据的使用

```python
# 添加带元数据的向量
metadata_list = [
    {"category": "document", "title": f"Doc {i}"}
    for i in range(len(vectors))
]

db_with_metadata = SageDB(dimension=128)
ids = db_with_metadata.add_batch(vectors.tolist(), metadata_list)

# 搜索并获取元数据
results = db_with_metadata.search(query.tolist(), k=5, include_metadata=True)
for result in results:
    print(f"ID: {result.id}, Score: {result.score:.4f}")
    print(f"Metadata: {result.metadata}")
```

## 4. 验证安装

运行内置的测试脚本：

```bash
python scripts/test_install.py
```

或者运行验证脚本：

```bash
python scripts/verify_install.py
```

## 5. 检查扩展状态

```python
import sage.extensions

# 检查所有扩展的加载状态
status = sage.extensions.get_extension_status()
print(f"Extension status: {status}")

# 检查 SAGE DB 具体状态
from sage.extensions.sage_db import get_status
db_status = get_status()
print(f"SAGE DB status: {db_status}")
```

## 6. 性能特性

- **高性能 C++ 后端**：关键算法使用 C++17 实现
- **FAISS 集成**：支持多种索引类型（FLAT, IVF_FLAT, HNSW等）
- **NumPy 兼容**：无缝处理 NumPy 数组
- **元数据支持**：支持向量关联的键值对元数据
- **批量操作**：优化的批量添加和搜索

## 构建文件说明

安装成功后，会生成以下关键文件：

```
src/sage/extensions/sage_db/
├── _sage_db.cpython-310-x86_64-linux-gnu.so  # 编译的C++扩展
├── build/                                      # CMake构建目录
│   ├── libsage_db.so                          # C++库文件
│   └── _sage_db.cpython-310-x86_64-linux-gnu.so
├── sage_db.py                                 # Python包装器
└── __init__.py                                # 模块初始化
```

## 故障排除

如果遇到问题，请：

1. 检查系统依赖：`cmake --version`, `gcc --version`, `pkg-config --version`
2. 验证 Python 依赖：`pip list | grep -E "(numpy|pybind11|faiss)"`
3. 重新构建：`python scripts/build.py`
4. 清理重装：`rm -rf build/ && pip install -e . --force-reinstall`

## 成功标志

看到以下输出表示安装成功：

```
SAGE Extensions Installation Test
========================================
Testing basic imports...
✓ sage.extensions imported successfully

Testing SAGE DB module...
✓ SageDB imported successfully
✓ SageDB instance created successfully
✓ Added 10 vectors successfully
✓ Search returned 3 results

========================================
✅ All tests passed!
```

🎉 恭喜！您的 SAGE Extensions 已经成功安装并可以使用了！
