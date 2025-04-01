import logging

from sage.core.neuromem.default_memory.dynamic_contextual_memory import DynamicContextualMemory
from sage.core.neuromem.default_memory.long_term_memory import LongTermMemory
from sage.core.neuromem.default_memory.short_term_memory import ShortTermMemory

import torch
from transformers import AutoTokenizer, AutoModel
from sage.core.neuromem.default_memory import (
    get_default_memory_class,
)

class TextPreprocessor:
    def __init__(self, model_name='sentence-transformers/all-MiniLM-L6-v2'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.fixed_dimension = 128  # Fixed dimension for the embedding vectors

    def generate_embedding_with_sliding_window(self, text: str, max_length=512, stride=256):
        """
        Generate an embedding for the given text using a sliding window approach.
        """
        # Tokenize the input text with sliding windows
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            stride=stride,
            return_overflowing_tokens=True,
            padding="max_length",
            return_tensors="pt"
        )

        embeddings = []
        with torch.no_grad():
            for input_ids in inputs["input_ids"]:# type: ignore 
                # Forward pass through the model
                output = self.model(input_ids.unsqueeze(0))

                # Mean pooling to obtain the embedding
                embedding = output.last_hidden_state.mean(dim=1).squeeze()
                embeddings.append(embedding)

        # Aggregate embeddings (e.g., mean pooling across all windows)
        aggregated_embedding = torch.stack(embeddings).mean(dim=0)

        # Adjust the aggregated embedding to match the fixed dimension
        if aggregated_embedding.size(0) > self.fixed_dimension:
            aggregated_embedding = aggregated_embedding[:self.fixed_dimension]  # Truncate if larger
        elif aggregated_embedding.size(0) < self.fixed_dimension:
            # Pad with zeros if smaller
            padding = torch.zeros(
                self.fixed_dimension - aggregated_embedding.size(0), device=aggregated_embedding.device
            )
            aggregated_embedding = torch.cat((aggregated_embedding, padding))

        # Return the embedding as a float32 PyTorch Tensor
        return aggregated_embedding.to(dtype=torch.float32)

    def generate_embedding(self, text: str):
        """
        Generate a fixed-dimension embedding for the given text using the model.
        """
        # Tokenize the input text for the model
        inputs = self.tokenizer(text, return_tensors='pt')

        # Generate embeddings using the model
        with torch.no_grad():
            outputs = self.model(**inputs)

            # Pooling strategy (mean pooling)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()

        # Ensure the embedding has the correct fixed dimension
        if embedding.size(0) > self.fixed_dimension:
            embedding = embedding[:self.fixed_dimension]  # Truncate if larger
        elif embedding.size(0) < self.fixed_dimension:
            # Pad with zeros if smaller
            padding = torch.zeros(self.fixed_dimension - embedding.size(0), device=embedding.device)
            embedding = torch.cat((embedding, padding))

        # Return the embedding as a float32 PyTorch Tensor
        return embedding.to(dtype=torch.float32)

def process_text_to_embedding(text, max_length=512, stride=256):
    """
    Process a long text into a single embedding using chunking and aggregation.
    :param text: Input text to process.
    :param max_length: Maximum token length for each chunk.
    :param stride: Overlap between consecutive chunks.
    :return: Aggregated embedding as a PyTorch tensor.
    """
    logger = logging.getLogger(__name__)
    text_preprocessor = TextPreprocessor()

    try:
        """
            待修复，最大仅支持512个token不太够用!！
        """
        # Tokenize the text to check its length
        tokens = text_preprocessor.tokenizer.tokenize(text)
        if len(tokens) > max_length:
            logger.warning(f"Input text length ({len(tokens)}) exceeds model's max length ({max_length}). Truncating text.")
            text = text_preprocessor.tokenizer.decode(text_preprocessor.tokenizer.encode(text, max_length=max_length, truncation=True))

        # Tokenize with truncation, stride, and overlapping chunks
        tokens = text_preprocessor.tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            stride=stride,
            return_overflowing_tokens=True,
            padding="max_length",
            return_tensors="pt"
        )

        embeddings = []
        for chunk in tokens["input_ids"]: # type: ignore 
            # Generate embedding for each chunk
            chunk_text = text_preprocessor.tokenizer.decode(chunk, skip_special_tokens=True)
            embedding = text_preprocessor.generate_embedding(chunk_text)  # Returns a tensor
            embeddings.append(embedding)

        # Aggregate embeddings (mean pooling)
        if embeddings:
            aggregated_embedding = torch.stack(embeddings).mean(dim=0)
            logger.info(f"Processed text into embedding of shape: {aggregated_embedding.shape}")
            return aggregated_embedding.to(dtype=torch.float32)  # Ensure float32 tensor
        else:
            raise ValueError("No embeddings generated. The input text might be empty.")
    except Exception as e:
        logger.error(f"Error processing text to embedding: {str(e)}")
        raise RuntimeError(f"Text processing failed: {str(e)}")



class NeuronMemManager:
    """
    STM LTM DCM Manager
    """

    def __init__(self, memory_layers = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.memory_layers = memory_layers or {}

    def register(self, memory_table_name, memory_collection):
        """
        Register a MemoryCollection instance.
        """
        if memory_table_name in self.memory_layers:
            self.logger.warning(f"Memory table {memory_table_name} already exists, overwriting.")

        self.memory_layers[memory_table_name] = memory_collection
        return memory_collection

    def list_collections(self):
        return list(self.memory_layers.values())

    def get(self, memory_table_name):
        return self.memory_layers.get(memory_table_name)
            
    # def get_memory_layers(self):
    #     return self.memory_layers


    # def get_memory_layers_by_name(self, name):
    #     return self.memory_layers[name]


    # def store_to_memory(self, data, raw_data=None, key=None, memory_layer="short_term"):
    #     """
    #     Store data into a specified memory layer.

    #     :param data: The data to store (e.g., {"question": ..., "answer": ...}).
    #     :param memory_layer: The target memory layer ("short_term" or "long_term").
    #     :param key: Optional key for the data. Auto-generated if not provided.
    #     """
    #     try:
    #         memory = self.get_memory_layers_by_name(memory_layer)
    #         if not memory:
    #             raise ValueError(f"Memory layer '{memory_layer}' not found.")
    #         if memory_layer == "long_term" or memory_layer == "dynamic_contextual":
    #             memory.store(data, raw_data=raw_data)
    #         else:
    #             memory.store(data, key=key)
    #         self.logger.info(f"Stored data in {memory_layer}")#: {data}")
    #     except Exception as e:
    #         self.logger.error(f"Failed to store data in {memory_layer}: {str(e)}")
    #         raise RuntimeError(f"Error storing data in {memory_layer}: {str(e)}")


    # def retrieve_from_memory(self, memory_layer="short_term", key=None, k=1, query_embedding=None):
    #     """
    #     Retrieve data from a specified memory layer.

    #     :param memory_layer: The memory layer to retrieve from ("short_term" or "long_term").
    #     :param key: Optional key for specific data. If None, retrieves the first `k` items.
    #     :param k: Number of items to retrieve if no key is provided.
    #     :param query_embedding: For long-term memory, the embedding to query similar sessions.
    #     :return: Retrieved data.
    #     """
    #     try:
    #         memory = self.get_memory_layers_by_name(memory_layer)
    #         if not memory:
    #             raise ValueError(f"Memory layer '{memory_layer}' not found.")

    #         if memory_layer == "long_term" or memory_layer == "dynamic_contextual":
    #             if query_embedding is None:
    #                 raise ValueError("Query embedding must be provided for long-term memory retrieval.")
    #             data = memory.retrieve(query_embedding=query_embedding, k=k)
    #         else:
    #             data = memory.retrieve(key=key, k=k)

    #         self.logger.info(f"Retrieved data from {memory_layer}")#(: {data}")
    #         return data
    #     except Exception as e:
    #         self.logger.error(f"Failed to retrieve data from {memory_layer}: {str(e)}")
    #         raise RuntimeError(f"Error retrieving data from {memory_layer}: {str(e)}")


    # def flush_stm_to_ltm(self):
    #     """
    #     Transfer all session data from STM to LTM at the end of a session.
    #     """
    #     try:
    #         stm = self.get_memory_layers_by_name("short_term")
    #         ltm = self.get_memory_layers_by_name("long_term")

    #         # Retrieve all STM data
    #         session_data = stm.retrieve(k=len(stm.storage))
    #         self.logger.info(f"Flushing session data from STM to LTM")# : {session_data}")

    #         # Process and store session data in LTM
    #         if session_data:
    #             combined_session_text = ' '.join(str(item) for item in session_data)
    #             session_embedding = process_text_to_embedding(combined_session_text)
    #             ltm.store(session_embedding, combined_session_text)
    #             self.logger.info(f"Flushed session data to LTM:")# {combined_session_text}")

    #         # Clear STM
    #         stm.clean()
    #         self.logger.info("Cleared STM after flushing session data to LTM.")
    #     except Exception as e:
    #         self.logger.error(f"Error during STM to LTM flush: {str(e)}")
    #         raise RuntimeError(f"Failed to flush STM to LTM: {str(e)}")


    # def execute(self, pipeline_name):
    #     """
    #     Execute memory access pipeline, such as Knowledge Ingestion and Knowledge Extraction + Integration.
    #     """
    #     raise NotImplementedError("Pipeline execution is not yet implemented.")

# python -m sage.core.neuromem.memory_manager

# if __name__ == '__main__':
#     import json
#     import os
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     config_path = os.path.join(script_dir, "default_memory/default_memory_config.json")
#     with open(config_path, 'r') as f:
#         config = json.load(f)

#     # Initialize memory manager
#     memory_manager = NeuronMemManager({
#         "short_term": ShortTermMemory(),
#         "long_term": LongTermMemory(config.get("neuromem")),
#         "dynamic_contextual": DynamicContextualMemory(config.get("neuromem"))
#     })

#     # Store data in STM
#     memory_manager.store_to_memory({"question": "What is AI?", "answer": "Artificial Intelligence"},
#                                    memory_layer="short_term")

#     # Store data in STM
#     memory_manager.store_to_memory({"question": "What is AI?", "answer": "Artificial Intelligence 22323"},
#                                    memory_layer="short_term")

#     # Retrieve data from STM
#     data = memory_manager.retrieve_from_memory(memory_layer="short_term", k=1)
#     print("Retrieved from STM:", data)

#     # End of session: Flush STM to LTM
#     memory_manager.flush_stm_to_ltm()

#     new_query = "What is AI?"
#     query_embedding = process_text_to_embedding(new_query)

#     # Retrieve data from LTM
#     ltm_data = memory_manager.retrieve_from_memory(memory_layer="long_term", query_embedding=query_embedding, k=3)
#     print("Retrieved from LTM:", ltm_data)

#     # Test Dynamic Contextual Memory
#     context = "Artificial Intelligence revolutionizes technology."
#     context_embedding = process_text_to_embedding(context)

#     # Store context in DCM
#     memory_manager.store_to_memory(data=context_embedding, raw_data=context,
#                                    memory_layer="dynamic_contextual")

#     # Query DCM
#     query_context = "AI and technology."
#     query_embedding = process_text_to_embedding(query_context)
#     dcm_data = memory_manager.retrieve_from_memory(memory_layer="dynamic_contextual", query_embedding=query_embedding,
#                                                    k=3)
#     print("Retrieved from DCM:", dcm_data)