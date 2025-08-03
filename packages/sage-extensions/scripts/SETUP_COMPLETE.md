# SAGE Extensions 安装完成！

## 🎉 恭喜！SAGE Extensions 已成功安装！

您现在可以使用高性能的向量数据库功能了。

## ✨ 快速开始

```python
from sage.extensions.sage_db import SageDB, IndexType, DistanceMetric

# 创建向量数据库
db = SageDB(dimension=128)

# 添加向量和元数据
vector1 = [0.1] * 128
metadata1 = {"type": "document", "id": "doc1", "category": "AI"}
id1 = db.add(vector1, metadata1)

# 批量添加
vectors = [[0.2] * 128, [0.3] * 128, [0.4] * 128]
metadata = [
    {"type": "document", "id": "doc2", "category": "ML"},
    {"type": "document", "id": "doc3", "category": "DL"},
    {"type": "document", "id": "doc4", "category": "AI"}
]
batch_ids = db.add_batch(vectors, metadata)

# 构建索引
db.build_index()

# 搜索相似向量
query = [0.25] * 128
results = db.search(query, k=3)

print(f"找到 {len(results)} 个相似结果:")
for i, result in enumerate(results):
    print(f"  结果 {i+1}: ID={result.id}, 相似度={result.score:.4f}")
    print(f"           元数据: {result.metadata}")
```

## 🔧 高级用法

### 自定义索引类型和距离度量

```python
# 使用余弦相似度的 FLAT 索引
db = SageDB(
    dimension=256, 
    index_type=IndexType.FLAT,
    metric=DistanceMetric.COSINE
)
```

### 可用的索引类型
- `IndexType.AUTO` - 自动选择最佳索引类型
- `IndexType.FLAT` - 精确搜索，适合小数据集
- `IndexType.IVF_FLAT` - 倒排文件索引，适合大数据集
- `IndexType.HNSW_FLAT` - 分层导航小世界图，快速近似搜索

### 可用的距离度量
- `DistanceMetric.L2` - 欧几里得距离
- `DistanceMetric.IP` - 内积距离
- `DistanceMetric.COSINE` - 余弦距离

## 📁 项目结构

```
scripts/
├── build.py              # C++ 扩展构建脚本
├── install.sh            # 系统依赖安装脚本
├── install_complete.sh   # 完整一键安装脚本
├── test_complete.py      # 完整功能测试脚本
└── SETUP_COMPLETE.md     # 本文件

src/sage/extensions/sage_db/
├── __init__.py           # Python 包初始化
├── sage_db.py           # Python API 包装器
├── _sage_db.so          # 编译的 C++ 扩展
└── ...                  # C++ 源代码和头文件
```

## 🚀 性能特性

- **高性能**: 基于 FAISS 的 C++ 后端
- **多种索引**: 支持精确和近似搜索
- **元数据支持**: 丰富的元数据过滤功能
- **批量操作**: 高效的批量向量添加
- **持久化**: 支持数据库保存和加载

## 🧪 运行测试

```bash
# 运行完整功能测试
python scripts/test_complete.py

# 重新构建 C++ 扩展
python scripts/build.py

# 完整重新安装
./scripts/install_complete.sh
```

## 📚 更多信息

- 查看 `scripts/test_complete.py` 了解更多使用示例
- 检查 `src/sage/extensions/sage_db/` 目录了解 API 详情
- 参考项目文档了解高级功能

---

**技术支持**: SAGE Extensions 现在已经完全配置并可以使用！

如果遇到任何问题，请检查：
1. Python 版本 >= 3.10
2. 所有系统依赖已安装
3. C++ 扩展编译成功
4. 运行测试脚本验证功能

享受使用 SAGE Extensions 的高性能向量数据库功能！🎯
