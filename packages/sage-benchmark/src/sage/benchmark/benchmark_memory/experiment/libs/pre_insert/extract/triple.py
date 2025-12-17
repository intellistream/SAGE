"""TripleExtractAction - 三元组提取策略

从文本中提取三元组（subject-predicate-object），并重构为适合检索的形式。
属于 Extract 类别，与 entity、keyword、noun 提取并列。
适用于 TiM, HippoRAG, HippoRAG2 等基于知识图谱的记忆体。
"""

from ..base import BasePreInsertAction, PreInsertInput, PreInsertOutput


class TripleExtractAction(BasePreInsertAction):
    """三元组提取 Action (Extract 类别)

    归属：D2 PreInsert - Extract 类别
    地位：与 entity、keyword、noun 并列的提取策略

    使用场景：
    - TiM: 提取三元组构建时序记忆图
    - HippoRAG: 三元组作为知识图谱节点和边
    - HippoRAG2: 增强的三元组提取和链接

    处理流程：
    1. 从对话中提取三元组（subject, predicate, object）
    2. 重构三元组为自然语言文本
    3. 为每个三元组生成 embedding
    """

    def _init_action(self) -> None:
        """初始化三元组提取工具"""
        self.extraction_method = self.config.get("extraction_method", "simple")
        self.max_triplets = self.config.get("max_triplets", 10)
        self.reconstruct_template = self.config.get(
            "reconstruct_template", "{subject} {predicate} {object}"
        )

        # 是否保留原始文本
        self.keep_original = self.config.get("keep_original", True)

        # LLM相关配置
        self.triple_extraction_prompt = self.config.get("triple_extraction_prompt", "")
        self.llm_generator = None

    def set_llm_generator(self, llm_generator):
        """设置LLM生成器"""
        self.llm_generator = llm_generator

    def execute(self, input_data: PreInsertInput) -> PreInsertOutput:
        """执行三元组提取和重构

        Args:
            input_data: 包含 dialogs 的输入数据

        Returns:
            包含三元组的记忆条目
        """
        # 提取并格式化对话
        dialogs = input_data.data.get("dialogs", [])
        text = self._format_dialogue(dialogs)

        # 提取三元组
        triplets = self._extract_triplets(text)

        # 重构三元组为文本
        reconstructed_texts = [self._reconstruct_triplet(t) for t in triplets]

        # 创建记忆条目
        entries = []

        if self.keep_original:
            # 保留原始文本作为第一条记忆
            original_entry = {
                "text": text,
                "metadata": {
                    "action": "extract.triple",
                    "type": "original",
                    "triplet_count": len(triplets),
                },
            }
            original_entry = self._set_default_fields(original_entry)
            original_entry["insert_method"] = "triple_extract_original"
            entries.append(original_entry)

        # 每个三元组作为独立记忆条目
        for i, (triplet, reconstructed) in enumerate(zip(triplets, reconstructed_texts)):
            entry = {
                "text": reconstructed,
                "triplet": triplet,
                "reconstructed_text": reconstructed,
                "metadata": {
                    "action": "extract.triple",
                    "type": "triplet",
                    "triplet_index": i,
                    "subject": triplet["subject"],
                    "predicate": triplet["predicate"],
                    "object": triplet["object"],
                },
            }
            entry = self._set_default_fields(entry)
            entry["insert_method"] = "triple_extract_triplet"
            entries.append(entry)

        return PreInsertOutput(
            memory_entries=entries,
            metadata={
                "triplet_count": len(triplets),
                "extraction_method": self.extraction_method,
            },
        )

    def _extract_triplets(self, text: str) -> list[dict[str, str]]:
        """提取三元组

        Args:
            text: 输入文本

        Returns:
            三元组列表，每个三元组包含 subject, predicate, object
        """
        if self.extraction_method == "llm":
            return self._extract_by_llm(text)
        else:
            return self._extract_simple(text)

    def _extract_simple(self, text: str) -> list[dict[str, str]]:
        """简单的三元组提取

        使用启发式规则提取 Subject-Verb-Object 结构。

        Args:
            text: 输入文本

        Returns:
            三元组列表
        """
        import re

        # 简化示例：按句子分割，提取简单的 SVO 结构
        sentences = re.split(r"[。.!?！？]+", text)
        triplets = []

        for sentence in sentences[: self.max_triplets]:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 非常简化的提取：假设句子格式为 "X is/was/has Y"
            # 实际应用中应使用 spaCy 依存句法分析
            patterns = [
                r"(\w+)\s+(is|are|was|were|has|have)\s+(.+)",
                r"(\w+)\s+(做|说|认为|喜欢|讨厌)\s+(.+)",
            ]

            matched = False
            for pattern in patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    triplets.append(
                        {
                            "subject": match.group(1).strip(),
                            "predicate": match.group(2).strip(),
                            "object": match.group(3).strip(),
                        }
                    )
                    matched = True
                    break

            # 如果没有匹配，创建简单三元组
            if not matched and len(sentence.split()) >= 3:
                words = sentence.split()
                triplets.append(
                    {
                        "subject": words[0],
                        "predicate": words[1] if len(words) > 1 else "relates_to",
                        "object": " ".join(words[2:]) if len(words) > 2 else words[-1],
                    }
                )

        return triplets[: self.max_triplets]

    def _extract_by_llm(self, text: str) -> list[dict[str, str]]:
        """使用 LLM 提取三元组

        Args:
            text: 输入文本

        Returns:
            三元组列表
        """
        if not self.llm_generator:
            print("[WARNING] LLM not available, falling back to simple extraction")
            return self._extract_simple(text)

        if not self.triple_extraction_prompt:
            print(
                "[WARNING] No triple_extraction_prompt configured, falling back to simple extraction"
            )
            return self._extract_simple(text)

        try:
            # 格式化prompt
            prompt = self.triple_extraction_prompt.format(dialogue=text)

            # 调用LLM
            response = self.llm_generator.generate(prompt)

            # 解析LLM输出
            triplets = self._parse_llm_response(response)

            # 限制数量
            return triplets[: self.max_triplets]

        except Exception as e:
            print(f"[ERROR] LLM extraction failed: {e}, falling back to simple extraction")
            return self._extract_simple(text)

    def _parse_llm_response(self, response: str) -> list[dict[str, str]]:
        """解析LLM返回的三元组

        期望格式：
        (Subject, Predicate, Object)
        (Subject2, Predicate2, Object2)
        或者：
        None
        """
        import re

        triplets = []

        # 如果LLM返回"None"，表示没有提取到三元组
        if response.strip().lower() in ["none", "无", "没有"]:
            return triplets

        # 使用正则表达式匹配三元组格式 (Subject, Predicate, Object)
        pattern = r"\(([^,]+),\s*([^,]+),\s*([^)]+)\)"
        matches = re.findall(pattern, response, re.MULTILINE)

        for match in matches:
            subject = match[0].strip()
            predicate = match[1].strip()
            obj = match[2].strip()

            # 清理引号
            for item in [subject, predicate, obj]:
                item = item.strip('"').strip("'").strip()

            triplets.append({"subject": subject, "predicate": predicate, "object": obj})

        # 如果正则匹配失败，尝试其他格式或回退到简单方法
        if not triplets:
            print(
                f"[WARNING] Could not parse LLM response, trying simple extraction. Response: {response[:200]}..."
            )
            # 不直接回退，而是返回空列表，让上层处理

        return triplets

    def _reconstruct_triplet(self, triplet: dict[str, str]) -> str:
        """重构三元组为自然语言文本

        Args:
            triplet: 三元组字典

        Returns:
            重构后的文本
        """
        return self.reconstruct_template.format(
            subject=triplet["subject"],
            predicate=triplet["predicate"],
            object=triplet["object"],
        )
