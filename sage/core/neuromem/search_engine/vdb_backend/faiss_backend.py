# file sage/core/neuromem/search_engine/vdb_backend/faiss_backend.py
# python sage/core/neuromem/search_engine/vdb_backend/faiss_backend.py


# TODO: 
# 1.墓碑机制的实现===>删除
# 2.更新机制的实现===>更新
# 3.保存机制的实现===>保存 类及属性，索引、映射表（hash256 Faiss64 vector）
# 4.批量插入、索引重建（首先要思考能不能在这一级别进行）

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
        self.index = self._init_index()
        self.id_map: Dict[int, str] = {}      # int64 → str 映射
        self.rev_map: Dict[str, int] = {}      # str → int64 映射
        self.next_id: int = 1                 # 自增 int64 ID
        
        if vectors is not None and ids is not None:
            self._build_index(vectors, ids)
            
    def _init_index(self):
        """
        根据环境变量初始化FAISS索引（默认IndexFlatL2）
        Initialize FAISS index according to environment variable. Default is IndexFlatL2.
        """
        index_type = os.getenv("FAISS_INDEX_TYPE", "IndexFlatL2")
        
        # 基础索引类型 / Basic index types
        if index_type == "IndexFlatL2":
            return faiss.IndexFlatL2(self.dim)

        elif index_type == "IndexFlatIP":
            return faiss.IndexFlatIP(self.dim)

        # 图索引类型 / Graph-based index
        elif index_type == "IndexHNSWFlat":
            hnsw_m = int(os.getenv("HNSW_M", "32"))
            ef_construction = int(os.getenv("HNSW_EF_CONSTRUCTION", "200"))
            index = faiss.IndexHNSWFlat(self.dim, hnsw_m)
            index.hnsw.efConstruction = ef_construction
            if os.getenv("HNSW_EF_SEARCH"):
                index.hnsw.efSearch = int(os.getenv("HNSW_EF_SEARCH"))  # type: ignore
            return index

        # 倒排文件索引 / IVF-based indexes
        elif index_type == "IndexIVFFlat":
            nlist = int(os.getenv("IVF_NLIST", "100"))
            nprobe = int(os.getenv("IVF_NPROBE", "10"))
            quantizer = faiss.IndexFlatL2(self.dim)
            metric = self._get_metric(os.getenv("IVF_METRIC", "L2"))
            index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, metric)
            index.nprobe = nprobe
            return index

        elif index_type == "IndexIVFPQ":
            nlist = int(os.getenv("IVF_NLIST", "100"))
            nprobe = int(os.getenv("IVF_NPROBE", "10"))
            m = int(os.getenv("PQ_M", "8"))
            nbits = int(os.getenv("PQ_NBITS", "8"))
            quantizer = faiss.IndexFlatL2(self.dim)
            metric = self._get_metric(os.getenv("IVF_METRIC", "L2"))
            index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, m, nbits, metric)
            index.nprobe = nprobe
            return index

        elif index_type == "IndexIVFScalarQuantizer":
            nlist = int(os.getenv("IVF_NLIST", "100"))
            nprobe = int(os.getenv("IVF_NPROBE", "10"))
            qtype_str = os.getenv("SQ_TYPE", "QT_8bit")
            qtype = getattr(faiss.ScalarQuantizer, qtype_str)
            metric = self._get_metric(os.getenv("IVF_METRIC", "L2"))
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFScalarQuantizer(quantizer, self.dim, nlist, qtype, metric)
            index.nprobe = nprobe
            return index

        # LSH、PQ、量化等其他索引类型 / Other index types
        elif index_type == "IndexLSH":
            nbits = int(os.getenv("LSH_NBITS", "512"))
            rotate_data = os.getenv("LSH_ROTATE_DATA", "True").lower() == "true"
            train_thresholds = os.getenv("LSH_TRAIN_THRESHOLDS", "False").lower() == "true"
            return faiss.IndexLSH(self.dim, nbits, rotate_data, train_thresholds)

        elif index_type == "IndexPQ":
            m = int(os.getenv("PQ_M", "8"))
            nbits = int(os.getenv("PQ_NBITS", "8"))
            metric = self._get_metric(os.getenv("PQ_METRIC", "L2"))
            return faiss.IndexPQ(self.dim, m, nbits, metric)

        elif index_type == "IndexScalarQuantizer":
            qtype_str = os.getenv("SQ_TYPE", "QT_8bit")
            qtype = getattr(faiss.ScalarQuantizer, qtype_str)
            metric = self._get_metric(os.getenv("SQ_METRIC", "L2"))
            return faiss.IndexScalarQuantizer(self.dim, qtype, metric)

        elif index_type == "IndexRefineFlat":
            base_index = self._init_base_index()  # 需要先初始化基础索引
            k_factor = float(os.getenv("REFINE_K_FACTOR", "1.0"))
            return faiss.IndexRefineFlat(base_index, k_factor)

        elif index_type == "IndexIDMap":
            base_index = self._init_base_index()  # 需要先初始化基础索引
            return faiss.IndexIDMap(base_index)

        else:
            raise ValueError(f"Unsupported FAISS index type: {index_type}")

    def _init_base_index(self):
        """
        用于 IndexIDMap / IndexRefineFlat 的基础索引初始化
        Initialize base index for IndexIDMap or IndexRefineFlat
        """
        base_type = os.getenv("FAISS_BASE_INDEX_TYPE", "IndexFlatL2")
        # 临时保存原始类型，然后恢复
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
        self.index = faiss.IndexIDMap(self.index)  # 包装为支持自定义 ID 的索引 / Wrap index with ID mapping support
        self.index.add_with_ids(np_vectors, int_ids_np) # type: ignore

    def search(self, query_vector: np.ndarray, topk: int = 10):
        """
        执行向量检索，返回 top_k 的字符串 ID 和对应距离
        Perform vector search and return top_k string IDs and distances
        """
        query_vector = np.expand_dims(query_vector.astype("float32"), axis=0)
        distances, int_ids = self.index.search(query_vector, topk) # type: ignore
        string_ids = [self.id_map.get(i, str(i)) for i in int_ids[0]]
        return string_ids, distances[0]

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
    
if __name__ == "__main__":
    import numpy as np

    # 测试参数
    dim = 4  # 向量维度
    index_name = "test_index"
    vectors = [
        np.array([1.0, 0.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0, 0.0]),
    ]
    ids = ["id1", "id2", "id3"]

    # 初始化 FaissBackend
    faiss_backend = FaissBackend(name=index_name, dim=dim, vectors=vectors, ids=ids)

    # 添加一个新向量
    new_vector = np.array([0.0, 0.0, 0.0, 1.0])
    new_id = "id4"
    faiss_backend.insert(new_vector, new_id)

    # 执行搜索
    query_vector = np.array([1.0, 0.0, 0.0, 0.0])  # 查询向量，接近 id1
    top_k = 2
    string_ids, distances = faiss_backend.search(query_vector, top_k)

    # 预期结果
    expected_ids = ["id1", "id2"]  # id1 应该最接近，其次是 id2 或其他
    expected_distances = [0.0, 2.0]  # id1 完全匹配，距离为 0；id2 距离为 sqrt(2)^2=2

    # 实际结果
    print("预期结果:")
    print(f"  IDs: {expected_ids}")
    print(f"  Distances: {expected_distances}")
    print("实际结果:")
    print(f"  IDs: {string_ids}")
    print(f"  Distances: {distances.tolist()}")


