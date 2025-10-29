"""
Usage 3: MemoryService Integration
==================================

将 unlearning 集成到 MemoryService 中。

适用场景：
- RAG 系统中的隐私遗忘
- 需要从 VDB 中检索和更新向量
- 与记忆管理系统集成
- 完整的数据生命周期管理

优势：
- 与 VDB collection 无缝集成
- 支持向量检索和更新
- 遗忘操作的持久化
- 隐私预算管理
"""

import os
from typing import Any

import numpy as np

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.service.base_service import BaseService
from sage.libs.unlearning import UnlearningEngine
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager


class DPMemoryService(BaseService):
    """
    带差分隐私的内存服务

    支持使用 DP 遗忘操作从 VDB 中安全删除数据。
    """

    def __init__(
        self, data_dir: str | None = None, epsilon: float = 1.0, delta: float = 1e-5
    ):
        super().__init__()

        # 初始化内存管理器
        if data_dir is None:
            data_dir = os.path.join(os.getcwd(), "data", "dp_memory_service")
        os.makedirs(data_dir, exist_ok=True)

        self.manager = MemoryManager(data_dir)
        self.logger.info(f"Initialized DPMemoryService with data_dir={data_dir}")

        # 初始化 DP unlearning engine
        self.unlearning_engine = UnlearningEngine(
            epsilon=epsilon,
            delta=delta,
            total_budget_epsilon=100.0,
            enable_compensation=True,
        )

        self.logger.info(f"Initialized UnlearningEngine with ε={epsilon}, δ={delta}")

    def create_collection(
        self, collection_name: str, config: dict | None = None
    ) -> bool:
        """创建 VDB collection"""
        try:
            if config is None:
                config = {
                    "name": collection_name,
                    "backend_type": "VDB",
                    "description": f"DP-enabled collection: {collection_name}",
                }

            collection = self.manager.create_collection(config)

            if collection is None:
                self.logger.warning(f"Failed to create collection: {collection_name}")
                return False

            # 创建默认索引
            index_config = {
                "name": "global_index",
                "embedding_model": "mockembedder",
                "dim": 128,
                "backend_type": "FAISS",
                "description": "Global index for similarity search",
            }
            collection.create_index(index_config)  # type: ignore[attr-defined]
            collection.init_index("global_index")  # type: ignore[attr-defined]

            self.logger.info(f"✓ Created collection: {collection_name}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating collection: {e}")
            return False

    def store_memory(
        self,
        collection_name: str,
        content: str,
        vector: np.ndarray,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        存储记忆到 VDB collection

        Args:
            collection_name: Collection 名称
            content: 文本内容
            vector: 向量表示
            metadata: 元数据

        Returns:
            Memory ID 或 None
        """
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                self.logger.error(f"Collection not found: {collection_name}")
                return None

            # 使用 insert 方法存储数据
            # VDBMemoryCollection.insert 使用 (index_name, raw_data, metadata)
            memory_id = collection.insert(
                index_name="global_index", raw_data=content, metadata=metadata
            )

            self.logger.debug(f"Stored memory: {memory_id}")
            return memory_id

        except Exception as e:
            self.logger.error(f"Error storing memory: {e}")
            return None

    def retrieve_memories(
        self, collection_name: str, query_text: str, topk: int = 5
    ) -> list[dict[str, Any]]:
        """
        检索相似的记忆

        Args:
            collection_name: Collection 名称
            query_text: 查询文本
            topk: 返回结果数量

        Returns:
            相似记忆列表
        """
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                self.logger.error(f"Collection not found: {collection_name}")
                return []

            results = collection.retrieve(  # type: ignore[call-arg]
                raw_data=query_text,
                index_name="global_index",
                topk=topk,
                with_metadata=True,
            )

            return results  # type: ignore[return-value]

        except Exception as e:
            self.logger.error(f"Error retrieving memories: {e}")
            return []

    def forget_with_dp(
        self,
        collection_name: str,
        memory_ids: list[str],
        perturbation_strategy: str = "adaptive",
    ) -> dict[str, Any]:
        """
        使用差分隐私遗忘指定的记忆

        Args:
            collection_name: Collection 名称
            memory_ids: 要遗忘的记忆 IDs
            perturbation_strategy: 扰动策略

        Returns:
            遗忘操作结果
        """
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                self.logger.error(f"Collection not found: {collection_name}")
                return {
                    "success": False,
                    "error": f"Collection not found: {collection_name}",
                }

            # 从 VDB index 获取要遗忘的向量
            index = collection.index_info.get("global_index", {}).get("index")  # type: ignore[attr-defined]
            if index is None:
                self.logger.error(f"Index not found in collection: {collection_name}")
                return {"success": False, "error": "Index not found"}

            vectors_to_forget = []
            valid_ids = []

            for mem_id in memory_ids:
                # 从 vector_store 获取向量
                if hasattr(index, "vector_store") and mem_id in index.vector_store:
                    vector = index.vector_store[mem_id]
                    vectors_to_forget.append(vector)
                    valid_ids.append(mem_id)
                else:
                    self.logger.warning(f"Vector not found for memory ID: {mem_id}")

            if not vectors_to_forget:
                self.logger.warning("No vectors found to forget")
                return {"success": False, "error": "No vectors found"}

            # 获取所有向量用于补偿
            all_vectors = []
            all_ids = []
            if hasattr(index, "vector_store"):
                for vid, vector in index.vector_store.items():
                    if (
                        vid
                        not in self.unlearning_engine.privacy_accountant.get_remaining_budget()
                    ):
                        all_vectors.append(vector)
                        all_ids.append(vid)

            vectors_array = np.array(vectors_to_forget)
            if all_vectors:
                all_vectors_array = np.array(all_vectors)
            else:
                all_vectors_array = vectors_array

            self.logger.info(f"Starting DP unlearning for {len(valid_ids)} memories...")

            # 执行 DP 遗忘
            result = self.unlearning_engine.unlearn_vectors(
                vectors_to_forget=vectors_array,
                vector_ids_to_forget=valid_ids,
                all_vectors=all_vectors_array,
                all_vector_ids=all_ids,
                perturbation_strategy=perturbation_strategy,
            )

            if not result.success:
                error_msg = result.metadata.get("error", "Unknown error")
                self.logger.error(f"Unlearning failed: {error_msg}")
                return {"success": False, "error": error_msg}

            # 获取扰动后的向量
            perturbed_vectors = result.metadata.get("perturbed_vectors", [])

            # 更新 VDB 中的向量
            updated_count = 0
            for mem_id, perturbed_vec in zip(valid_ids, perturbed_vectors):
                try:
                    # 更新向量
                    if hasattr(index, "update"):
                        index.update(mem_id, perturbed_vec)
                    else:
                        # 备选：删除后重新插入
                        index.delete(mem_id)
                        index.insert(perturbed_vec, mem_id)
                    updated_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to update vector for {mem_id}: {e}")

            # 持久化更改
            self.manager.store_collection(collection_name)

            self.logger.info(f"✓ Successfully forgotten {updated_count} memories")

            # 返回结果
            status = self.unlearning_engine.get_privacy_status()
            remaining = status["remaining_budget"]

            return {
                "success": True,
                "num_forgotten": updated_count,
                "privacy_cost": {
                    "epsilon": result.privacy_cost[0],
                    "delta": result.privacy_cost[1],
                },
                "remaining_budget": {
                    "epsilon": remaining["epsilon_remaining"],
                    "delta": remaining["delta_remaining"],
                },
                "budget_utilization": status["accountant_summary"][
                    "budget_utilization"
                ],
            }

        except Exception as e:
            self.logger.error(f"Error in forget_with_dp: {e}")
            return {"success": False, "error": str(e)}

    def get_privacy_status(self) -> dict[str, Any]:
        """获取当前隐私预算状态"""
        return self.unlearning_engine.get_privacy_status()


def example_basic_dp_memory():
    """示例1：基础 DP Memory Service"""
    print("\n" + "=" * 70)
    print("Example 1: Basic DP Memory Service")
    print("=" * 70)

    # 创建服务
    service = DPMemoryService(epsilon=1.0, delta=1e-5)

    # 创建 collection
    service.create_collection("documents")

    # 存储一些记忆
    print("\n📝 Storing memories...")
    memory_ids = []
    for i in range(5):
        content = f"This is document {i} with sensitive information"
        vector = np.random.randn(128).astype(np.float32)
        vector = vector / (np.linalg.norm(vector) + 1e-10)
        metadata = {"doc_index": i, "category": "sensitive" if i % 2 == 0 else "normal"}

        mem_id = service.store_memory(
            collection_name="documents",
            content=content,
            vector=vector,
            metadata=metadata,
        )
        if mem_id:
            memory_ids.append(mem_id)
            print(f"  ✓ Stored memory {i}: {mem_id[:8]}...")

    # 检索
    print("\n🔍 Retrieving memories...")
    results = service.retrieve_memories("documents", "document information", topk=3)
    print(f"  Found {len(results)} results")

    # 遗忘其中一些
    print("\n🔒 Forgetting sensitive documents...")
    if memory_ids:
        forget_ids = memory_ids[::2]  # 每隔一个遗忘
        result = service.forget_with_dp(
            collection_name="documents",
            memory_ids=forget_ids,
            perturbation_strategy="selective",
        )

        print(f"  Success: {result['success']}")
        if result["success"]:
            print(f"  Forgotten: {result['num_forgotten']} documents")
            print(f"  Privacy cost: ε={result['privacy_cost']['epsilon']:.4f}")
            print(f"  Remaining budget: ε={result['remaining_budget']['epsilon']:.4f}")

    print()


def example_privacy_budget_management():
    """示例2：隐私预算管理"""
    print("\n" + "=" * 70)
    print("Example 2: Privacy Budget Management")
    print("=" * 70)

    service = DPMemoryService(epsilon=0.5, delta=1e-5)
    service.create_collection("sensitive_data")

    # 创建测试数据
    memory_ids = []
    for i in range(10):
        content = f"Document {i}"
        vector = np.random.randn(128).astype(np.float32)
        vector = vector / (np.linalg.norm(vector) + 1e-10)
        mem_id = service.store_memory("sensitive_data", content, vector)
        if mem_id:
            memory_ids.append(mem_id)

    print("\n📊 Privacy Budget Tracking:")

    # 多次遗忘操作
    forget_count = 0
    for batch_idx in range(3):
        # 每批遗忘 2 个
        batch_ids = memory_ids[batch_idx * 2 : (batch_idx + 1) * 2]
        if not batch_ids:
            break

        result = service.forget_with_dp(
            collection_name="sensitive_data",
            memory_ids=batch_ids,
            perturbation_strategy="uniform",
        )

        forget_count += 1

        if result["success"]:
            print(f"  Batch {forget_count}: Success")
            print(f"    Forgotten: {result['num_forgotten']}")
            print(f"    Remaining ε: {result['remaining_budget']['epsilon']:.4f}")
        else:
            print(f"  Batch {forget_count}: Failed - {result['error']}")
            break

    print()


def example_multi_collection():
    """示例3：多 Collection 管理"""
    print("\n" + "=" * 70)
    print("Example 3: Multi-Collection Management")
    print("=" * 70)

    service = DPMemoryService(epsilon=1.0)

    # 创建多个 collection
    collections = ["public", "internal", "confidential"]
    for col_name in collections:
        service.create_collection(col_name)
        print(f"  ✓ Created collection: {col_name}")

    # 向不同 collection 存储数据
    print("\n📝 Storing data to different collections...")
    for col_name in collections:
        for i in range(3):
            content = f"{col_name} document {i}"
            vector = np.random.randn(128).astype(np.float32)
            vector = vector / (np.linalg.norm(vector) + 1e-10)
            mem_id = service.store_memory(col_name, content, vector)
            if mem_id:
                print(f"  ✓ {col_name}: {mem_id[:8]}...")

    # 从 confidential collection 遗忘一些数据
    print("\n🔒 Forgetting from confidential collection...")
    results = service.retrieve_memories("confidential", "document", topk=2)
    if results:
        # 获取第一个结果的 ID（这是一个简化版，实际需要追踪 ID）
        print(f"  Found {len(results)} documents in confidential collection")

    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("SAGE Unlearning Library - MemoryService Integration")
    print("=" * 70)
    print("\n这些示例展示了如何将 unlearning 集成到 MemoryService。")
    print("适合：RAG 系统的隐私遗忘、VDB 集成、数据生命周期管理\n")

    # 禁用调试日志
    CustomLogger.disable_global_console_debug()

    # 运行示例
    example_basic_dp_memory()
    example_privacy_budget_management()
    example_multi_collection()

    print("=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print("  1. Integrate with real embedding models")
    print("  2. Implement custom forgetting policies")
    print("  3. See basic_unlearning_demo.py for full RAG example\n")


if __name__ == "__main__":
    main()
