import logging

from sage.core.neuromem.memory.dynamic_contextual_memory import DynamicContextualMemory
from sage.core.neuromem.memory.long_term_memory import LongTermMemory
from sage.core.neuromem.memory.short_term_memory import ShortTermMemory
from sage.core.neuromem.pipelines.ingestion_pipeline import DynamicIngestionPipeline
from sage.core.neuromem.pipelines.integration_pipeline import IntegrationPipeline
from sage.utils.text_processing import process_session_text_to_embedding, process_text_to_embedding


class NeuronMemManager:
    """
    负责 长短期记忆的选择
    负责 进出数据的修剪和扩展
    使用LLM 和 CANDY进行相关推荐和记忆存储
    Dynamic Knowledge Ingestion Pipeline
    Contextual Knowledge Integration Pipeline
    """

    def __init__(self, memory_layers):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_layers = memory_layers
        self.integration_pipeline = IntegrationPipeline(self)
        self.ingestion_pipeline = DynamicIngestionPipeline(self)  # Initialize ingestion pipeline


    def get_memory_layers(self):
        return self.memory_layers


    def get_memory_layers_by_name(self, name):
        return self.memory_layers[name]


    def retrieve(self, query):
        """
        Retrieve relevant data for a given query using an adaptive retrieval plan.
        :param query: User's query (plain text).
        :return: Retrieved data.
        """
        try:
            return self.integration_pipeline.execute(query)

        except Exception as e:
            self.logger.error(f"Retrieval error: {str(e)}")
            raise RuntimeError(f"Error in adaptive retrieval: {str(e)}")


    def store(self, content, trigger_event):
        """
        Public API for ingestion. Decides where to store based on trigger event.
        :param content: Data to store (only needed for STM ingestion).
        :param trigger_event: Reason for storing (e.g., "LLM Response is valid", "Session Ended").
        """
        self.ingestion_pipeline.execute(content, trigger_event)


    def store_to_memory(self, data, raw_data=None, key=None, memory_layer="short_term"):
        """
        Store data into a specified memory layer.

        :param data: The data to store (e.g., {"question": ..., "answer": ...}).
        :param memory_layer: The target memory layer ("short_term" or "long_term").
        :param key: Optional key for the data. Auto-generated if not provided.
        """
        try:
            memory = self.get_memory_layers_by_name(memory_layer)
            if not memory:
                raise ValueError(f"Memory layer '{memory_layer}' not found.")
            if memory_layer == "long_term" or memory_layer == "dynamic_contextual":
                memory.store(data, raw_data=raw_data)
            else:
                memory.store(data, key=key)
            self.logger.info(f"Stored data in {memory_layer}: {data}")
        except Exception as e:
            self.logger.error(f"Failed to store data in {memory_layer}: {str(e)}")
            raise RuntimeError(f"Error storing data in {memory_layer}: {str(e)}")


    def retrieve_from_memory(self, memory_layer="short_term", key=None, k=1, query_embedding=None):
        """
        Retrieve data from a specified memory layer.

        :param memory_layer: The memory layer to retrieve from ("short_term" or "long_term").
        :param key: Optional key for specific data. If None, retrieves the first `k` items.
        :param k: Number of items to retrieve if no key is provided.
        :param query_embedding: For long-term memory, the embedding_model to query similar sessions.
        :return: Retrieved data.
        """
        try:
            memory = self.get_memory_layers_by_name(memory_layer)
            if not memory:
                raise ValueError(f"Memory layer '{memory_layer}' not found.")

            if memory_layer == "long_term" or memory_layer == "dynamic_contextual":
                if query_embedding is None:
                    raise ValueError("Query embedding_model must be provided for long-term memory retrieval.")
                data = memory.retrieve(query_embedding=query_embedding, k=k)
            else:
                data = memory.retrieve(key=key, k=k)

            self.logger.info(f"Retrieved data from {memory_layer}: {data}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to retrieve data from {memory_layer}: {str(e)}")
            raise RuntimeError(f"Error retrieving data from {memory_layer}: {str(e)}")


    def flush_stm_to_ltm(self):
        """
        Transfer all session data from STM to LTM at the end of a session.
        """
        try:
            stm = self.get_memory_layers_by_name("short_term")
            ltm = self.get_memory_layers_by_name("long_term")

            # Retrieve all STM data
            session_data = stm.retrieve(k=len(stm.storage))
            self.logger.info(f"Flushing session data from STM to LTM: {session_data}")

            # Process and store session data in LTM
            if session_data:
                combined_session_text = ' '.join(str(item) for item in session_data)
                session_embedding = process_text_to_embedding(combined_session_text)
                ltm.store(session_embedding, combined_session_text)
                self.logger.info(f"Flushed session data to LTM: {combined_session_text}")

            # Clear STM
            stm.clean()
            self.logger.info("Cleared STM after flushing session data to LTM.")
        except Exception as e:
            self.logger.error(f"Error during STM to LTM flush: {str(e)}")
            raise RuntimeError(f"Failed to flush STM to LTM: {str(e)}")


    def execute(self, pipeline_name):
        """
        Execute memory access pipeline, such as Knowledge Ingestion and Knowledge Extraction + Integration.
        """
        raise NotImplementedError("Pipeline execution is not yet implemented.")

    # Start a chrono thread that can run backend pipeline periodically.



if __name__ == '__main__':
    # Initialize memory manager
    memory_manager = NeuronMemManager({
        "short_term": ShortTermMemory(),
        "long_term": LongTermMemory(
            vector_dim=128,  # Vector dimensions
            search_algorithm="knnsearch"  # Search algorithm
        ),
        "dynamic_contextual": DynamicContextualMemory(
            vector_dim=128,  # Vector dimensions
            search_algorithm="knnsearch"  # Search algorithm
        )
    })

    # Store data in STM
    memory_manager.store_to_memory({"question": "What is AI?", "answer": "Artificial Intelligence"},
                                   memory_layer="short_term")

    # Store data in STM
    memory_manager.store_to_memory({"question": "What is AI?", "answer": "Artificial Intelligence 22323"},
                                   memory_layer="short_term")

    # Retrieve data from STM
    data = memory_manager.retrieve_from_memory(memory_layer="short_term", k=1)
    print("Retrieved from STM:", data)

    # End of session: Flush STM to LTM
    memory_manager.flush_stm_to_ltm()

    new_query = "What is AI?"
    query_embedding = process_text_to_embedding(new_query)

    # Retrieve data from LTM
    ltm_data = memory_manager.retrieve_from_memory(memory_layer="long_term", query_embedding=query_embedding, k=1)
    print("Retrieved from LTM:", ltm_data)

    # Test Dynamic Contextual Memory
    context = "Artificial Intelligence revolutionizes technology."
    context_embedding = process_text_to_embedding(context)

    # Store context in DCM
    memory_manager.store_to_memory(data=context_embedding, raw_data=context,
                                   memory_layer="dynamic_contextual")

    # Query DCM
    query_context = "AI and technology."
    query_embedding = process_text_to_embedding(query_context)
    dcm_data = memory_manager.retrieve_from_memory(memory_layer="dynamic_contextual", query_embedding=query_embedding,
                                                   k=1)
    print("Retrieved from DCM:", dcm_data)