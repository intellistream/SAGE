# file sage/core/neuromem/search_engine/vdb_backend/faiss_backend.py
# python sage/core/neuromem/search_engine/vdb_backend/faiss_backend.py

# TODO: 
# 1.保存机制的实现===>保存 类及属性，索引、映射表（hash256 Faiss64 vector）

import os
import faiss
import numpy as np
from dotenv import load_dotenv
from typing import Optional, List, Dict

# 加载工程根目录下 sage/.env 配置
# Load configuration from .env file under the sage directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../../.env'))

class FaissBackend:
    def __init__(
        self, 
        name: str, 
        dim: int, 
        vectors: Optional[List[np.ndarray]] = None, 
        ids: Optional[List[str]] = None
        ):
        """
        初始化 FaissBackend 实例，设置索引名称、维度，并可选性地加载初始向量和ID
        Initialize the FaissBackend instance with name, dimension, and optionally preload vectors and ids.
        """
        self.index_name = name
        self.dim = dim
        self.index, self._deletion_supported = self._init_index()
        self.id_map: Dict[int, str] = {}      # int64 → str mapping
        self.rev_map: Dict[str, int] = {}     # str → int64 mapping
        self.next_id: int = 1                 # Auto-increment int64 ID
        self.tombstones: set[str] = set()     # Tombstone set for deleted IDs
        
        if vectors is not None and ids is not None:
            self._build_index(vectors, ids)
           
    def _init_index(self):
        """
        根据环境变量初始化FAISS索引
        Initialize FAISS index based on environment variables
        """
        index_type = os.getenv("FAISS_INDEX_TYPE", "IndexFlatL2")
        
        # 基础索引类型 / Basic index types
        if index_type == "IndexFlatL2":
            return faiss.IndexFlatL2(self.dim), True

        elif index_type == "IndexFlatIP":
            return faiss.IndexFlatIP(self.dim), True

        # 图索引类型 / Graph index types
        elif index_type == "IndexHNSWFlat":
            hnsw_m = int(os.getenv("HNSW_M", "32"))
            ef_construction = int(os.getenv("HNSW_EF_CONSTRUCTION", "200"))
            index = faiss.IndexHNSWFlat(self.dim, hnsw_m)
            index.hnsw.efConstruction = ef_construction
            if os.getenv("HNSW_EF_SEARCH"):
                index.hnsw.efSearch = int(os.getenv("HNSW_EF_SEARCH")) # type: ignore
            return index, False  

        # 倒排文件索引 / Inverted file indexes
        elif index_type == "IndexIVFFlat":
            nlist = int(os.getenv("IVF_NLIST", "100"))
            nprobe = int(os.getenv("IVF_NPROBE", "10"))
            quantizer = faiss.IndexFlatL2(self.dim)
            metric = self._get_metric(os.getenv("IVF_METRIC", "L2"))
            index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, metric)
            index.nprobe = nprobe
            return index, True

        elif index_type == "IndexIVFPQ":
            nlist = int(os.getenv("IVF_NLIST", "100"))
            nprobe = int(os.getenv("IVF_NPROBE", "10"))
            m = int(os.getenv("PQ_M", "8"))
            nbits = int(os.getenv("PQ_NBITS", "8"))
            quantizer = faiss.IndexFlatL2(self.dim)
            metric = self._get_metric(os.getenv("IVF_METRIC", "L2"))
            index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, m, nbits, metric)
            index.nprobe = nprobe
            return index, True

        elif index_type == "IndexIVFScalarQuantizer":
            nlist = int(os.getenv("IVF_NLIST", "100"))
            nprobe = int(os.getenv("IVF_NPROBE", "10"))
            qtype_str = os.getenv("SQ_TYPE", "QT_8bit")
            qtype = getattr(faiss.ScalarQuantizer, qtype_str)
            metric = self._get_metric(os.getenv("IVF_METRIC", "L2"))
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFScalarQuantizer(quantizer, self.dim, nlist, qtype, metric)
            index.nprobe = nprobe
            return index, True

        # 其他索引类型 / Other index types
        elif index_type == "IndexLSH":
            nbits = int(os.getenv("LSH_NBITS", "512"))
            rotate_data = os.getenv("LSH_ROTATE_DATA", "True").lower() == "true"
            train_thresholds = os.getenv("LSH_TRAIN_THRESHOLDS", "False").lower() == "true"
            index = faiss.IndexLSH(self.dim, nbits, rotate_data, train_thresholds)
            return index, False  

        elif index_type == "IndexPQ":
            m = int(os.getenv("PQ_M", "8"))
            nbits = int(os.getenv("PQ_NBITS", "8"))
            metric = self._get_metric(os.getenv("PQ_METRIC", "L2"))
            return faiss.IndexPQ(self.dim, m, nbits, metric), False

        elif index_type == "IndexScalarQuantizer":
            qtype_str = os.getenv("SQ_TYPE", "QT_8bit")
            qtype = getattr(faiss.ScalarQuantizer, qtype_str)
            metric = self._get_metric(os.getenv("SQ_METRIC", "L2"))
            return faiss.IndexScalarQuantizer(self.dim, qtype, metric), True

        elif index_type == "IndexRefineFlat":
            base_index, base_deletion_supported = self._init_base_index()
            k_factor = float(os.getenv("REFINE_K_FACTOR", "1.0"))
            return faiss.IndexRefineFlat(base_index, k_factor), True

        elif index_type == "IndexIDMap":
            base_index, base_deletion_supported = self._init_base_index()
            return faiss.IndexIDMap(base_index), base_deletion_supported

        else:
            raise ValueError(f"Unsupported FAISS index type: {index_type}")

    def _init_base_index(self):
        """
        用于 IndexIDMap / IndexRefineFlat 的基础索引初始化
        Initialize base index for IndexIDMap or IndexRefineFlat
        """
        base_type = os.getenv("FAISS_BASE_INDEX_TYPE", "IndexFlatL2")

        original_type = os.getenv("FAISS_INDEX_TYPE")
        os.environ["FAISS_INDEX_TYPE"] = base_type
        index = self._init_index()
        if original_type:
            os.environ["FAISS_INDEX_TYPE"] = original_type
        return index

    def _get_metric(self, metric_str):
        """
        获取距离度量方式：L2 或 Inner Product
        Get distance metric: L2 or Inner Product
        """
        return faiss.METRIC_L2 if metric_str == "L2" else faiss.METRIC_INNER_PRODUCT
    
    def _build_index(self, vectors: List[np.ndarray], ids: List[str]):
        """
        构建初始索引并绑定 string ID → int ID 映射关系
        Build initial index and bind string ID to int ID mapping
        """
        np_vectors = np.vstack(vectors).astype("float32")
        int_ids = []

        for string_id in ids:
            if string_id in self.rev_map:
                int_id = self.rev_map[string_id]
            else:
                int_id = self.next_id
                self.next_id += 1
                self.rev_map[string_id] = int_id
                self.id_map[int_id] = string_id
            int_ids.append(int_id)

        int_ids_np = np.array(int_ids, dtype=np.int64)
        if not isinstance(self.index, faiss.IndexIDMap):
            print("Wrapping index with IndexIDMap")
            self.index = faiss.IndexIDMap(self.index)  # 仅当未包装时才包装
        self.index.add_with_ids(np_vectors, int_ids_np)  # type: ignore
        
    def delete(self, string_id: str):
        """
        删除指定ID（物理删除或墓碑标记）
        Delete by ID (physical removal or tombstone marking)
        """
        if string_id not in self.rev_map:
            return

        int_id = self.rev_map[string_id]
        
        if self._deletion_supported:
            try:
                id_vector = np.array([int_id], dtype=np.int64)
                self.index.remove_ids(id_vector)  # type: ignore
            except Exception as e:
                print(f"删除失败，转为墓碑标记 / Deletion failed, fallback to tombstone: {e}")
                self.tombstones.add(string_id)
        else:
            self.tombstones.add(string_id)
    
    def update(self, string_id: str, new_vector: np.ndarray):
        """
        更新指定 ID 的向量：保持原有映射关系，仅替换向量内容
        Update the vector for the given ID, preserving the existing ID mapping.
        """
        if string_id not in self.rev_map:
            # 如果ID不存在，直接插入
            return self.insert(new_vector, string_id)

        int_id = self.rev_map[string_id]

        if self._deletion_supported:
            try:
                 # 删除旧向量并插入新向量 / Remove old vector and insert new one
                id_vector = np.array([int_id], dtype=np.int64)
                self.index.remove_ids(id_vector)  # type: ignore
                vector = np.expand_dims(new_vector.astype("float32"), axis=0)
                int_id_np = np.array([int_id], dtype=np.int64)
                self.index.add_with_ids(vector, int_id_np)  # type: ignore
            except Exception as e:
                print(f"更新失败 / Update failed: {e}")
                self.insert(new_vector, string_id)
        else:
            if string_id in self.rev_map:
                old_int_id = self.rev_map[string_id]
                if old_int_id in self.id_map:
                    del self.id_map[old_int_id]
                del self.rev_map[string_id]
            
            new_int_id = self.next_id
            self.next_id += 1
            self.rev_map[string_id] = new_int_id
            self.id_map[new_int_id] = string_id
            vector = np.expand_dims(new_vector.astype("float32"), axis=0)
            int_id_np = np.array([new_int_id], dtype=np.int64)
            self.index.add_with_ids(vector, int_id_np)  # type: ignore

    def search(self, query_vector: np.ndarray, topk: int = 10):
        """
        向量检索 / Vector search
        返回top_k结果（过滤墓碑） / Return top_k results (filter tombstones)
        """
        query_vector = np.expand_dims(query_vector.astype("float32"), axis=0)
        distances, int_ids = self.index.search(query_vector, topk + len(self.tombstones))  # 多查一些结果 # type: ignore
        
        results = []
        filtered_distances = []
        
        for i, dist in zip(int_ids[0], distances[0]):
            if i == -1:  # FAISS 空槽位标记
                continue
            string_id = self.id_map.get(i)
            if string_id and string_id not in self.tombstones:
                results.append(string_id)
                filtered_distances.append(float(dist))  # 显式转为Python float
            if len(results) >= topk:
                break
                
        return results, filtered_distances

    def insert(self, vector: np.ndarray, string_id: str):
        """
        插入单个向量及其字符串 ID 到索引中
        Insert a single vector and its string ID into the index
        """
        if string_id in self.rev_map:
            int_id = self.rev_map[string_id]
        else:
            int_id = self.next_id
            self.next_id += 1
            self.rev_map[string_id] = int_id
            self.id_map[int_id] = string_id

        vector = np.expand_dims(vector.astype("float32"), axis=0)
        int_id_np = np.array([int_id], dtype=np.int64)
        self.index.add_with_ids(vector, int_id_np) # type: ignore
    
    def batch_insert(self, vectors: List[np.ndarray], string_ids: List[str]):
        """
        批量插入多个向量及其对应的 string_id
        Batch insert multiple vectors and their corresponding string_id
        """
        assert len(vectors) == len(string_ids), "Vectors and IDs must match in length"
        np_vectors = np.vstack(vectors).astype("float32")
        int_ids = []

        for string_id in string_ids:
            if string_id in self.rev_map:
                int_id = self.rev_map[string_id]
            else:
                int_id = self.next_id
                self.next_id += 1
                self.rev_map[string_id] = int_id
                self.id_map[int_id] = string_id
            int_ids.append(int_id)

        int_ids_np = np.array(int_ids, dtype=np.int64)
        self.index.add_with_ids(np_vectors, int_ids_np)  # type: ignore



if __name__ == "__main__":
    import numpy as np

    # 初始化参数
    dim = 4
    index_name = "test_index"
    vectors = [np.array([1.0, 0.0, 0.0, 0.0]),
               np.array([0.0, 1.0, 0.0, 0.0]),
               np.array([0.0, 0.0, 1.0, 0.0])]
    ids = ["id1", "id2", "id3"]
    faiss_backend = FaissBackend(name=index_name, dim=dim, vectors=vectors, ids=ids)

    def run_test(test_name, operation, query_vector, expected_ids, expected_distances, top_k=10, round_digits=None):
        print(f"\n{test_name}")
        operation()
        
        string_ids, distances = faiss_backend.search(query_vector, top_k)
        if round_digits is not None:
            distances = [round(d, round_digits) for d in distances]
        
        print("预期结果:")
        print(f"  IDs: {expected_ids}")
        print(f"  Distances: {expected_distances}")
        print("实际结果:")
        print(f"  IDs: {string_ids}")
        print(f"  Distances: {distances}")

    # 测试用例
    tests = [
        ("测试 1: 插入单个向量",
         lambda: faiss_backend.insert(np.array([0.0, 0.0, 0.0, 1.0]), "id4"),
         np.array([1.0, 0.0, 0.0, 0.0]),
         ['id1', 'id2', 'id3', 'id4'],
         [0.0, 2.0, 2.0, 2.0]),
        
        ("测试 2: 更新向量",
         lambda: faiss_backend.update("id1", np.array([0.5, 0.5, 0.0, 0.0])),
         np.array([0.5, 0.5, 0.0, 0.0]),
         ['id1', 'id2', 'id3', 'id4'],
         [0.0, 0.5, 1.5, 1.5]),
        
        ("测试 3: 删除向量",
         lambda: faiss_backend.delete("id2"),
         np.array([0.0, 1.0, 0.0, 0.0]),
         ['id1', 'id3', 'id4'],
         [0.5, 2.0, 2.0]),
        
        ("测试 4: 批量插入",
         lambda: faiss_backend.batch_insert(
             [np.array([0.1, 0.1, 0.1, 0.1]),
              np.array([0.2, 0.2, 0.2, 0.2])],
             ["id5", "id6"]),
         np.array([0.1, 0.1, 0.1, 0.1]),
         ['id5', 'id6', 'id1', 'id3', 'id4'],
         [0.0, 0.04, 0.34, 0.84, 0.84],
         10, 2)
    ]

    for test in tests:
        run_test(*test)


