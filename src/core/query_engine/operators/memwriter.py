import logging
from src.core.query_engine.operators.base_operator import BaseOperator
from src.core.prompts.utils import generate_prompt

class MemWriter(BaseOperator):
    """
    Operator for generating structured documentation or outputs.
    """

    def __init__(self, memory_manager, reorganize_template):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.reorganize_template = reorganize_template
        self.memory_manager = memory_manager

    def execute(self, input_data, memory_layer="short_term", **kwargs):
        """
        Write data to the specified memory layer.

        :param input_data: Data to write, expected to have `question` and `answer` attributes.
        :param memory_layer: Target memory layer ("short_term", "long_term", or "dynamic_contextual").
        :param kwargs: Additional parameters for memory operations.
        """
        try:
            # Validate input data structure
            if not isinstance(input_data[0], dict) or "raw_data" not in input_data[0] or "question" not in \
                    input_data[0]["raw_data"] or "answer" not in input_data[0]:
                raise ValueError("input_data must be a dictionary with 'question' in 'raw_data' and 'answer' keys.")
            input_data = self._flatten_input_data(input_data[0])
            '''
            {
                "answer": str,  # 答案
                "context": str,  # 上下文
                "history": str,  # 历史信息
                "question": str  # 问题
            }
            '''
            final_store_data = generate_prompt(self.reorganize_template, **input_data)

            # Write to the specified memory layer
            self.memory_manager.store_to_memory(data=final_store_data, memory_layer=memory_layer, **kwargs)
            self.logger.info(f"Data written to {memory_layer}")#: {input_data[0]}")

        except Exception as e:
            self.logger.error(f"Error writing to {memory_layer}: {str(e)}")
            raise RuntimeError(f"Failed to write to {memory_layer}: {str(e)}")

    def _flatten_input_data(self, input_data):
        """
        将 input_data 中的 raw_data 字段提取出来，使其与 answer 同级。

        :param input_data: 原始输入数据
        :return: 扁平化后的数据
        """
        # 提取 raw_data 中的字段，如果字段不存在则使用默认值
        flattened_data = {
            "context": input_data["raw_data"].get("context", None),  # 上下文，默认为 None
            "history": input_data["raw_data"].get("history", None),  # 历史信息，默认为 None
            "question": input_data["raw_data"].get("question", ""),  # 问题，默认为空字符串
            "answer": input_data.get("answer", "")  # 答案，默认为空字符串
        }
        return flattened_data