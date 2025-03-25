import logging


class DynamicIngestionPipeline:
    """
    Dynamic Knowledge Ingestion Pipeline for memory management.
    Decides where to store knowledge based on trigger events.
    """

    def __init__(self, memory_manager):
        """
        Initialize the ingestion pipeline.
        :param memory_manager: Reference to NeuronMemManager.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_manager = memory_manager

    def execute(self, content, trigger_event):
        """
        Stores knowledge in the appropriate memory layer based on the trigger event.
        :param content: The knowledge content to store (only needed for "LLM Response is valid").
        :param trigger_event: Event that triggered this storage.
        """
        self.logger.info(f"Ingesting knowledge based on trigger: {trigger_event}")

        if trigger_event == "Question_Answer":
            self.memory_manager.store_to_memory(content, memory_layer="short_term")

        elif trigger_event == "Session_Ended":
            self.memory_manager.flush_stm_to_ltm()  # No need to pass content

        else:
            self.logger.warning(f"Unknown trigger event: {trigger_event}")