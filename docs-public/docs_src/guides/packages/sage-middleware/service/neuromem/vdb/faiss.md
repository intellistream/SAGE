# FaissIndex API 文档

`FaissIndex` 位于 `packages/sage-middleware/src/sage/middleware/components/neuromem/search_engine/vdb_index/faiss_index.py`，是 `index_factory` 默认创建的向量索引实现。它封装了常见的 FAISS 索引类型（Flat、HNSW、IVF、PQ 等），同时提供字符串 ID 与向量的映射管理。

---

## 一、快速开始

```python
import numpy as np
from sage.middleware.components.neuromem.search_engine.vdb_index.faiss_index import FaissIndex

config = {
    "name": "demo_index",
    "dim": 384,
    "index_type": "IndexFlatL2",
    "tombstone_threshold": 50,
}

index = FaissIndex(config=config)

vectors = [np.random.random(config["dim"]).astype(np.float32) for _ in range(5)]
ids = [f"doc_{i}" for i in range(5)]
index.batch_insert(vectors, ids)

query = np.random.random(config["dim"]).astype(np.float32)
result_ids, distances = index.search(query, topk=3)
print(result_ids, distances)

index.store("./faiss_index_store")
```

---

## 二、初始化参数

| 参数 | 说明 |
| --- | --- |
| `name` | 索引名称，用于序列化。|
| `dim` | 向量维度，需与集合中的向量一致。|
| `index_type` | FAISS 索引类型，例如 `IndexFlatL2`、`IndexHNSWFlat`、`IndexIVFPQ`。|
| `tombstone_threshold` | 软删除阈值，超过后触发重建。|
| `vectors` / `ids` | 可选：在构造时加载初始向量与 ID。|
| `config` | 额外参数，透传给具体索引类型（如 `IVF_NLIST`、`PQ_M` 等）。|

常见调优字段：

- `IVF_NLIST`, `IVF_NPROBE`
- `HNSW_M`, `HNSW_EF_CONSTRUCTION`, `HNSW_EF_SEARCH`
- `PQ_M`, `PQ_NBITS`

---

## 三、核心方法

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `search` | `search(query_vector: np.ndarray, topk: int = 10, threshold: Optional[float] = None)` | 返回字符串 ID 列表及距离。|
| `insert` | `insert(vector: np.ndarray, string_id: str)` | 写入单个向量。|
| `batch_insert` | `batch_insert(vectors: List[np.ndarray], string_ids: List[str])` | 批量写入向量。|
| `update` | `update(string_id: str, new_vector: np.ndarray)` | 更新现有向量。|
| `delete` | `delete(string_id: str)` | 软删除指定 ID（落入墓碑集合）。|
| `store` | `store(dir_path: str)` | 序列化索引、向量与映射关系。|
| `load` | `load(name: str, load_path: str)` *(类方法)* | 从磁盘恢复索引。|

---

## 四、索引类型速查

| 类型 | 特性 | 建议场景 |
| --- | --- | --- |
| `IndexFlatL2` / `IndexFlatIP` | 精确检索，无需训练，内存消耗较高 | 小规模数据或对召回率要求极高的场景 |
| `IndexHNSWFlat` | 图结构近似检索，速度快、内存中等 | 中等规模数据，平衡性能与精度 |
| `IndexIVFFlat` / `IndexIVFPQ` | 倒排列表 + 精确/量化编码 | 大规模数据；`PQ` 适用于内存紧张场景 |
| `IndexLSH` | 局部敏感哈希 | 极高维稀疏向量（实验性） |

---

## 五、注意事项

- **字符串 ID 管理**：内部会维护双向映射，确保可以使用业务侧的字符串 ID。
- **墓碑机制**：部分索引不支持原地删除，`delete` 会将向量标记为墓碑并在达到阈值时触发重建。
- **向量归一化**：`VDBMemoryCollection` 会自动对向量进行 L2 归一化（即每个向量的模长为 1），适用于需要归一化的索引类型（如 `IndexFlatIP` 用于余弦相似度检索）。**如果你直接使用 `FaissIndex`，请根据所选索引类型自行判断是否需要归一化**。例如，使用 `IndexFlatIP` 时，建议在插入和查询前对向量进行归一化：

  ```python
  import numpy as np
  def l2_normalize(vecs):
      return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
  # 示例：归一化一批向量
  vectors = np.random.rand(10, 384)
  normalized_vectors = l2_normalize(vectors)
- **持久化**：`store` 会保存索引文件、ID 映射及配置；加载时需提供相同的 `name`。

更多细节请阅读源码 `search_engine/vdb_index/faiss_index.py` 以及 `vdb_collection.py` 中的调用示例。
