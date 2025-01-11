import logging
from src.core.query_engine.operators.base_operator import BaseOperator


class MemWriter(BaseOperator):
    """
    Operator for generating structured documentation or outputs.
    """

    def __init__(self, memory_manager):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_manager = memory_manager

    def execute(self, input_data, memory_layer="short_term", **kwargs):
        """
        Write data to the specified memory layer.

        :param input_data: Data to write, expected to have `question` and `answer` attributes.
        :param memory_layer: Target memory layer ("short_term", "long_term", or "dynamic_contextual").
        :param kwargs: Additional parameters for memory operations.
        """
        try:
            # Validate memory layer
            memory = self.memory_manager.get_memory_layers_by_name(memory_layer)
            if not memory:
                raise ValueError(f"Memory layer '{memory_layer}' not found.")

            # Write data into the specified memory layer
            memory.store(input_data[0])
            self.logger.info(f"Data written to {memory_layer}: {input_data[0]}")

        except Exception as e:
            self.logger.error(f"Error writing to {memory_layer}: {str(e)}")
            raise RuntimeError(f"Failed to write to {memory_layer}: {str(e)}")