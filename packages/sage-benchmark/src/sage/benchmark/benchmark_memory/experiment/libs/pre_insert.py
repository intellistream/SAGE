"""预插入处理模块 - 在记忆插入前的预处理（可选）

对于短期记忆（STM），通常不需要预处理，直接插入即可。
此模块保留用于未来扩展（如数据验证、格式转换等）。
"""

from sage.benchmark.benchmark_memory.experiment.utils.dialogue_parser import DialogueParser
from sage.benchmark.benchmark_memory.experiment.utils.triple_parser import TripleParser
from sage.benchmark.benchmark_memory.experiment.utils.embedding_generator import (
    EmbeddingGenerator,
)
from sage.benchmark.benchmark_memory.experiment.utils.llm_generator import LLMGenerator
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

        # 初始化解析器
        self.dialogue_parser = DialogueParser()
        self.triple_parser = TripleParser()

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
        # 根据 action 模式生成记忆条目队列
        if self.action == "none":
            # 直接模式：原始数据作为单个条目
            # 示例 entries:
            # [
            #     {
            #         "task_id": "1",
            #         "session_id": 0,
            #         "dialog_id": 2,
            #         "dialogs": [
            #             {"speaker": "user1", "text": "今天天气真好", "date_time": "2024-01-01 10:00"},
            #             {"speaker": "user2", "text": "是啊，适合出去玩", "date_time": "2024-01-01 10:01"}
            #         ],
            #         "dialog_len": 2,
            #         "packet_idx": 1,
            #         "total_packets": 10
            #     }
            # ]
            entries = [data]
        elif self.action == "tri_embed":
            # 三元组模式：提取三元组并生成多个条目
            # 示例 entries (从一段对话中提取多个三元组):
            # [
            #     {
            #         "dialogs": [{"speaker": "user1", "text": "...", "date_time": "..."}],
            #         "triple": ("Alice", "likes", "coffee"),
            #         "refactor": "Alice likes coffee",
            #         "embedding": numpy.ndarray([0.1, 0.2, ...]) 
            #     },
            #     {
            #         "dialogs": [{"speaker": "user1", "text": "...", "date_time": "..."}],
            #         "triple": ("Bob", "works at", "Google"),
            #         "refactor": "Bob works at Google",
            #         "embedding": numpy.ndarray([0.3, 0.4, ...])  # 768维向量
            #     }
            # ]
            # 即使为空列表也继续流转，避免阻塞 Pipeline
            entries = self._extract_and_embed_triples(data)
        elif self.action == "validate":
            # TODO: 实现数据验证逻辑
            # 示例 entries (验证通过后原样返回):
            # [
            #     {
            #         "task_id": "1",
            #         "session_id": 0,
            #         "dialog_id": 2,
            #         "dialogs": [...],
            #         "dialog_len": 2,
            #         "packet_idx": 1,
            #         "total_packets": 10
            #     }
            # ]
            entries = [data]
        elif self.action == "transform":
            # TODO: 实现数据转换逻辑
            # 示例 entries (转换后的数据，格式待定):
            # [
            #     {
            #         "task_id": "1",
            #         "session_id": 0,
            #         "dialog_id": 2,
            #         "dialogs": [...],  # 可能经过格式转换
            #         ...
            #     }
            # ]
            entries = [data]
        else:
            # 未知操作模式，原样返回
            # 示例 entries: [原始 data 字典]
            entries = [data]

        # 在原字典基础上添加 memory_entries 队列
        # 最终送往下游的完整数据示例:
        #
        # 【action="none" 时】:
        # {
        #     "task_id": "1",
        #     "session_id": 0,
        #     "dialog_id": 2,
        #     "dialogs": [{"speaker": "user1", "text": "今天天气真好", "date_time": "2024-01-01 10:00"}, ...],
        #     "dialog_len": 2,
        #     "packet_idx": 1,
        #     "total_packets": 10,
        #     "memory_entries": [
        #         {... 与外层相同的完整 data 字典 ...}
        #     ]
        # }
        #
        # 【action="tri_embed" 时】:
        # {
        #     "task_id": "1",
        #     "session_id": 0,
        #     "dialog_id": 2,
        #     "dialogs": [...],
        #     "dialog_len": 2,
        #     "packet_idx": 1,
        #     "total_packets": 10,
        #     "memory_entries": [
        #         {"dialogs": [...], "triple": ("Alice", "likes", "coffee"), "refactor": "Alice likes coffee", "embedding": ndarray},
        #         {"dialogs": [...], "triple": ("Bob", "works at", "Google"), "refactor": "Bob works at Google", "embedding": ndarray}
        #     ]
        # }
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
        dialogue = self.dialogue_parser.format(dialogs)

        # 2. 使用 LLM 提取三元组
        prompt = self.triple_extraction_prompt.replace("{dialogue}", dialogue)
        triples_text = self.generator.generate(prompt)

        # 3. 解析三元组并重构为自然语言描述
        triples, refactor_descriptions = self.triple_parser.parse_and_refactor(triples_text)

        # 4. 去重：基于 refactor 描述去重（保留首次出现）
        unique_triples, unique_refactors = self.triple_parser.deduplicate(triples, refactor_descriptions)
        
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
