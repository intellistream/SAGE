"""预插入处理模块 - 在记忆插入前的预处理（可选）

对于短期记忆（STM），通常不需要预处理，直接插入即可。
此模块保留用于未来扩展（如数据验证、格式转换等）。
"""

from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
from sage.benchmark.benchmark_memory.experiment.utils.pre_insert_parser import PreInsertParser
from sage.common.core import MapFunction


class PreInsert(MapFunction):
    """记忆插入前的预处理算子

    职责：
    - 数据验证
    - 格式转换
    - 过滤无效对话

    注：短期记忆通常不需要此步骤
    """

    def __init__(self, config):
        """初始化 PreInsert

        Args:
            config: RuntimeConfig 对象，从中获取 operators.pre_insert.action
        """
        super().__init__()
        self.action = config.get("operators.pre_insert.action", "none")
        self.config = config

        # 初始化解析器（无需配置）
        self.parser = PreInsertParser()

        # 如果 action 是 tri_embed，初始化 LLM 生成器和 Embedding 生成器
        if self.action == "tri_embed":
            # 从配置文件读取三元组提取的 Prompt 模板
            self.triple_extraction_prompt = config.get("operators.pre_insert.triple_extraction_prompt")
            if not self.triple_extraction_prompt:
                raise ValueError("缺少必需的配置: operators.pre_insert.triple_extraction_prompt")

            # 初始化 LLM 生成器
            self.generator = LLMGenerator.from_config(config)

            # 初始化 Embedding 生成器
            self.embedding_generator = EmbeddingGenerator.from_config(config)

    def execute(self, data):
        """执行预处理

        Args:
            data: 原始对话数据（字典格式）

        Returns:
            处理后的数据（字典格式或 None）：
            - None: 如果没有可处理的数据
            - dict: 包含 memory_entries 队列的字典（保留原字典的所有字段）
                {
                    "memory_entries": [条目1, 条目2, ...],  # 待插入的记忆条目队列
                    ...原字典的其他字段（包括可能的控制字段）
                }
        """
        if not data:
            return None

        # 根据 action 模式生成记忆条目队列
        if self.action == "none":
            # 直接模式：原始数据作为单个条目
            entries = [data]
        elif self.action == "tri_embed":
            # 三元组模式：提取三元组并生成多个条目
            entries = self._extract_and_embed_triples(data)
            # 即使为空列表也继续流转，避免阻塞 Pipeline
            if not entries:
                entries = []
        elif self.action == "validate":
            # TODO: 实现数据验证逻辑
            entries = [data]
        elif self.action == "transform":
            # TODO: 实现数据转换逻辑
            entries = [data]
        else:
            # 未知操作模式
            entries = [data]

        # 在原字典基础上添加 memory_entries 队列
        data["memory_entries"] = entries

        return data

    def _extract_and_embed_triples(self, data):
        """提取三元组并进行 Embedding

        Args:
            data: 对话数据（字典格式），包含 "dialogs" 字段：
                {
                    "task_id": "xxx",
                    "session_id": x,
                    "dialog_id": y,
                    "dialogs": [{"speaker": "xxx", "text": "xxx", "date_time": "xxx"}, ...]
                }

        Returns:
            记忆条目列表，每个条目包含：
            {
                "triple": (subject, predicate, object),
                "refactor": "subject predicate object",
                "embedding": numpy.ndarray,
                "metadata": {...}  # 可选的元数据
            }
        """
        # 1. 从 data 中提取 dialogs 并格式化为字符串
        dialogs = data.get("dialogs", [])
        dialogue = self.parser.format_dialogue(dialogs)

        # 2. 使用 LLM 提取三元组
        prompt = self.triple_extraction_prompt.replace("{dialogue}", dialogue)
        triples_text = self.generator.generate(prompt)

        # 3. 解析三元组
        triples = self.parser.parse_triples(triples_text)

        # 4. 重构三元组为自然语言描述
        refactor_descriptions = self.parser.refactor_triples(triples)
        
        # 5. 去重：基于 refactor 描述去重（保留首次出现）
        seen_refactors = set()
        unique_triples = []
        unique_refactors = []
        
        for triple, refactor in zip(triples, refactor_descriptions):
            if refactor not in seen_refactors:
                seen_refactors.add(refactor)
                unique_triples.append(triple)
                unique_refactors.append(refactor)
        
        # 如果去重后为空，直接返回
        if not unique_refactors:
            return []
        
        # 6. 生成 Embedding（只对去重后的数据生成）
        embeddings = self.embedding_generator.embed_batch(unique_refactors)

        # 7. 构建记忆条目列表
        memory_entries = []
        for i, (triple, refactor) in enumerate(zip(unique_triples, unique_refactors)):
            entry = {
                "dialogs": dialogs,
                "triple": triple,
                "refactor": refactor,
                "embedding": embeddings[i] if embeddings is not None else None,
            }
            memory_entries.append(entry)

        return memory_entries
