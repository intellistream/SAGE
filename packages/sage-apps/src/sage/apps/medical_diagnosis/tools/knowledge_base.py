"""
医学知识库管理
负责医学知识和病例的检索
"""

from typing import Any


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

        # TODO: 集成 SAGE EmbeddingService 和 SageDB
        # 参见跟踪问题: https://github.com/your-org/your-repo/issues/123
        # Issue URL: https://github.com/intellistream/SAGE/issues/906
        # from sage.common.components.sage_embedding.service import EmbeddingService
        # from sage.middleware.components.sage_db.service import SageDBService

        # self.embedding_service = EmbeddingService(...)
        # self.vector_db = SageDBService(...)

        self.embedding_service = "placeholder"
        self.vector_db = "placeholder"

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
        if self.vector_db == "placeholder":
            # 返回模拟病例
            return self._get_mock_cases()[:top_k]

        # TODO: 实现真实的向量检索
        # Issue URL: https://github.com/intellistream/SAGE/issues/904
        # 1. 对查询文本进行embedding
        # 2. 对影像特征进行embedding
        # 3. 多模态检索（文本+影像）
        # 4. 返回Top-K相似病例

        return []

    def retrieve_knowledge(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        检索医学知识

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            医学知识列表
        """
        # 简单匹配（实际应该使用向量检索）
        results = []

        for knowledge in self.knowledge_base:
            if any(keyword in query for keyword in knowledge["topic"].split()):
                results.append(knowledge)

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
        # TODO: 实现病例添加
        # Issue URL: https://github.com/intellistream/SAGE/issues/903
        # 1. 提取影像特征
        # 2. 生成文本embedding
        # 3. 存入向量数据库
        self.case_database.append(case_data)

    def update_knowledge(self, knowledge_data: dict[str, Any]) -> dict[str, str]:
        """
        更新医学知识

        Args:
            knowledge_data: 知识数据字典，必须包含 'topic' 字段

        Returns:
            操作结果字典，包含 'action' (added/updated) 和 'topic' 字段

        Raises:
            ValueError: 如果 knowledge_data 缺少必需的 'topic' 字段
        """
        # 验证必需字段
        if not knowledge_data or "topic" not in knowledge_data:
            raise ValueError("knowledge_data must contain 'topic' field")

        topic = knowledge_data["topic"]

        # 检查是否已存在相同主题的知识
        existing_index = None
        for i, knowledge in enumerate(self.knowledge_base):
            if knowledge.get("topic") == topic:
                existing_index = i
                break

        if existing_index is not None:
            # 更新现有知识
            self.knowledge_base[existing_index] = knowledge_data
            return {"action": "updated", "topic": topic}
        else:
            # 添加新知识
            self.knowledge_base.append(knowledge_data)
            return {"action": "added", "topic": topic}


if __name__ == "__main__":
    # 测试
    config = {"services": {"vector_db": {"collection_name": "lumbar_cases", "top_k": 5}}}

    kb = MedicalKnowledgeBase(config)

    print("=" * 80)
    print("测试知识库功能")
    print("=" * 80)

    # 测试检索
    print(f"\n1. 初始知识库包含 {len(kb.knowledge_base)} 个知识条目")
    print(f"   主题: {[k['topic'] for k in kb.knowledge_base]}")

    # 测试添加新知识
    print("\n2. 测试添加新知识")
    new_knowledge = {
        "topic": "椎体压缩性骨折",
        "content": "椎体压缩性骨折是指椎体在外力作用下发生压缩性变形",
        "diagnosis_criteria": "X线或CT显示椎体高度降低超过20%",
        "treatment": "急性期卧床休息，必要时行椎体成形术",
    }
    result = kb.update_knowledge(new_knowledge)
    print(f"   结果: {result['action']} - {result['topic']}")
    print(f"   知识库现有 {len(kb.knowledge_base)} 个条目")

    # 测试更新现有知识
    print("\n3. 测试更新现有知识")
    updated_knowledge = {
        "topic": "腰椎间盘突出症",
        "content": "更新后的内容：腰椎间盘突出症是最常见的腰椎疾病之一",
        "diagnosis_criteria": "更新后的诊断标准",
        "treatment": "更新后的治疗方案",
        "additional_info": "新增字段：这是补充信息",
    }
    result = kb.update_knowledge(updated_knowledge)
    print(f"   结果: {result['action']} - {result['topic']}")
    print(f"   知识库仍有 {len(kb.knowledge_base)} 个条目 (未增加)")

    # 验证更新是否成功
    disc_knowledge = [k for k in kb.knowledge_base if k["topic"] == "腰椎间盘突出症"]
    print(f"   '腰椎间盘突出症' 条目数: {len(disc_knowledge)}")
    if disc_knowledge:
        print(f"   更新后的内容预览: {disc_knowledge[0]['content'][:50]}...")

    # 测试相似病例检索
    print("\n4. 测试相似病例检索")
    cases = kb.retrieve_similar_cases(query="腰痛伴下肢麻木", image_features={}, top_k=3)
    print(f"   检索到 {len(cases)} 个相似病例:")
    for case in cases:
        print(f"     - {case['case_id']}: {case['diagnosis']} (相似度: {case['similarity_score']})")

    print("\n" + "=" * 80)
