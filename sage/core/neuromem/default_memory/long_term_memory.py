import logging
from sage.core.neuromem.default_memory.base_memory import BaseMemory

from sage.core.neuromem.storage_engine import (
    verify_physical_memory_implementation,
    check_physical_memory_env_vars,
    get_physical_memory_class,
    get_filtered_config,
)

class LongTermMemory(BaseMemory):
    """
    Long-term memory layer that stores entire sessions in a VectorDB for retrieval based on similarity.
    """

    def __init__(self, config):
        """
        Initialize the LongTermMemory with a VectorDB for session storage and retrieval.
        :param retrieval_threshold: Retrieval threshold.
        :param vector_dim: Dimensionality of the embeddings.
        :param Top_k: Define to return the K closest results. 
        :param search_algorithm: Search algorithm to use in VectorDB.
        """
        super().__init__()
        self.logger.info(f"\033[92mLTM\033[0m is starting initialization with Physical Memory \033[92m{config.get('DCM_Physical_Memory')}\033[0m")

        self.physical_memory_name = config.get("LTM_Physical_Memory")
        self.config = config.get(self.physical_memory_name + "_LTM")
        verify_physical_memory_implementation("VECTOR_MEMORY", self.physical_memory_name)
        check_physical_memory_env_vars(self.physical_memory_name)

        self.physical_memory = get_physical_memory_class(
            physical_memory_name = self.physical_memory_name,
            **get_filtered_config(self.config, "ltm_")
        )
        self.logger.info("\033[92mLCM\033[0m initialization ends")
        
    def store(self, raw_data, embedding):
        return self.physical_memory.store(embedding, raw_data)

    def retrieve(self, embedding, k=None):
        return self.physical_memory.retrieve(embedding, k)

    def delete(self, embedding):
        return self.physical_memory.delete(embedding)
    
    def clean(self):
        self.physical_memory.clean()

if __name__ == "__main__":
    import json
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "default_memory_config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
    test = LongTermMemory(config.get("neuromem"))
    print(config.get("neuromem").get("DCM_Physical_Memory"))
    import torch
    id = torch.randn(128)
    test.store(id, "nihao")
    id1 = torch.randn(128)
    test.store(id1, "hello")
    id3 = torch.randn(128)
    test.store(id3, "ohayo")
    print(test.retrieve(id))

    # python -m sage.core.neuromem.default_memory.long_term_memory
