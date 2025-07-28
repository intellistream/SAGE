# VDB索引类型简要总结

## 1 FAISS 索引

### 1.1 FAISS 索引类型总结

| 索引类型                | 插入       | 删除       | 更新       | 搜索性能 | 搜索精度 | 内存占用 | 适用场景                     |
|-------------------------|------------|------------|------------|----------|----------|----------|-----------------------------|
| Flat (IndexFlatL2/IP)   | 支持       | 不支持     | 不支持     | 慢       | 高       | 高       | 小规模，精确搜索             |
| IVF (IndexIVFFlat)      | 支持       | 支持       | 不支持     | 中       | 中       | 中       | 大规模，近似搜索             |
| IVFPQ (IndexIVFPQ)      | 支持       | 支持       | 不支持     | 快       | 低       | 低       | 超大规模，低内存             |
| HNSW (IndexHNSW)        | 支持       | 不支持     | 不支持     | 快       | 高       | 高       | 中小规模，高精度快速搜索      |
| LSH (IndexLSH)          | 支持       | 不支持     | 不支持     | 快       | 低       | 低       | 高维，快速低精度搜索         |
| ScalarQuantizer         | 支持       | 支持       | 不支持     | 中       | 中       | 低       | 中大规模，内存受限           |

### 1.2 FAISS 索引简要说明

#### 1. Flat (IndexFlatL2 / IndexFlatIP)
- **插入**：支持，慢。
- **删除**：不支持。
- **更新**：不支持。
- **搜索性能**：慢，逐一计算距离。
- **搜索精度**：高，精确搜索。
- **必须参数**：向量维度 `d`。
- **代码**：
  ```python
  import faiss
  d = 64  # 向量维度
  index = faiss.IndexFlatL2(d)  # 仅需维度
  ```

#### 2. IVF (IndexIVFFlat)
- **插入**：支持，较快。
- **删除**：支持（需ID）。
- **更新**：不支持。
- **搜索性能**：中，依赖簇数量。
- **搜索精度**：中，受`nprobe`影响。
- **必须参数**：向量维度 `d`，簇数量 `nlist`，量化器（如 `IndexFlatL2`）。
- **代码**：
  ```python
  import faiss
  d, nlist = 64, 100  # 维度，簇数
  quantizer = faiss.IndexFlatL2(d)
  index = faiss.IndexIVFFlat(quantizer, d, nlist)
  ```

#### 3. IVFPQ (IndexIVFPQ)
- **插入**：支持，较快。
- **删除**：支持（需ID）。
- **更新**：不支持。
- **搜索性能**：快，量化加速。
- **搜索精度**：低，量化损失。
- **必须参数**：向量维度 `d`，簇数量 `nlist`，量化字节数 `m`，量化器。
- **代码**：
  ```python
  import faiss
  d, nlist, m = 64, 100, 8  # 维度，簇数，字节数
  quantizer = faiss.IndexFlatL2(d)
  index = faiss.IndexIVFPQ(quantizer, d, nlist, m, 8)
  ```

#### 4. HNSW (IndexHNSW)
- **插入**：支持，中等。
- **删除**：不支持。
- **更新**：不支持。
- **搜索性能**：快，图结构优化。
- **搜索精度**：高，接近精确。
- **必须参数**：向量维度 `d`，每节点连接数 `M`。
- **代码**：
  ```python
  import faiss
  d, M = 64, 32  # 维度，连接数
  index = faiss.IndexHNSWFlat(d, M)
  ```

#### 5. LSH (IndexLSH)
- **插入**：支持，快速。
- **删除**：不支持。
- **更新**：不支持。
- **搜索性能**：快，哈希计算。
- **搜索精度**：低，哈希近似。
- **必须参数**：向量维度 `d`，哈希位数 `nbits`。
- **代码**：
  ```python
  import faiss
  d, nbits = 64, 256  # 维度，哈希位数
  index = faiss.IndexLSH(d, nbits)
  ```

#### 6. ScalarQuantizer (IndexScalarQuantizer)
- **插入**：支持，快速。
- **删除**：支持（需ID）。
- **更新**：不支持。
- **搜索性能**：中，量化影响。
- **搜索精度**：中，量化损失较小。
- **必须参数**：向量维度 `d`，量化类型（如 `QT_8bit`）。
- **代码**：
  ```python
  import faiss
  d = 64  # 维度
  index = faiss.IndexScalarQuantizer(d, faiss.ScalarQuantizer.QT_8bit)
  ```