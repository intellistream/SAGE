# file sage/core/sage_memory/search_engine/vdb_index/faiss_index.py
# python -m sage.core.sage_memory.search_engine.vdb_index.faiss_index

import json
import faiss
import pickle
import numpy as np
from typing import Optional, List, Dict, Any
from sage_utils.custom_logger import CustomLogger
from sage.service.memory.search_engine.vdb_index.base_vdb_index import BaseVDBIndex
import os

class FaissIndex(BaseVDBIndex):
    def __init__(
        self, 
        name: str, 
        dim: int, 
        vectors: Optional[List[np.ndarray]] = None, 
        ids: Optional[List[str]] = None,
        config: Optional[dict] = None,
        load_path: Optional[str] = None,
        ):
        """
        初始化 FaissIndex 实例，设置索引名称、维度，并可选性地加载初始向量和ID
        Initialize the FaissIndex instance with name, dimension, and optionally preload vectors and ids.
        """
        self.index_name = name
        self.dim = dim
        self.config = config or {}
        self.id_map: Dict[int, str] = {}
        self.rev_map: Dict[str, int] = {}
        self.next_id: int = 1
        self.tombstones: set[str] = set()
        self._deletion_supported = True
        self.index = None
        self.logger = CustomLogger(
            filename=f"FaissIndex",
            console_output=False,
            file_output=True
        )
        if load_path is not None:
            self._load(load_path)
        else:
            self.index, self._deletion_supported = self._init_index()
            if vectors is not None and ids is not None:
                self._build_index(vectors, ids)

           
    def _init_index(self):
        config = self.config  # 保持全程都叫config
        index_type = config.get("index_type", "IndexFlatL2")

        # 基础索引
        if index_type == "IndexFlatL2":
            return faiss.IndexFlatL2(self.dim), True

        elif index_type == "IndexFlatIP":
            return faiss.IndexFlatIP(self.dim), True

        # HNSW
        elif index_type == "IndexHNSWFlat":
            hnsw_m = int(config.get("HNSW_M", 32))
            ef_construction = int(config.get("HNSW_EF_CONSTRUCTION", 200))
            index = faiss.IndexHNSWFlat(self.dim, hnsw_m)
            index.hnsw.efConstruction = ef_construction
            if "HNSW_EF_SEARCH" in config:
                index.hnsw.efSearch = int(config["HNSW_EF_SEARCH"])
            return index, False

        # IVF Flat
        elif index_type == "IndexIVFFlat":
            nlist = int(config.get("IVF_NLIST", 100))
            nprobe = int(config.get("IVF_NPROBE", 10))
            metric = self._get_metric(config.get("IVF_METRIC", "L2"))
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFFlat(quantizer, self.dim, nlist, metric)
            index.nprobe = nprobe
            return index, True

        # IVF PQ
        elif index_type == "IndexIVFPQ":
            nlist = int(config.get("IVF_NLIST", 100))
            nprobe = int(config.get("IVF_NPROBE", 10))
            m = int(config.get("PQ_M", 8))
            nbits = int(config.get("PQ_NBITS", 8))
            metric = self._get_metric(config.get("IVF_METRIC", "L2"))
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFPQ(quantizer, self.dim, nlist, m, nbits, metric)
            index.nprobe = nprobe
            return index, True

        # IVF ScalarQuantizer
        elif index_type == "IndexIVFScalarQuantizer":
            nlist = int(config.get("IVF_NLIST", 100))
            nprobe = int(config.get("IVF_NPROBE", 10))
            qtype_str = config.get("SQ_TYPE", "QT_8bit")
            qtype = getattr(faiss.ScalarQuantizer, qtype_str)
            metric = self._get_metric(config.get("IVF_METRIC", "L2"))
            quantizer = faiss.IndexFlatL2(self.dim)
            index = faiss.IndexIVFScalarQuantizer(quantizer, self.dim, nlist, qtype, metric)
            index.nprobe = nprobe
            return index, True

        # LSH
        elif index_type == "IndexLSH":
            nbits = int(config.get("LSH_NBITS", 512))
            rotate_data = bool(config.get("LSH_ROTATE_DATA", True))
            train_thresholds = bool(config.get("LSH_TRAIN_THRESHOLDS", False))
            index = faiss.IndexLSH(self.dim, nbits, rotate_data, train_thresholds)
            return index, False

        # PQ
        elif index_type == "IndexPQ":
            m = int(config.get("PQ_M", 8))
            nbits = int(config.get("PQ_NBITS", 8))
            metric = self._get_metric(config.get("PQ_METRIC", "L2"))
            return faiss.IndexPQ(self.dim, m, nbits, metric), False

        # ScalarQuantizer
        elif index_type == "IndexScalarQuantizer":
            qtype_str = config.get("SQ_TYPE", "QT_8bit")
            qtype = getattr(faiss.ScalarQuantizer, qtype_str)
            metric = self._get_metric(config.get("SQ_METRIC", "L2"))
            return faiss.IndexScalarQuantizer(self.dim, qtype, metric), True

        # RefineFlat
        elif index_type == "IndexRefineFlat":
            base_type = config.get("FAISS_BASE_INDEX_TYPE", "IndexFlatL2")
            # 临时切换 index_type, 递归用 config 初始化
            orig_type = config.get("index_type", None)
            config["index_type"] = base_type
            base_index, base_deletion_supported = self._init_index()
            if orig_type is not None:
                config["index_type"] = orig_type
            k_factor = float(config.get("REFINE_K_FACTOR", 1.0))
            return faiss.IndexRefineFlat(base_index, k_factor), True

        # IndexIDMap
        elif index_type == "IndexIDMap":
            base_type = config.get("FAISS_BASE_INDEX_TYPE", "IndexFlatL2")
            orig_type = config.get("index_type", None)
            config["index_type"] = base_type
            base_index, base_deletion_supported = self._init_index()
            if orig_type is not None:
                config["index_type"] = orig_type
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
            self.logger.info("Wrapping index with IndexIDMap")
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

    def store(self, dir_path: str) -> Dict[str, Any]:
            """
            将FAISS索引、参数和映射全部保存到指定目录。
            """
            os.makedirs(dir_path, exist_ok=True)
            # 1. 保存faiss主索引
            faiss.write_index(self.index, os.path.join(dir_path, "faiss.index"))
            # 2. 保存id映射
            with open(os.path.join(dir_path, "id_map.pkl"), "wb") as f:
                pickle.dump(self.id_map, f)
            with open(os.path.join(dir_path, "rev_map.pkl"), "wb") as f:
                pickle.dump(self.rev_map, f)
            with open(os.path.join(dir_path, "tombstones.pkl"), "wb") as f:
                pickle.dump(self.tombstones, f)
            # 3. 保存参数（如dim、下一个ID、自定义config等）
            meta = {
                "index_name": self.index_name,
                "dim": self.dim,
                "next_id": self.next_id,
                "deletion_supported": self._deletion_supported,
                "config": getattr(self, "config", {}),  # 若有config则保存
            }
            with open(os.path.join(dir_path, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            return {"index_path": dir_path}

    def _load(self, dir_path: str):
        """
        从目录恢复索引、映射与参数。仅供类方法load调用。
        """
        self.index = faiss.read_index(os.path.join(dir_path, "faiss.index"))
        with open(os.path.join(dir_path, "id_map.pkl"), "rb") as f:
            self.id_map = pickle.load(f)
        with open(os.path.join(dir_path, "rev_map.pkl"), "rb") as f:
            self.rev_map = pickle.load(f)
        with open(os.path.join(dir_path, "tombstones.pkl"), "rb") as f:
            self.tombstones = pickle.load(f)
        with open(os.path.join(dir_path, "meta.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.index_name = meta["index_name"]
        self.dim = meta["dim"]
        self.next_id = meta["next_id"]
        self._deletion_supported = meta.get("deletion_supported", True)
        self.config = meta.get("config", {})

    @classmethod
    def load(cls, name: str, load_path: str) -> "FaissIndex":
        """
        推荐方式，等价于 BM25sIndex.load
        """
        return cls(name=name, dim=0, load_path=load_path)  # dim会被_load覆盖

if __name__ == "__main__":
    import os
    import shutil
    import numpy as np

    def colored(text, color):
        # color: "green", "red", "yellow"
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
        return colors.get(color, "") + text + colors["reset"]

    def print_test_case(desc, expected_ids, expected_dists, actual_ids, actual_dists, digits=4):
        ids_pass = list(expected_ids) == list(actual_ids)
        dists_pass = all(abs(e-a) < 10**-digits for e,a in zip(expected_dists, actual_dists))
        status = "通过" if ids_pass and dists_pass else "不通过"
        color = "green" if status == "通过" else "red"
        print(f"【{desc}】")
        print(f"预期IDs：{expected_ids}")
        print(f"实际IDs：{actual_ids}")
        print(f"预期距离：{expected_dists}")
        print(f"实际距离：{[round(x, digits) for x in actual_dists]}")
        print(f"测试情况：{colored(status, color)}\n")

    # ==== 基础数据 ====
    dim = 4
    index_name = "test_index"
    root_dir = "./faiss_index_test"
    if os.path.exists(root_dir):
        shutil.rmtree(root_dir)
    os.makedirs(root_dir, exist_ok=True)

    vectors = [
        np.array([1.0, 0.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0, 0.0])
    ]
    ids = ["id1", "id2", "id3"]

    index = FaissIndex(name=index_name, dim=dim, vectors=vectors, ids=ids)
    # 1. 检索
    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    r_ids, r_dists = index.search(q1, 3)
    print_test_case("基础检索", ["id1", "id2", "id3"], [0.0, 2.0, 2.0], r_ids, r_dists)

    # 2. 插入新向量
    index.insert(np.array([0.0, 0.0, 0.0, 1.0]), "id4")
    q2 = np.array([0.0, 0.0, 0.0, 1.0])
    r_ids, r_dists = index.search(q2, 4)
    print_test_case("插入后检索", ["id4", "id1", "id2", "id3"], [0.0, 2.0, 2.0, 2.0], r_ids, r_dists)

    # 3. 更新向量
    index.update("id1", np.array([0.5, 0.5, 0.0, 0.0]))
    q3 = np.array([0.5, 0.5, 0.0, 0.0])
    r_ids, r_dists = index.search(q3, 4)
    print_test_case("更新后检索", ['id1', 'id2', 'id3', 'id4'], [0.0, 0.5, 1.5, 1.5], r_ids, r_dists)

    # 4. 删除向量
    index.delete("id2")
    q4 = np.array([1.0, 0.0, 0.0, 0.0])
    r_ids, r_dists = index.search(q4, 4)
    print_test_case("删除后检索", ['id1', 'id3', 'id4'], [0.5, 2.0, 2.0], r_ids, r_dists)

    # 5. 批量插入
    index.batch_insert([
        np.array([0.1, 0.1, 0.1, 0.1]),
        np.array([0.2, 0.2, 0.2, 0.2])
    ], ["id5", "id6"])
    q5 = np.array([0.1, 0.1, 0.1, 0.1])
    r_ids, r_dists = index.search(q5, 6)
    print_test_case("批量插入后检索", ['id5', 'id6', 'id1', 'id3', 'id4'], [0.0, 0.04, 0.34, 0.84, 0.84], r_ids[:5], r_dists[:5], 2)

    # ==== 持久化保存 ====
    print(colored("\n--- 保存索引到磁盘 ---", "yellow"))
    index.store(root_dir)
    print(colored(f"数据已保存到目录: {root_dir}", "yellow"))

    # ==== 内存对象清空 ====
    del index
    print(colored("内存对象已清除。", "yellow"))

    # ==== 读取并检索 ====
    user_input = input(colored("输入 yes 加载刚才保存的数据: ", "yellow"))
    if user_input.strip().lower() == "yes":
        index2 = FaissIndex.load(index_name, root_dir)
        print(colored("数据已从磁盘恢复！", "green"))

        r_ids, r_dists = index2.search(np.array([0.1, 0.1, 0.1, 0.1]), 5)
        print_test_case("恢复后检索", ["id5", "id6", "id1", "id3", "id4"], [0.0, 0.04, 0.34, 0.84, 0.84], r_ids, r_dists, 2)
    else:
        print(colored("跳过加载测试。", "yellow"))

    # ==== 清除磁盘数据 ====
    user_input = input(colored("输入 yes 删除磁盘所有数据: ", "yellow"))
    if user_input.strip().lower() == "yes":
        shutil.rmtree(root_dir)
        print(colored("所有数据已删除！", "green"))
    else:
        print(colored("未执行删除。", "yellow"))


