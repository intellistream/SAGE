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

            '''
            {
                "answer": str,  # 答案
                "context": str,  # 上下文
                "history": str,  # 历史信息
                "question": str  # 问题
            }
            '''
            # 合并 context_stm 和 context_ltm 到 history_dialogue
            history_dialogue = input_data.context_ltm + input_data.context_stm
            history_dialogue = "".join(history_dialogue) if history_dialogue else None

            # 将 external_docs 放入 external_corpus
            external_corpus = input_data.external_docs
            external_corpus = "".join(external_corpus) if external_corpus else None

            store_data = {
                "answer": input_data.answer,
                "question": input_data.natural_query,
                "history_dialogue": history_dialogue,
                "external_corpus": external_corpus
            }
            final_store_data = generate_prompt(self.reorganize_template, **store_data)

            # Write to the specified memory layer
            self.memory_manager.store_to_memory(data=final_store_data, memory_layer=memory_layer, **kwargs)
            self.logger.info(f"Data written to {memory_layer}")

        except Exception as e:
            self.logger.error(f"Error writing to {memory_layer}: {str(e)}")
            raise RuntimeError(f"Failed to write to {memory_layer}: {str(e)}")
