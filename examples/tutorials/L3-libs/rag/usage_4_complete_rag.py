"""
Usage 4: Complete RAG System with DP Unlearning
===============================================

完整的 RAG 系统中的隐私遗忘场景。

适用场景：
- 完整的 RAG Pipeline
- 用户请求删除数据
- 组织数据删除义务（GDPR 等）
- 恶意数据清理

特性：
- 检索 → 筛选 → 遗忘 → 更新 的完整流程
- 多个查询的批量处理
- 隐私预算跟踪
- 操作日志和审计
"""

import os
from datetime import datetime
from typing import Any

import numpy as np

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.service.base_service import BaseService
from sage.libs.privacy.unlearning import UnlearningEngine
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)


class RAGUnlearningSystem(BaseService):
    """RAG 系统中的隐私遗忘管理"""

    def __init__(self, data_dir: str | None = None, epsilon: float = 1.0):
        super().__init__()

        if data_dir is None:
            data_dir = os.path.join(os.getcwd(), "data", "rag_unlearning")
        os.makedirs(data_dir, exist_ok=True)

        self.data_dir = data_dir
        self.manager = MemoryManager(data_dir)
        self.unlearning_engine = UnlearningEngine(
            epsilon=epsilon,
            delta=1e-5,
            total_budget_epsilon=100.0,
            enable_compensation=True,
        )

        # 审计日志
        self.audit_log = []

        self.logger.info("RAGUnlearningSystem initialized")

    def initialize_rag_corpus(
        self, collection_name: str, documents: list[dict[str, Any]]
    ) -> bool:
        """
        初始化 RAG corpus

        Args:
            collection_name: Collection 名称
            documents: 文档列表，每个包含 'id', 'content', 'vector', 'metadata'

        Returns:
            是否成功
        """
        try:
            # 创建 collection
            collection = self.manager.create_collection(
                {
                    "name": collection_name,
                    "backend_type": "VDB",
                    "description": f"RAG corpus: {collection_name}",
                }
            )

            if collection is None:
                return False

            # 创建索引
            index_config = {
                "name": "content_index",
                "embedding_model": "mockembedder",
                "dim": 128,
                "backend_type": "FAISS",
                "description": "Content search index",
            }
            collection.create_index(index_config)  # type: ignore[attr-defined]

            # 确保是 VDB collection
            if not isinstance(collection, VDBMemoryCollection):
                self.logger.error("Collection is not a VDB collection")
                return False

            # 插入文档 - VDBMemoryCollection.insert(index_name, raw_data, metadata)
            for doc in documents:
                collection.insert(
                    index_name="content_index",
                    raw_data=doc["content"],
                    metadata=doc.get("metadata", {}),
                )

            collection.init_index("content_index")
            self.manager.store_collection(collection_name)

            self.logger.info(
                f"✓ Initialized RAG corpus with {len(documents)} documents"
            )
            self._audit_log("INIT_CORPUS", collection_name, len(documents))

            return True

        except Exception as e:
            self.logger.error(f"Error initializing corpus: {e}")
            return False

    def retrieve_relevant_documents(
        self, collection_name: str, query: str, topk: int = 5
    ) -> list[dict[str, Any]]:
        """检索相关文档"""
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                return []

            # 确保是 VDB collection
            if not isinstance(collection, VDBMemoryCollection):
                self.logger.error("Collection is not a VDB collection")
                return []

            # VDBMemoryCollection.retrieve(raw_data, index_name, topk, ...)
            results = collection.retrieve(
                raw_data=query,
                index_name="content_index",
                topk=topk,
                with_metadata=True,
            )

            # retrieve 可能返回 None
            if results is None:
                return []

            return results  # type: ignore[return-value]

        except Exception as e:
            self.logger.error(f"Error retrieving documents: {e}")
            return []

    def forget_documents(
        self,
        collection_name: str,
        document_ids: list[str],
        reason: str = "user_request",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        遗忘指定的文档

        Args:
            collection_name: Collection 名称
            document_ids: 要遗忘的文档 IDs
            reason: 遗忘原因
            user_id: 发起遗忘的用户 ID

        Returns:
            操作结果
        """
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                return {"success": False, "error": "Collection not found"}

            index = collection.index_info.get("content_index", {}).get("index")  # type: ignore[attr-defined]
            if index is None:
                return {"success": False, "error": "Index not found"}

            # 收集要遗忘的向量
            vectors_to_forget = []
            valid_ids = []

            for doc_id in document_ids:
                if hasattr(index, "vector_store") and doc_id in index.vector_store:
                    vector = index.vector_store[doc_id]
                    vectors_to_forget.append(vector)
                    valid_ids.append(doc_id)

            if not vectors_to_forget:
                return {"success": False, "error": "No documents found to forget"}

            # 获取所有向量用于补偿
            all_vectors = []
            all_ids = []
            if hasattr(index, "vector_store"):
                for vid, vector in index.vector_store.items():
                    if vid not in valid_ids:  # 排除要遗忘的向量
                        all_vectors.append(vector)
                        all_ids.append(vid)

            self.logger.info(
                f"Starting DP unlearning for {len(valid_ids)} documents..."
            )

            # 执行 DP 遗忘
            vectors_array = np.array(vectors_to_forget)
            all_vectors_array = np.array(all_vectors) if all_vectors else vectors_array

            result = self.unlearning_engine.unlearn_vectors(
                vectors_to_forget=vectors_array,
                vector_ids_to_forget=valid_ids,
                all_vectors=all_vectors_array,
                all_vector_ids=all_ids,
                perturbation_strategy="adaptive",
            )

            if not result.success:
                error = result.metadata.get("error", "Unknown error")
                self.logger.error(f"Unlearning failed: {error}")
                return {"success": False, "error": error}

            # 更新 VDB 中的向量
            perturbed_vectors = result.metadata.get("perturbed_vectors", [])
            updated_count = 0

            for doc_id, perturbed_vec in zip(valid_ids, perturbed_vectors):
                try:
                    if hasattr(index, "update"):
                        index.update(doc_id, perturbed_vec)
                    else:
                        index.delete(doc_id)
                        index.insert(perturbed_vec, doc_id)
                    updated_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to update vector for {doc_id}: {e}")

            # 持久化
            self.manager.store_collection(collection_name)

            # 记录审计日志
            self._audit_log(
                "FORGET_DOCUMENTS",
                collection_name,
                len(valid_ids),
                extra={
                    "reason": reason,
                    "user_id": user_id,
                    "privacy_cost": result.privacy_cost,
                },
            )

            status = self.unlearning_engine.get_privacy_status()
            remaining = status["remaining_budget"]

            self.logger.info(f"✓ Successfully forgotten {updated_count} documents")

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
            }

        except Exception as e:
            self.logger.error(f"Error in forget_documents: {e}")
            return {"success": False, "error": str(e)}

    def handle_user_deletion_request(
        self, collection_name: str, user_id: str, user_keywords: list[str] | None = None
    ) -> dict[str, Any]:
        """
        处理用户数据删除请求（如 GDPR 删除权）

        Args:
            collection_name: Collection 名称
            user_id: 用户 ID
            user_keywords: 用户特定关键词（可选）

        Returns:
            处理结果
        """
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                return {"success": False, "error": "Collection not found"}

            # 查找属于该用户的所有文档
            all_ids = collection.get_all_ids()
            user_docs = []

            for doc_id in all_ids:
                metadata = collection.metadata_storage.get(doc_id)
                if metadata and metadata.get("user_id") == user_id:
                    user_docs.append(doc_id)

            if not user_docs:
                self.logger.info(f"No documents found for user {user_id}")
                return {
                    "success": True,
                    "num_forgotten": 0,
                    "message": "No documents to delete",
                }

            self.logger.info(f"Found {len(user_docs)} documents for user {user_id}")

            # 遗忘用户所有文档
            result = self.forget_documents(
                collection_name=collection_name,
                document_ids=user_docs,
                reason="user_deletion_request",
                user_id=user_id,
            )

            if result["success"]:
                self.logger.info(f"✓ Deleted all data for user {user_id}")

            return result

        except Exception as e:
            self.logger.error(f"Error handling deletion request: {e}")
            return {"success": False, "error": str(e)}

    def handle_malicious_content_removal(
        self, collection_name: str, detection_keywords: list[str]
    ) -> dict[str, Any]:
        """
        处理恶意内容移除

        Args:
            collection_name: Collection 名称
            detection_keywords: 恶意内容关键词

        Returns:
            处理结果
        """
        try:
            collection = self.manager.get_collection(collection_name)
            if collection is None:
                return {"success": False, "error": "Collection not found"}

            # 查找包含恶意内容的文档
            all_ids = collection.get_all_ids()
            malicious_docs = []

            for doc_id in all_ids:
                content = collection.text_storage.get(doc_id)
                if content:
                    for keyword in detection_keywords:
                        if keyword.lower() in content.lower():
                            malicious_docs.append(doc_id)
                            break

            if not malicious_docs:
                self.logger.info("No malicious content detected")
                return {
                    "success": True,
                    "num_forgotten": 0,
                    "message": "No malicious content found",
                }

            self.logger.warning(
                f"Detected {len(malicious_docs)} documents with malicious content"
            )

            # 遗忘恶意内容
            result = self.forget_documents(
                collection_name=collection_name,
                document_ids=malicious_docs,
                reason="malicious_content",
                user_id="system",
            )

            return result

        except Exception as e:
            self.logger.error(f"Error handling malicious content: {e}")
            return {"success": False, "error": str(e)}

    def get_audit_log(self) -> list[dict[str, Any]]:
        """获取审计日志"""
        return self.audit_log

    def _audit_log(
        self, operation: str, collection: str, count: int, extra: dict | None = None
    ):
        """记录审计事件"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "collection": collection,
            "count": count,
            "extra": extra or {},
        }
        self.audit_log.append(log_entry)


def example_basic_rag():
    """示例1：基础 RAG 系统"""
    print("\n" + "=" * 70)
    print("Example 1: Basic RAG System with Unlearning")
    print("=" * 70)

    system = RAGUnlearningSystem(epsilon=1.0)

    # 创建示例文档
    documents = [
        {
            "id": "doc_001",
            "content": "Machine learning is a subset of artificial intelligence",
            "metadata": {"user_id": "user_1", "category": "public"},
        },
        {
            "id": "doc_002",
            "content": "Deep learning uses neural networks with multiple layers",
            "metadata": {"user_id": "user_1", "category": "public"},
        },
        {
            "id": "doc_003",
            "content": "Natural language processing is used for text analysis",
            "metadata": {"user_id": "user_2", "category": "public"},
        },
        {
            "id": "doc_004",
            "content": "Computer vision helps machines understand images",
            "metadata": {"user_id": "user_2", "category": "sensitive"},
        },
        {
            "id": "doc_005",
            "content": "Reinforcement learning enables agents to learn from interaction",
            "metadata": {"user_id": "user_3", "category": "public"},
        },
    ]

    # 为每个文档添加随机向量
    for doc in documents:
        doc["vector"] = np.random.randn(128).astype(np.float32)
        doc["vector"] = doc["vector"] / (np.linalg.norm(doc["vector"]) + 1e-10)

    # 初始化 corpus
    system.initialize_rag_corpus("knowledge_base", documents)

    # 检索
    print("\n🔍 Retrieving documents...")
    results = system.retrieve_relevant_documents(
        "knowledge_base", "machine learning", topk=3
    )
    print(f"  Found {len(results)} relevant documents")

    # 用户请求删除
    print("\n🗑️ Processing user deletion request...")
    result = system.handle_user_deletion_request("knowledge_base", "user_1")
    print(f"  Success: {result['success']}")
    if result["success"]:
        print(f"  Deleted: {result['num_forgotten']} documents")
        print(f"  Privacy cost: ε={result['privacy_cost']['epsilon']:.4f}")

    print()


def example_malicious_content():
    """示例2：恶意内容检测和移除"""
    print("\n" + "=" * 70)
    print("Example 2: Malicious Content Detection and Removal")
    print("=" * 70)

    system = RAGUnlearningSystem(epsilon=1.0)

    # 创建包含一些恶意内容的文档
    documents = [
        {
            "id": "doc_001",
            "content": "This is normal technical content about machine learning",
            "metadata": {"user_id": "user_1", "category": "normal"},
        },
        {
            "id": "doc_002",
            "content": "Spam content: click here for free money!!!",
            "metadata": {"user_id": "user_2", "category": "spam"},
        },
        {
            "id": "doc_003",
            "content": "More legitimate deep learning information",
            "metadata": {"user_id": "user_1", "category": "normal"},
        },
        {
            "id": "doc_004",
            "content": "Malware distribution: download now!!!",
            "metadata": {"user_id": "user_3", "category": "malicious"},
        },
    ]

    for doc in documents:
        doc["vector"] = np.random.randn(128).astype(np.float32)
        doc["vector"] = doc["vector"] / (np.linalg.norm(doc["vector"]) + 1e-10)

    system.initialize_rag_corpus("content_db", documents)

    # 检测并移除恶意内容
    print("\n🚨 Detecting malicious content...")
    result = system.handle_malicious_content_removal(
        "content_db", detection_keywords=["spam", "malware", "!!!"]
    )

    print(f"  Success: {result['success']}")
    if result["success"]:
        print(f"  Removed: {result['num_forgotten']} malicious documents")

    print()


def example_audit_log():
    """示例3：审计日志"""
    print("\n" + "=" * 70)
    print("Example 3: Audit Log and Compliance")
    print("=" * 70)

    system = RAGUnlearningSystem(epsilon=1.0)

    # 创建文档
    documents = []
    for i in range(10):
        documents.append(
            {
                "id": f"doc_{i:03d}",
                "content": f"Document {i} content",
                "metadata": {"user_id": f"user_{i % 3}", "category": "normal"},
                "vector": np.random.randn(128).astype(np.float32)
                / np.linalg.norm(np.random.randn(128).astype(np.float32)),
            }
        )

    system.initialize_rag_corpus("audit_test", documents)

    # 执行多个操作
    print("\n📝 Performing operations...")

    # 用户 0 删除请求
    system.handle_user_deletion_request("audit_test", "user_0")
    print("  ✓ User deletion request processed")

    # 恶意内容检测（无恶意内容）
    system.handle_malicious_content_removal("audit_test", ["malware"])
    print("  ✓ Malicious content check completed")

    # 显示审计日志
    print("\n📋 Audit Log:")
    for entry in system.get_audit_log():
        print(
            f"  {entry['timestamp']}: {entry['operation']} on {entry['collection']} ({entry['count']} items)"
        )

    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 70)
    print("SAGE Unlearning - Complete RAG System Examples")
    print("=" * 70)
    print("\n这些示例展示了在完整 RAG 系统中使用隐私遗忘。")
    print("包括：用户删除请求、恶意内容移除、合规审计\n")

    CustomLogger.disable_global_console_debug()

    # 运行示例
    example_basic_rag()
    example_malicious_content()
    example_audit_log()

    print("=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print("\n💡 Key Takeaways:")
    print("  1. Unlearning 库提供灵活的隐私保护机制")
    print("  2. 支持多种遗忘场景（用户请求、恶意内容等）")
    print("  3. 完整的审计日志用于合规")
    print("  4. 隐私预算管理确保整体隐私保证\n")


if __name__ == "__main__":
    main()
