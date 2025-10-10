import json
import os
import pickle
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sage.common.utils.logging.custom_logger import CustomLogger

from .base_vdb_index import (
    BaseVDBIndex,
)


class FaissIndex(BaseVDBIndex):
    def __init__(self, config: Optional[dict]):
        super().__init__()
        """
        初始化 FaissIndex 实例，支持两种初始化方式：
        1. 通过声明来创建：传入 config
        2. 通过 FaissIndex.load() 来加载：调用load方法

        Initialize the FaissIndex instance with two initialization methods:
        1. Creation: by config and new
        2. Load from disk: use load method
        """
        self.logger = CustomLogger()

        if config is None:
            raise ValueError("Config cannot be None for FaissIndex initialization")
        self.config = config

        # 从config中获取必要参数
        self.index_name = self.config.get("name", None)
        if self.index_name is None:
            self.logger.error(
                "The index name is not specified in the config, so the index cannot be created."
            )
            raise ValueError(
                "The index name is not specified in the config, so the index cannot be created."
            )

        self.dim = self.config.get("dim", 128)
        self.id_map: Dict[int, str] = {}
        self.rev_map: Dict[str, int] = {}
        self.next_id: int = 1
        self.tombstones: set[str] = set()
        self.tombstone_threshold = self.config.get("tombstone_threshold", 30)
        self.index, self._deletion_supported = self._init_index()

        # 确保索引被IndexIDMap包装以支持自定义ID
        if not isinstance(self.index, faiss.IndexIDMap):
            self.logger.info("Wrapping index with IndexIDMap")
            self.index = faiss.IndexIDMap(self.index)

        # 用于检测重复向量的容器
        self.vector_hashes: Dict[str, str] = {}  # vector_hash -> string_id

        # 存储向量副本用于重建索引
        self.vector_store: Dict[str, np.ndarray] = {}  # string_id -> vector

    def _init_index(self):
        config = self.config  # 保持全程都叫config
        index_type = config.get(
            "index_type", "IndexFlatIP"
        )  # 默认使用Inner Product以支持归一化向量

        # 确保index_type被存储到config中，以便后续搜索时使用
        config["index_type"] = index_type

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
            index = faiss.IndexIVFScalarQuantizer(
                quantizer, self.dim, nlist, qtype, metric
            )
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

    def _get_vector_hash(self, vector: np.ndarray) -> str:
        """
        计算向量的哈希值用于检测重复
        Calculate vector hash for duplicate detection
        """
        import hashlib

        return hashlib.md5(vector.tobytes()).hexdigest()

    def _rebuild_index_if_needed(self):
        """
        当墓碑数量达到阈值时重建索引
        Rebuild index when tombstone count reaches threshold
        """
        if len(self.tombstones) < self.tombstone_threshold:
            return

        self.logger.warning(
            f"墓碑数量({len(self.tombstones)})达到阈值({self.tombstone_threshold})，开始重建索引"
        )

        # 收集有效的向量和ID
        valid_vectors = []
        valid_ids = []
        new_id_map = {}
        new_rev_map = {}
        new_vector_hashes = {}
        new_vector_store = {}

        next_id = 1
        for string_id, vector in self.vector_store.items():
            if string_id not in self.tombstones:
                valid_vectors.append(vector)
                valid_ids.append(string_id)

                new_rev_map[string_id] = next_id
                new_id_map[next_id] = string_id
                new_vector_store[string_id] = vector

                vector_hash = self._get_vector_hash(vector)
                new_vector_hashes[vector_hash] = string_id

                next_id += 1

        if valid_vectors:
            # 重新创建索引
            self.index, self._deletion_supported = self._init_index()
            if not isinstance(self.index, faiss.IndexIDMap):
                self.index = faiss.IndexIDMap(self.index)

            # 批量添加有效向量
            np_vectors = np.vstack(valid_vectors).astype("float32")
            int_ids_np = np.array(
                [new_rev_map[sid] for sid in valid_ids], dtype=np.int64
            )
            self.index.add_with_ids(np_vectors, int_ids_np)
        else:
            # 如果没有有效向量，创建空索引
            self.index, self._deletion_supported = self._init_index()
            if not isinstance(self.index, faiss.IndexIDMap):
                self.index = faiss.IndexIDMap(self.index)

        # 更新映射关系
        self.id_map = new_id_map
        self.rev_map = new_rev_map
        self.vector_hashes = new_vector_hashes
        self.vector_store = new_vector_store
        self.next_id = next_id
        self.tombstones.clear()

        self.logger.info(f"索引重建完成，保留{len(valid_ids)}个有效向量，墓碑已清零")

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

        # 存储向量副本和哈希
        for vector, string_id in zip(vectors, ids):
            self.vector_store[string_id] = vector.astype("float32").flatten()
            vector_hash = self._get_vector_hash(vector)
            self.vector_hashes[vector_hash] = string_id

    def delete(self, string_id: str) -> int:
        """
        删除指定ID（物理删除或墓碑标记）
        Delete by ID (physical removal or tombstone marking)

        Returns:
            1: 删除成功
            0: 删除失败（ID不存在）
        """
        if string_id not in self.rev_map:
            self.logger.warning(f"尝试删除不存在的ID: {string_id}")
            return 0

        int_id = self.rev_map[string_id]

        if self._deletion_supported:
            try:
                id_vector = np.array([int_id], dtype=np.int64)
                self.index.remove_ids(id_vector)  # type: ignore
                # 清理映射关系
                del self.rev_map[string_id]
                del self.id_map[int_id]
                # 清理向量哈希和存储
                vector_hash_to_remove = None
                for vh, sid in self.vector_hashes.items():
                    if sid == string_id:
                        vector_hash_to_remove = vh
                        break
                if vector_hash_to_remove:
                    del self.vector_hashes[vector_hash_to_remove]
                if string_id in self.vector_store:
                    del self.vector_store[string_id]
                self.logger.info(f"成功删除ID: {string_id}")
                return 1
            except Exception as e:
                self.logger.warning(f"物理删除失败，转为墓碑标记: {e}")
                self.tombstones.add(string_id)
        else:
            self.tombstones.add(string_id)

        # 检查是否需要重建索引
        self._rebuild_index_if_needed()
        self.logger.info(f"ID {string_id} 已标记为墓碑")
        return 1

    def update(self, string_id: str, new_vector: np.ndarray) -> int:
        """
        更新指定 ID 的向量：保持原有映射关系，仅替换向量内容
        Update the vector for the given ID, preserving the existing ID mapping.

        Returns:
            1: 更新成功
            0: 更新失败
        """
        if string_id not in self.rev_map:
            # 如果ID不存在，直接插入
            self.logger.info(f"ID {string_id} 不存在，将执行插入操作")
            return self.insert(new_vector, string_id)

        int_id = self.rev_map[string_id]

        # 检查新向量是否与其他向量重复
        new_vector_hash = self._get_vector_hash(new_vector)
        if (
            new_vector_hash in self.vector_hashes
            and self.vector_hashes[new_vector_hash] != string_id
        ):
            self.logger.warning(
                f"更新失败: 向量与已存在的ID {self.vector_hashes[new_vector_hash]} 重复"
            )
            return 0

        if self._deletion_supported:
            try:
                # 删除旧向量并插入新向量 / Remove old vector and insert new one
                id_vector = np.array([int_id], dtype=np.int64)
                self.index.remove_ids(id_vector)  # type: ignore
                vector = np.expand_dims(new_vector.astype("float32"), axis=0)
                int_id_np = np.array([int_id], dtype=np.int64)
                self.index.add_with_ids(vector, int_id_np)  # type: ignore

                # 更新向量哈希和存储
                old_hash_to_remove = None
                for vh, sid in self.vector_hashes.items():
                    if sid == string_id:
                        old_hash_to_remove = vh
                        break
                if old_hash_to_remove:
                    del self.vector_hashes[old_hash_to_remove]
                self.vector_hashes[new_vector_hash] = string_id
                self.vector_store[string_id] = new_vector.astype("float32").flatten()

                self.logger.info(f"成功更新ID: {string_id}")
                return 1
            except Exception as e:
                self.logger.error(f"更新失败: {e}")
                return 0
        else:
            # 对于不支持删除的索引，删除旧映射并创建新映射
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

            # 更新向量哈希和存储
            old_hash_to_remove = None
            for vh, sid in self.vector_hashes.items():
                if sid == string_id:
                    old_hash_to_remove = vh
                    break
            if old_hash_to_remove:
                del self.vector_hashes[old_hash_to_remove]
            self.vector_hashes[new_vector_hash] = string_id
            self.vector_store[string_id] = new_vector.astype("float32").flatten()

            self.logger.info(f"成功更新ID: {string_id}")
            return 1

    def search(
        self,
        query_vector: np.ndarray,
        topk: int = 10,
        threshold: Optional[float] = None,
    ):
        """
        向量检索 / Vector search
        返回top_k结果（过滤墓碑） / Return top_k results (filter tombstones)

        Args:
            query_vector: 查询向量
            topk: 返回结果数量
            threshold: 相似度阈值，低于此阈值的结果将被过滤（适用于归一化向量）

        Returns:
            tuple: (结果IDs, 相似度列表)
        """
        # 检查索引是否为空
        if self.index.ntotal == 0:
            self.logger.warning("索引为空，无法进行检索")
            return [], []

        query_vector = np.expand_dims(query_vector.astype("float32"), axis=0)

        # 考虑墓碑数量，多查询一些结果
        search_k = topk + len(self.tombstones)
        if search_k > self.index.ntotal:
            search_k = self.index.ntotal

        distances, int_ids = self.index.search(query_vector, search_k)  # type: ignore

        results = []
        filtered_distances = []

        for i, dist in zip(int_ids[0], distances[0]):
            if i == -1:  # FAISS 空槽位标记
                continue
            string_id = self.id_map.get(i)
            if string_id and string_id not in self.tombstones:
                # 应用阈值过滤：根据索引类型决定过滤逻辑
                should_filter = False
                if threshold is not None:
                    # 对于IndexFlatIP（内积），距离越大表示越相似，应该保留距离大于阈值的结果
                    # 对于IndexFlatL2（L2距离），距离越小表示越相似，应该保留距离小于阈值的结果
                    index_type = self.config.get("index_type", "IndexFlatIP")
                    if "IP" in index_type:  # Inner Product类型索引
                        if dist < threshold:  # 内积小于阈值，相似度低，过滤
                            should_filter = True
                    else:  # L2距离类型索引
                        if dist > threshold:  # L2距离大于阈值，相似度低，过滤
                            should_filter = True
                if not should_filter:
                    results.append(string_id)
                    filtered_distances.append(float(dist))  # 显式转为Python float
            if len(results) >= topk:
                break

        # 检查结果数量并给出警告
        available_count = len(
            [sid for sid in self.id_map.values() if sid not in self.tombstones]
        )
        if len(results) < topk and len(results) < available_count:
            self.logger.warning(f"期望返回{topk}个结果，实际只找到{len(results)}个结果")

        if threshold is not None and len(results) == 0:
            self.logger.warning(f"在阈值{threshold}限制下，未找到任何结果")

        return results, filtered_distances

    def insert(self, vector: np.ndarray, string_id: str) -> int:
        """
        插入单个向量及其字符串 ID 到索引中
        Insert a single vector and its string ID into the index

        Returns:
            1: 插入成功
            0: 插入失败（向量重复或ID已存在）
        """
        # 检查ID是否已存在且不在墓碑中
        if string_id in self.rev_map and string_id not in self.tombstones:
            self.logger.warning(f"ID {string_id} 已存在，无法插入")
            return 0

        # 检查向量是否重复
        vector_hash = self._get_vector_hash(vector)
        if vector_hash in self.vector_hashes:
            existing_id = self.vector_hashes[vector_hash]
            if existing_id not in self.tombstones:  # 确保现有ID未被删除
                self.logger.warning(
                    f"向量重复: 尝试插入的向量与已存在的ID {existing_id} 相同"
                )
                return 0

        # 如果是墓碑状态的ID，复用其int_id
        if string_id in self.rev_map and string_id in self.tombstones:
            int_id = self.rev_map[string_id]
            self.tombstones.remove(string_id)  # 移除墓碑标记
        else:
            int_id = self.next_id
            self.next_id += 1
            self.rev_map[string_id] = int_id
            self.id_map[int_id] = string_id

        vector = np.expand_dims(vector.astype("float32"), axis=0)
        int_id_np = np.array([int_id], dtype=np.int64)
        self.index.add_with_ids(vector, int_id_np)  # type: ignore

        # 记录向量哈希和存储向量副本
        self.vector_hashes[vector_hash] = string_id
        self.vector_store[string_id] = vector.astype("float32").flatten()  # 存储1D副本

        self.logger.info(f"成功插入向量，ID: {string_id}")
        return 1

    def batch_insert(self, vectors: List[np.ndarray], string_ids: List[str]) -> int:
        """
        批量插入多个向量及其对应的 string_id
        Batch insert multiple vectors and their corresponding string_id

        Returns:
            成功插入的向量数量
        """
        assert len(vectors) == len(string_ids), "Vectors and IDs must match in length"

        valid_vectors = []
        valid_ids = []
        success_count = 0

        for vector, string_id in zip(vectors, string_ids):
            # 检查向量是否重复
            vector_hash = self._get_vector_hash(vector)
            if vector_hash in self.vector_hashes:
                existing_id = self.vector_hashes[vector_hash]
                self.logger.warning(
                    f"跳过重复向量: ID {string_id} 的向量与已存在的ID {existing_id} 相同"
                )
                continue

            valid_vectors.append(vector)
            valid_ids.append(string_id)

        if not valid_vectors:
            self.logger.warning("批量插入：所有向量都重复，没有插入任何向量")
            return 0

        np_vectors = np.vstack(valid_vectors).astype("float32")
        int_ids = []

        for string_id in valid_ids:
            if string_id in self.rev_map:
                int_id = self.rev_map[string_id]
            else:
                int_id = self.next_id
                self.next_id += 1
                self.rev_map[string_id] = int_id
                self.id_map[int_id] = string_id
            int_ids.append(int_id)

        int_ids_np = np.array(int_ids, dtype=np.int64)

        # 确保索引被IDMap包装
        if not isinstance(self.index, faiss.IndexIDMap):
            self.logger.info("Wrapping index with IndexIDMap")
            self.index = faiss.IndexIDMap(self.index)

        self.index.add_with_ids(np_vectors, int_ids_np)  # type: ignore

        # 记录向量哈希和存储
        for vector, string_id in zip(valid_vectors, valid_ids):
            vector_hash = self._get_vector_hash(vector)
            self.vector_hashes[vector_hash] = string_id
            self.vector_store[string_id] = vector.astype("float32").flatten()

        success_count = len(valid_vectors)
        self.logger.info(f"批量插入完成，成功插入 {success_count} 个向量")
        return success_count

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
        with open(os.path.join(dir_path, "vector_hashes.pkl"), "wb") as f:
            pickle.dump(self.vector_hashes, f)
        with open(os.path.join(dir_path, "vector_store.pkl"), "wb") as f:
            pickle.dump(self.vector_store, f)
        # 3. 保存参数（如dim、下一个ID、自定义config等）
        meta = {
            "index_name": self.index_name,
            "dim": self.dim,
            "next_id": self.next_id,
            "deletion_supported": self._deletion_supported,
            "tombstone_threshold": self.tombstone_threshold,
            "config": getattr(self, "config", {}),  # 若有config则保存
        }
        with open(os.path.join(dir_path, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return {"index_path": dir_path}

    def _load_data(self, dir_path: str):
        """
        从目录加载索引文件和映射数据。仅供load类方法调用。
        """
        # 加载faiss索引
        self.index = faiss.read_index(os.path.join(dir_path, "faiss.index"))

        # 加载ID映射
        with open(os.path.join(dir_path, "id_map.pkl"), "rb") as f:
            self.id_map = pickle.load(f)
        with open(os.path.join(dir_path, "rev_map.pkl"), "rb") as f:
            self.rev_map = pickle.load(f)
        with open(os.path.join(dir_path, "tombstones.pkl"), "rb") as f:
            self.tombstones = pickle.load(f)

        # 加载向量哈希（如果存在）
        vector_hashes_path = os.path.join(dir_path, "vector_hashes.pkl")
        if os.path.exists(vector_hashes_path):
            with open(vector_hashes_path, "rb") as f:
                self.vector_hashes = pickle.load(f)
        else:
            self.vector_hashes = {}

        # 加载向量存储（如果存在）
        vector_store_path = os.path.join(dir_path, "vector_store.pkl")
        if os.path.exists(vector_store_path):
            with open(vector_store_path, "rb") as f:
                self.vector_store = pickle.load(f)
        else:
            self.vector_store = {}

    @classmethod
    def load(cls, name: str, load_path: str) -> "FaissIndex":
        """
        从指定路径加载索引，name参数用于验证
        """
        # 读取meta.json获取保存的参数
        meta_path = os.path.join(load_path, "meta.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # 验证索引名称
        saved_name = meta["index_name"]
        if name != saved_name:
            raise ValueError(f"索引名称不匹配: 期望 {name}, 实际 {saved_name}")

        # 创建实例但不调用__init__，避免重复初始化索引
        instance = cls.__new__(cls)
        super(FaissIndex, instance).__init__()

        # 直接设置从存储中恢复的属性
        instance.config = meta.get("config", {})
        instance.logger = CustomLogger()
        instance.index_name = saved_name
        instance.dim = meta["dim"]
        instance.next_id = meta["next_id"]
        instance._deletion_supported = meta.get("deletion_supported", True)
        instance.tombstone_threshold = meta.get("tombstone_threshold", 30)
        instance.vector_hashes = {}  # 将在_load_data中加载
        instance.vector_store = {}  # 将在_load_data中加载

        # 加载保存的数据
        instance._load_data(load_path)
        return instance


if __name__ == "__main__":
    import os
    import shutil

    import numpy as np

    def colored(text, color):
        # color: "green", "red", "yellow"
        colors = {
            "green": "\033[92m",
            "red": "\033[91m",
            "yellow": "\033[93m",
            "reset": "\033[0m",
        }
        return colors.get(color, "") + text + colors["reset"]

    def print_test_case(
        desc, expected_ids, expected_dists, actual_ids, actual_dists, digits=4
    ):
        ids_pass = list(expected_ids) == list(actual_ids)
        dists_pass = all(
            abs(e - a) < 10**-digits for e, a in zip(expected_dists, actual_dists)
        )
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
        np.array([0.0, 0.0, 1.0, 0.0]),
    ]
    ids = ["id1", "id2", "id3"]

    # 使用新的初始化方式
    config = {
        "name": index_name,
        "dim": dim,
        "tombstone_threshold": 2,
    }  # 设置较小的墓碑阈值用于测试
    index = FaissIndex(config=config)

    # 先插入初始数据
    for vector, vector_id in zip(vectors, ids):
        result = index.insert(vector, vector_id)
        if result != 1:
            print(f"初始插入失败: {vector_id}")

    # 1. 检索
    q1 = np.array([1.0, 0.0, 0.0, 0.0])
    r_ids, r_dists = index.search(q1, 3)
    print_test_case("基础检索", ["id1", "id2", "id3"], [0.0, 2.0, 2.0], r_ids, r_dists)

    # 2. 插入新向量
    result = index.insert(np.array([0.0, 0.0, 0.0, 1.0]), "id4")
    print(f"插入结果: {result} (期望: 1)")
    q2 = np.array([0.0, 0.0, 0.0, 1.0])
    r_ids, r_dists = index.search(q2, 4)
    print_test_case(
        "插入后检索", ["id4", "id1", "id2", "id3"], [0.0, 2.0, 2.0, 2.0], r_ids, r_dists
    )

    # 3. 测试重复向量插入
    result = index.insert(np.array([0.0, 0.0, 0.0, 1.0]), "id5")  # 重复向量
    print(f"重复向量插入结果: {result} (期望: 0)")

    # 4. 更新向量
    result = index.update("id1", np.array([0.5, 0.5, 0.0, 0.0]))
    print(f"更新结果: {result} (期望: 1)")
    q3 = np.array([0.5, 0.5, 0.0, 0.0])
    r_ids, r_dists = index.search(q3, 4)
    print_test_case(
        "更新后检索", ["id1", "id2", "id3", "id4"], [0.0, 0.5, 1.5, 1.5], r_ids, r_dists
    )

    # 5. 删除向量
    result = index.delete("id2")
    print(f"删除结果: {result} (期望: 1)")
    q4 = np.array([1.0, 0.0, 0.0, 0.0])
    r_ids, r_dists = index.search(q4, 4)
    print_test_case(
        "删除后检索", ["id1", "id3", "id4"], [0.5, 2.0, 2.0], r_ids, r_dists
    )

    # 6. 测试阈值检索
    r_ids, r_dists = index.search(q4, 4, threshold=1.0)
    print_test_case("阈值检索(threshold=1.0)", ["id1"], [0.5], r_ids, r_dists)

    # 7. 批量插入
    count = index.batch_insert(
        [np.array([0.1, 0.1, 0.1, 0.1]), np.array([0.2, 0.2, 0.2, 0.2])], ["id5", "id6"]
    )
    print(f"批量插入结果: {count} (期望: 2)")
    q5 = np.array([0.1, 0.1, 0.1, 0.1])
    r_ids, r_dists = index.search(q5, 6)
    print_test_case(
        "批量插入后检索",
        ["id5", "id6", "id1", "id3", "id4"],
        [0.0, 0.04, 0.34, 0.84, 0.84],
        r_ids[:5],
        r_dists[:5],
        2,
    )

    # 8. 测试墓碑阈值重建（删除多个向量触发重建）
    print(colored("\n--- 测试墓碑阈值重建 ---", "yellow"))
    index.delete("id3")  # 第二个删除
    index.delete("id4")  # 第三个删除，应该触发重建

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

        # 注意：id3和id4已被删除并保存为墓碑，所以恢复后不会出现在结果中
        r_ids, r_dists = index2.search(np.array([0.1, 0.1, 0.1, 0.1]), 5)
        print_test_case(
            "恢复后检索", ["id5", "id6", "id1"], [0.0, 0.04, 0.34], r_ids, r_dists, 2
        )

        # 验证墓碑状态
        print(f"当前墓碑数量: {len(index2.tombstones)}")
        print(f"墓碑内容: {index2.tombstones}")
    else:
        print(colored("跳过加载测试。", "yellow"))

    # ==== 清除磁盘数据 ====
    user_input = input(colored("输入 yes 删除磁盘所有数据: ", "yellow"))
    if user_input.strip().lower() == "yes":
        shutil.rmtree(root_dir)
        print(colored("所有数据已删除！", "green"))
    else:
        print(colored("未执行删除。", "yellow"))
