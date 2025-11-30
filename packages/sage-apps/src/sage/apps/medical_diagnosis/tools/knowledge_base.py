"""
医学知识库管理
负责医学知识和病例的检索
"""

from typing import Any

from sage.common.components.sage_embedding.service import EmbeddingService
from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (
    SageDBService,
)


class MedicalKnowledgeBase:
    """
    医学知识库

    功能:
    1. 存储和检索医学知识
    2. 存储和检索病例数据
    3. 多模态检索（文本+影像）
    """

    def __init__(self, config: dict):
        """
        初始化知识库

        Args:
            config: 配置字典
        """
        self.config = config
        self.embedding_service = None
        self.vector_db = None
        self._setup_services()
        self._load_knowledge()

    def _setup_services(self):
        """设置服务"""
        print("   Setting up knowledge base services...")

        # 获取embedding和向量数据库配置
        embedding_config = self.config.get("services", {}).get("embedding", {})
        vector_db_config = self.config.get("services", {}).get("vector_db", {})
        models_config = self.config.get("models", {})

        # 初始化 EmbeddingService
        embedding_service_config = {
            "method": embedding_config.get("method", "hf"),
            "model": models_config.get("embedding_model", "BAAI/bge-large-zh-v1.5"),
            "batch_size": embedding_config.get("batch_size", 32),
            "normalize": embedding_config.get("normalize", True),
            "cache_enabled": embedding_config.get("cache_enabled", False),
        }

        self.embedding_service = EmbeddingService(embedding_service_config)
        self.embedding_service.setup()

        # 初始化 SageDBService
        # 获取embedding维度
        dimension = self.embedding_service.get_dimension()
        index_type = vector_db_config.get("index_type", "AUTO")

        self.vector_db = SageDBService(dimension=dimension, index_type=index_type)

        print(
            f"   ✓ EmbeddingService initialized (dim={dimension}, method={embedding_service_config['method']})"
        )
        print(f"   ✓ SageDBService initialized (dim={dimension}, index_type={index_type})")

    def _load_knowledge(self):
        """加载医学知识"""
        # TODO: 从数据集和医学文献加载知识
        # Issue URL: https://github.com/intellistream/SAGE/issues/905
        self.knowledge_base = self._get_default_knowledge()
        self.case_database = []

    def _get_default_knowledge(self) -> list[dict[str, str]]:
        """获取默认医学知识"""
        return [
            {
                "topic": "腰椎间盘突出症",
                "content": """
                腰椎间盘突出症是指椎间盘的纤维环破裂，髓核组织从破裂处突出于后方或椎管内，
                导致相邻脊神经根遭受刺激或压迫，从而产生腰部疼痛、下肢麻木疼痛等一系列临床症状。
                好发部位：L4/L5、L5/S1。
                """,
                "diagnosis_criteria": "MRI T2加权像显示椎间盘后突，硬膜囊受压变形",
                "treatment": "保守治疗包括卧床休息、物理治疗、药物治疗；严重者可考虑手术",
            },
            {
                "topic": "腰椎退行性变",
                "content": """
                腰椎退行性变是指随年龄增长，腰椎间盘、椎体及小关节发生的退行性改变。
                主要表现为椎间盘高度降低、信号减低、骨质增生等。
                """,
                "diagnosis_criteria": "MRI显示椎间盘信号减低、高度降低、椎体边缘骨赘形成",
                "treatment": "以保守治疗为主，加强腰背肌锻炼，避免久坐久站",
            },
            {
                "topic": "椎管狭窄",
                "content": """
                腰椎管狭窄症是指因各种原因导致椎管容积减小，压迫硬膜囊、马尾神经或神经根，
                引起相应神经功能障碍的一组综合征。
                """,
                "diagnosis_criteria": "MRI显示椎管矢状径<12mm，硬膜囊明显受压",
                "treatment": "轻度可保守治疗，重度需手术减压",
            },
        ]

    def retrieve_similar_cases(
        self, query: str, image_features: dict[str, Any], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        检索相似病例

        Args:
            query: 查询文本
            image_features: 影像特征
            top_k: 返回数量

        Returns:
            相似病例列表
        """
        # 如果向量数据库为空，返回模拟病例
        if self.vector_db.stats()["size"] == 0:
            # 返回模拟病例
            return self._get_mock_cases()[:top_k]

        # 使用 EmbeddingService 生成查询向量
        result = self.embedding_service.embed(query)
        query_vector = result["vectors"][0]

        # 使用 SageDB 进行向量检索
        search_results = self.vector_db.search(query_vector, k=top_k, include_metadata=True)

        # 转换为病例格式
        cases = []
        for res in search_results:
            metadata = res.get("metadata", {})
            cases.append(
                {
                    "case_id": metadata.get("case_id", f"CASE_{res['id']:03d}"),
                    "age": int(metadata.get("age", 0)) if metadata.get("age") else 0,
                    "gender": metadata.get("gender", "unknown"),
                    "diagnosis": metadata.get("diagnosis", ""),
                    "symptoms": metadata.get("symptoms", ""),
                    "treatment": metadata.get("treatment", ""),
                    "outcome": metadata.get("outcome", ""),
                    "similarity_score": float(res["score"]),
                }
            )

        return cases

    def retrieve_knowledge(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        检索医学知识

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            医学知识列表
        """
        # 使用简单的关键词匹配（可以后续改进为向量检索）
        results = []

        for knowledge in self.knowledge_base:
            if any(keyword in query for keyword in knowledge["topic"].split()):
                results.append(knowledge)

        # 如果没有匹配结果，使用向量相似度检索
        if not results and self.embedding_service:
            # 为知识库条目生成embedding并检索
            knowledge_texts = [k["topic"] + " " + k["content"] for k in self.knowledge_base]
            knowledge_embeddings = self.embedding_service.embed(knowledge_texts)

            # 为查询生成embedding
            query_embedding = self.embedding_service.embed(query)
            query_vec = query_embedding["vectors"][0]

            # 计算相似度并排序
            import numpy as np

            similarities = []
            for i, emb_vec in enumerate(knowledge_embeddings["vectors"]):
                similarity = float(np.dot(query_vec, emb_vec))
                similarities.append((i, similarity))

            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)

            # 返回top_k个最相似的知识
            for idx, _ in similarities[:top_k]:
                results.append(self.knowledge_base[idx])

        return results[:top_k]

    def _get_mock_cases(self) -> list[dict[str, Any]]:
        """获取模拟病例"""
        return [
            {
                "case_id": "CASE_001",
                "age": 48,
                "gender": "male",
                "diagnosis": "L4/L5椎间盘突出症",
                "symptoms": "下背部疼痛，左腿麻木",
                "treatment": "保守治疗3个月后症状缓解",
                "outcome": "良好",
                "similarity_score": 0.92,
            },
            {
                "case_id": "CASE_002",
                "age": 52,
                "gender": "male",
                "diagnosis": "L5/S1椎间盘突出症伴椎管狭窄",
                "symptoms": "腰痛伴双下肢麻木",
                "treatment": "手术治疗（椎间盘切除+椎管减压）",
                "outcome": "症状明显改善",
                "similarity_score": 0.88,
            },
            {
                "case_id": "CASE_003",
                "age": 43,
                "gender": "female",
                "diagnosis": "L4/L5椎间盘突出症",
                "symptoms": "右下肢放射痛",
                "treatment": "物理治疗+药物治疗",
                "outcome": "部分缓解",
                "similarity_score": 0.85,
            },
            {
                "case_id": "CASE_004",
                "age": 60,
                "gender": "male",
                "diagnosis": "腰椎退行性变，L3/L4、L4/L5椎间盘突出",
                "symptoms": "慢性腰痛",
                "treatment": "长期康复训练",
                "outcome": "稳定",
                "similarity_score": 0.82,
            },
            {
                "case_id": "CASE_005",
                "age": 38,
                "gender": "female",
                "diagnosis": "L5/S1椎间盘突出症",
                "symptoms": "急性腰痛，左腿麻木",
                "treatment": "卧床休息+止痛药",
                "outcome": "2周后好转",
                "similarity_score": 0.80,
            },
        ]

    def add_case(self, case_data: dict[str, Any]):
        """添加新病例到知识库"""
        # 构建病例文本描述用于embedding
        case_text = f"{case_data.get('diagnosis', '')} {case_data.get('symptoms', '')}"

        # 生成文本embedding
        result = self.embedding_service.embed(case_text)
        case_vector = result["vectors"][0]

        # 准备metadata
        metadata = {
            "case_id": str(case_data.get("case_id", "")),
            "age": str(case_data.get("age", "")),
            "gender": str(case_data.get("gender", "")),
            "diagnosis": str(case_data.get("diagnosis", "")),
            "symptoms": str(case_data.get("symptoms", "")),
            "treatment": str(case_data.get("treatment", "")),
            "outcome": str(case_data.get("outcome", "")),
        }

        # 存入向量数据库
        vector_id = self.vector_db.add(case_vector, metadata)

        # 同时添加到本地缓存
        self.case_database.append(case_data)

        return vector_id

    def update_knowledge(self, knowledge_data: dict[str, Any]):
        """更新医学知识"""
        # TODO: 实现知识更新
        # Issue URL: https://github.com/intellistream/SAGE/issues/902
        self.knowledge_base.append(knowledge_data)

    def cleanup(self):
        """清理资源"""
        if self.embedding_service and hasattr(self.embedding_service, "cleanup"):
            self.embedding_service.cleanup()

    def __del__(self):
        """析构时清理资源"""
        self.cleanup()


if __name__ == "__main__":
    # 测试
    config = {"services": {"vector_db": {"collection_name": "lumbar_cases", "top_k": 5}}}

    kb = MedicalKnowledgeBase(config)

    # 测试检索
    cases = kb.retrieve_similar_cases(query="腰痛伴下肢麻木", image_features={}, top_k=3)

    print(f"检索到 {len(cases)} 个相似病例:")
    for case in cases:
        print(f"  - {case['case_id']}: {case['diagnosis']} (相似度: {case['similarity_score']})")
