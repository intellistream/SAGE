"""后插入处理模块 - 在记忆插入后的后处理（可选）

对于短期记忆（STM），通常不需要后处理。
此模块保留用于未来扩展（记忆蒸馏等）。
"""

import json

from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.common.core import MapFunction


class PostInsert(MapFunction):
    """记忆插入后的后处理算子

    职责：
    - 触发后续操作
    - 记忆蒸馏（distillation）
    """

    def __init__(self, config):
        """初始化 PostInsert

        Args:
            config: RuntimeConfig 对象，从中获取 operators.post_insert.action
        """
        super().__init__()
        self.config = config
        self.action = config.get("operators.post_insert.action", "none")

        # 服务后端配置
        self.service_name = config.get("services.register_memory_service", "short_term_memory")

        # 如果 action 是 distillation，初始化 LLM 和 Embedding 生成器
        if self.action == "distillation":
            # 蒸馏配置
            self.distillation_topk = config.get("operators.post_insert.distillation_topk", 10)
            # threshold: 汉明距离阈值，即最多接受多少位不同，None 表示使用服务默认值 (nbits/2)
            self.distillation_threshold = config.get(
                "operators.post_insert.distillation_threshold", None
            )
            self.distillation_prompt = config.get("operators.post_insert.distillation_prompt")
            if not self.distillation_prompt:
                raise ValueError("缺少必需的配置: operators.post_insert.distillation_prompt")

            # 初始化 LLM 生成器
            self.generator = LLMGenerator.from_config(config)

            # 初始化 Embedding 生成器
            self.embedding_generator = EmbeddingGenerator.from_config(config)

    def execute(self, data):
        """执行后处理

        Args:
            data: 由 MemoryInsert 输出的数据，格式：
                {
                    "memory_entries": [条目1, 条目2, ...],  # 已插入但未清空的队列
                    ...其他字段
                }

        Returns:
            处理后的数据（清空队列后透传）
        """
        # 根据 action 模式执行不同操作
        if self.action == "distillation":
            # 记忆蒸馏：在清空队列之前处理
            self._distill_memory(data)
        elif self.action == "log":
            # 日志记录
            self._log_data(data)
        elif self.action == "stats":
            # 统计分析
            self._analyze_stats(data)

        return data

    def _distill_memory(self, data):
        """执行记忆蒸馏

        对于每个已插入的三元组，检索相似记忆并进行蒸馏：
        1. 调用搜索服务，检索 Top10，如果结果个数不满足 10 个，跳过
        2. 个数满足 10 个，调用大模型进行蒸馏
        3. 调用删除服务，删除蒸馏过程中被移除的数据
        4. 调用插入服务，依次 embedding 并插入新的数据

        Args:
            data: 包含 memory_entries 的数据字典
        """

        # 逐个处理记忆条目（空列表时自动跳过循环）
        for entry_dict in data.get("memory_entries", []):
            # 获取该条目的 embedding 向量
            query_vector = entry_dict.get("embedding")

            # Step 1: 检索 Top-K 相似记忆(通过阈值和Top-K共同决定是否蒸馏)
            results = self._retrieve_memories(query_vector)

            # 如果结果不足指定数量，跳过蒸馏
            if not results or len(results) < self.distillation_topk:
                continue

            # Step 2: 调用 LLM 进行蒸馏
            memory_texts = [r.get("text", "") for r in results]
            memory_list_str = "\n".join(memory_texts)

            prompt = self.distillation_prompt.replace("{memory_list}", memory_list_str)
            distillation_result = self.generator.generate(prompt)

            # 解析 JSON 格式的蒸馏结果
            try:
                result_text = distillation_result.strip()
                start_idx = result_text.find("{")
                end_idx = result_text.rfind("}") + 1

                if start_idx == -1 or end_idx == 0:
                    continue

                json_str = result_text[start_idx:end_idx]
                result = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            to_delete_raw = result.get("to_delete", [])
            to_insert_raw = result.get("to_insert", [])

            # 构建原始记忆文本集合，用于对齐验证
            memory_texts_set = set(memory_texts)

            # 处理 to_delete：必须和原始记忆完全匹配才能删除
            to_delete_set = set()
            for t in to_delete_raw:
                if not t or not isinstance(t, str):
                    continue
                t = t.strip()
                if t in memory_texts_set:
                    to_delete_set.add(t)

            # 处理 to_insert：去重，过滤包含括号的文本，且不能是已存在的记忆
            seen = set()
            new_texts = []
            for t in to_insert_raw:
                if not t or not isinstance(t, str):
                    continue
                t = t.strip()
                # 过滤包含括号的文本（可能是格式错误）
                if "(" in t or ")" in t:
                    continue
                # 跳过已存在于原始记忆中的文本（避免重复插入）
                if t in memory_texts_set:
                    continue
                if t and t not in seen and t not in to_delete_set:
                    seen.add(t)
                    new_texts.append(t)

            # Step 3: 删除需要删除的记忆（已去重、已清理）
            for text_to_delete in to_delete_set:
                self._delete_memory(text_to_delete)

            # Step 4: 插入合并后的新记忆（已去重且过滤）
            if new_texts:
                embeddings = self.embedding_generator.embed_batch(new_texts)
                for i, text in enumerate(new_texts):
                    vector = embeddings[i] if embeddings is not None else None
                    self._insert_memory(text, vector)
            # print("")
            # print(f"delete: {text_to_delete}")
            # print(f"memory_list:\n{memory_list_str}")
            # print("-----------------------------")
            # print(f"insert: {new_texts}")

    # ==================== 服务调用方法 ====================

    def _retrieve_memories(
        self, vector, topk: int | None = None, threshold: int | None = None
    ) -> list:
        """检索相似记忆

        Args:
            vector: 查询向量
            topk: 返回数量，默认使用 distillation_topk
            threshold: 汉明距离阈值（最多接受多少位不同），默认使用 distillation_threshold

        Returns:
            检索结果列表，每个元素包含 text 和 metadata
        """
        return self.call_service(
            self.service_name,
            vector=vector,
            topk=topk or self.distillation_topk,
            threshold=threshold if threshold is not None else self.distillation_threshold,
            method="retrieve",
            timeout=10.0,
        )

    def _delete_memory(self, entry: str) -> bool:
        """删除记忆条目

        Args:
            entry: 要删除的文本

        Returns:
            是否删除成功
        """
        return self.call_service(
            self.service_name,
            entry=entry,
            method="delete",
            timeout=10.0,
        )

    def _insert_memory(self, entry: str, vector=None, metadata: dict | None = None) -> bool:
        """插入记忆条目

        Args:
            entry: 文本内容
            vector: embedding 向量
            metadata: 元数据

        Returns:
            是否插入成功
        """
        return self.call_service(
            self.service_name,
            entry=entry,
            vector=vector,
            metadata=metadata,
            method="insert",
            timeout=10.0,
        )
