"""
医学知识库管理
负责医学知识和病例的检索
"""

import json
from pathlib import Path
from typing import Any


class MedicalKnowledgeBase:
    """
    医学知识库

    功能:
    1. 存储和检索医学知识
    2. 存储和检索病例数据
    3. 多模态检索（文本+影像）

    配置选项 (config):
        data_path: str - 处理后数据集的路径
        enable_dataset_knowledge: bool - 是否从数据集加载知识 (默认True)
        enable_report_knowledge: bool - 是否从医学报告加载知识 (默认True)
        enable_case_database: bool - 是否加载病例数据库 (默认True)
        max_reports: int - 最大读取报告数量 (默认50)
        verbose: bool - 是否输出详细日志 (默认True)
    """

    def __init__(self, config: dict):
        """
        初始化知识库

        Args:
            config: 配置字典，支持以下选项：
                - data_path: 数据路径
                - enable_dataset_knowledge: 启用数据集知识加载
                - enable_report_knowledge: 启用报告知识加载
                - enable_case_database: 启用病例数据库加载
                - max_reports: 最大报告读取数量
                - verbose: 详细输出
        """
        self.config = config
        self.embedding_service = None
        self.vector_db = None

        # 配置选项
        self._verbose = config.get("verbose", True)
        self._enable_dataset = config.get("enable_dataset_knowledge", True)
        self._enable_reports = config.get("enable_report_knowledge", True)
        self._enable_cases = config.get("enable_case_database", True)
        self._max_reports = config.get("max_reports", 50)

        self._setup_services()
        self._load_knowledge()

    def _log(self, message: str):
        """输出日志信息（如果启用详细模式）"""
        if self._verbose:
            print(message)

    def _setup_services(self):
        """设置服务"""
        self._log("   Setting up knowledge base services...")

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
        self._log("   Loading medical knowledge...")

        # 从默认知识开始
        self.knowledge_base = self._get_default_knowledge()
        self.case_database = []

        # 从数据集加载知识
        if self._enable_dataset:
            dataset_knowledge = self._load_knowledge_from_dataset()
            if dataset_knowledge:
                self.knowledge_base.extend(dataset_knowledge)
                self._log(f"   ✓ Loaded {len(dataset_knowledge)} knowledge entries from dataset")

        # 从医学文献/报告加载知识
        if self._enable_reports:
            literature_knowledge = self._load_knowledge_from_reports()
            if literature_knowledge:
                self.knowledge_base.extend(literature_knowledge)
                self._log(f"   ✓ Loaded {len(literature_knowledge)} knowledge entries from reports")

        # 加载病例数据库
        if self._enable_cases:
            cases = self._load_case_database()
            if cases:
                self.case_database = cases
                self._log(f"   ✓ Loaded {len(cases)} cases from database")

        self._log(f"   Total knowledge base size: {len(self.knowledge_base)} entries")

    def _load_knowledge_from_dataset(self) -> list[dict[str, Any]]:
        """从处理好的数据集加载医学知识"""
        knowledge = []

        # 获取数据集路径配置
        data_path = self.config.get("data_path")
        if not data_path:
            # 尝试默认路径
            current_file = Path(__file__)
            default_path = current_file.parent.parent / "data" / "processed"
            if default_path.exists():
                data_path = str(default_path)
            else:
                return knowledge

        data_dir = Path(data_path)
        if not data_dir.exists():
            return knowledge

        # 加载统计信息，从中提取疾病知识
        stats_file = data_dir / "stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, encoding="utf-8") as f:
                    stats = json.load(f)

                # 从疾病分布中提取知识
                disease_dist = stats.get("disease_distribution", {})
                for disease, count in disease_dist.items():
                    if disease and disease != "正常":
                        knowledge.append(
                            {
                                "topic": disease,
                                "content": f"{disease}是常见的腰椎疾病，在数据集中有{count}个相关病例。",
                                "source": "dataset_statistics",
                                "case_count": count,
                            }
                        )
            except Exception as e:
                print(f"   Warning: Failed to load stats.json: {e}")

        return knowledge

    def _load_knowledge_from_reports(self) -> list[dict[str, Any]]:
        """从医学报告中提取知识"""
        knowledge = []

        # 获取数据集路径配置
        data_path = self.config.get("data_path")
        if not data_path:
            # 尝试默认路径
            current_file = Path(__file__)
            default_path = current_file.parent.parent / "data" / "processed"
            if default_path.exists():
                data_path = str(default_path)
            else:
                return knowledge

        data_dir = Path(data_path)
        reports_dir = data_dir / "reports"

        if not reports_dir.exists():
            return knowledge

        # 读取所有报告并提取知识
        report_files = list(reports_dir.glob("*.txt"))

        # 用于存储提取的独特知识点
        disease_knowledge = {}

        for report_file in report_files[: self._max_reports]:  # 限制读取数量以避免过载
            try:
                with open(report_file, encoding="utf-8") as f:
                    report_content = f.read()

                # 从报告中提取诊断结论和治疗建议
                lines = report_content.split("\n")
                diagnosis = None
                treatment = None
                findings = None

                for i, line in enumerate(lines):
                    if "诊断结论:" in line and i + 1 < len(lines):
                        diagnosis = lines[i + 1].strip()
                    elif "治疗建议:" in line and i + 1 < len(lines):
                        treatment = lines[i + 1].strip()
                    elif "主要发现:" in line:
                        # 提取接下来几行的发现
                        findings_lines = []
                        for j in range(i + 1, min(i + 5, len(lines))):
                            if lines[j].strip().startswith("-"):
                                findings_lines.append(lines[j].strip())
                        findings = "\n".join(findings_lines) if findings_lines else None

                # 如果提取到有效信息，添加到知识库
                if diagnosis and diagnosis not in disease_knowledge:
                    # 从诊断中提取疾病名称
                    disease_name = diagnosis.split("，")[0] if "，" in diagnosis else diagnosis

                    if disease_name and len(disease_name) > 2:
                        disease_knowledge[disease_name] = {
                            "topic": disease_name,
                            "content": diagnosis,
                            "treatment": treatment if treatment else "请咨询专业医生",
                            "findings": findings if findings else "影像学检查显示相应变化",
                            "source": "medical_reports",
                        }

            except Exception:
                # 忽略单个文件的错误，继续处理其他文件
                continue

        # 将提取的知识转换为列表
        knowledge = list(disease_knowledge.values())

        return knowledge

    def _load_case_database(self) -> list[dict[str, Any]]:
        """从数据集加载病例数据库"""
        cases = []

        # 获取数据集路径配置
        data_path = self.config.get("data_path")
        if not data_path:
            # 尝试默认路径
            current_file = Path(__file__)
            default_path = current_file.parent.parent / "data" / "processed"
            if default_path.exists():
                data_path = str(default_path)
            else:
                return cases

        data_dir = Path(data_path)

        # 尝试加载所有病例索引
        all_cases_file = data_dir / "all_cases.json"
        if all_cases_file.exists():
            try:
                with open(all_cases_file, encoding="utf-8") as f:
                    cases_data = json.load(f)

                # 转换为统一格式
                for case in cases_data:
                    cases.append(
                        {
                            "case_id": case.get("case_id", ""),
                            "age": case.get("age", 0),
                            "gender": case.get("gender", "unknown"),
                            "diagnosis": case.get("disease", ""),
                            "severity": case.get("severity", ""),
                            "image_path": case.get("image_path", ""),
                            "report_path": case.get("report_path", ""),
                        }
                    )

            except Exception as e:
                print(f"   Warning: Failed to load case database: {e}")

        return cases

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
            # 如果有加载的病例数据库，使用它；否则返回模拟病例
            if self.case_database:
                # 简单的关键词匹配（实际应该使用向量检索）
                matched_cases = []
                query_keywords = query.lower().split()

                for case in self.case_database:
                    # 计算匹配分数
                    score = 0.0
                    diagnosis = case.get("diagnosis", "").lower()

                    for keyword in query_keywords:
                        if keyword in diagnosis:
                            score += 1.0

                    if score > 0:
                        matched_cases.append(
                            {
                                "case_id": case.get("case_id", ""),
                                "age": case.get("age", 0),
                                "gender": case.get("gender", "unknown"),
                                "diagnosis": case.get("diagnosis", ""),
                                "severity": case.get("severity", ""),
                                "similarity_score": min(score / len(query_keywords), 1.0),
                            }
                        )

                # 按相似度排序
                matched_cases.sort(key=lambda x: x["similarity_score"], reverse=True)

                # 如果找到匹配的病例，返回它们
                if matched_cases:
                    return matched_cases[:top_k]

            # 没有加载的数据或没有匹配，返回模拟病例
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
            topic = knowledge.get("topic", "")
            content = knowledge.get("content", "")

            # Check if query contains topic or topic contains query (for Chinese text)
            # Also check if query matches content
            if (
                topic in query
                or query in topic
                or any(char in topic for char in query if len(char.strip()) > 0)
                or topic in content
                or query in content
            ):
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

    def update_knowledge(self, knowledge_data: dict[str, Any]):
        """更新医学知识"""
        # TODO: 实现知识更新
        # Issue URL: https://github.com/intellistream/SAGE/issues/902
        self.knowledge_base.append(knowledge_data)


if __name__ == "__main__":
    # 测试
    config = {"services": {"vector_db": {"collection_name": "lumbar_cases", "top_k": 5}}}

    kb = MedicalKnowledgeBase(config)

    # 测试检索
    cases = kb.retrieve_similar_cases(query="腰痛伴下肢麻木", image_features={}, top_k=3)

    print(f"检索到 {len(cases)} 个相似病例:")
    for case in cases:
        print(f"  - {case['case_id']}: {case['diagnosis']} (相似度: {case['similarity_score']})")
