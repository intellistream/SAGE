import torch
import hashlib
import numpy as np 
from pycandy import VectorDB # type: ignore 
from sage.core.neuromem_before.storage_engine.base_physical_memory import BaseVectorPhysicalMemory, TextStorageLayer

'''
    only 128 dimension can be used.
    只能接受128维度的向量.
    can not perform deletion operation.
    不能执行删除操作.
'''

def _generate_embedding_key(embedding):
    """Generate a hash key for numpy.ndarray or torch.Tensor."""
    if torch.is_tensor(embedding):
        embedding = embedding.cpu().detach().numpy()
    elif not isinstance(embedding, np.ndarray):
        raise TypeError(f"Expected numpy.ndarray or torch.Tensor, got {type(embedding)}")

    # Ensure float32 and contiguous memory
    embedding = np.ascontiguousarray(embedding, dtype=np.float32).reshape(-1)
    return hashlib.sha256(embedding.tobytes()).hexdigest()


class CandyMemory(BaseVectorPhysicalMemory):
    """
    A Candy-based Vector DB Storage for SAGE.
    Using cosine similarity for KNN search(temporarily).
    """
    def __init__(
            self,
            vector_dim: int,
            search_algorithm: str,
            top_k: int, 
            retrieval_threshold: float, 
            physical_data_path: str
        ):
        """
        Initialize CandyDB for session storage and retrieval.

        :param vector_dim: Dimensionality of the embeddings.
        :param search_algorithm: Search algorithm to use in VectorDB.
        """
        super().__init__()
        self.top_k = top_k
        self.retrieval_threshold = retrieval_threshold
        self.db = VectorDB(vector_dim, search_algorithm)
        self.raw_data_storage = TextStorageLayer(physical_data_path)
        self.embedding_to_raw_map = {}

        self.logger.info("CandyMemory(Physical Memory) initialized for session storage.")

    def store(self, embedding = None, raw_data = None):
        if raw_data is None:
                raise ValueError("Raw data must be provided for Storage.")
        elif embedding is None:
                raise ValueError("Embedding must be provided for Storage.")

        # Save the raw data and get its ID
        raw_id = self.raw_data_storage.add_text(raw_data)

        # Generate a hash key for the embedding
        embedding_key = _generate_embedding_key(embedding)

        # Insert the embedding into VectorDB
        self.db.insert_tensor(embedding.clone())

        # Map the embedding hash to the raw ID
        self.embedding_to_raw_map[embedding_key] = raw_id

        self.logger.info(f"Stored embedding with Raw ID: {raw_id}")

        return raw_id    
                    
    def retrieve(self, embedding=None, k = None):
        if embedding is None:
            raise ValueError("Embedding must be provided for Retrieve.")
        
        try:
            # Query the database for nearest neighbors
            if k is not None and k > 0:
                self.top_k = k
            embeddings = self.db.query_nearest_tensors(embedding.clone(), self.top_k)
            results = []

            for emb in embeddings:
                embedding_key = _generate_embedding_key(emb)
                raw_id = self.embedding_to_raw_map.get(embedding_key)
                
                if raw_id is None:
                    results.append(None)
                    continue
                    
                raw_data_path = self.raw_data_storage.get_text_path(raw_id)
                if not raw_data_path:
                    results.append(None)
                    continue
                    
                try:
                    with open(raw_data_path, 'r') as file:
                        results.append(file.read())
                    self.logger.debug(f"Retrieved context: {results[-1]}")
                except Exception as e:
                    self.logger.error(f"Error reading raw data file {raw_data_path}: {str(e)}")
                    results.append(None)

            self.logger.info(f"Retrieved {len(results)} raw data items from dynamic contextual memory.")
            return results
        
        except Exception as e:
            self.logger.error(f"Error retrieving items: {str(e)}")
            raise RuntimeError(f"Failed to retrieve items: {str(e)}")      

    def delete(self, embedding = None):
        if embedding is None:
            raise ValueError("Embedding must be provided for Delete.")
        
        try:
            # Remove the embedding from VectorDB
            if isinstance(embedding, np.ndarray):
                tensor = torch.from_numpy(embedding)
            else:
                tensor = embedding
            self.db.remove_tensor(tensor.clone())

            # Remove the embedding-to-raw mapping and raw data
            embedding_key = tuple(embedding.tolist())
            raw_id = self.embedding_to_raw_map.pop(embedding_key, None)
            if raw_id:
                self.raw_data_storage.delete_text(raw_id)

            self.logger.info("Deleted embedding and its associated raw data.")

        except Exception as e:
            self.logger.error(f"Error deleting embedding: {str(e)}")
            raise RuntimeError(f"Failed to delete embedding: {str(e)}")
        
    def clean(self):
        self.raw_data_storage.delete_all_data()

if __name__ == "__main__":
    import json
    from pathlib import Path

    current_dir = Path(__file__).parent
    config_path = current_dir.parent / "default_memory" / "default_memory_config.json"

    def LTM_Test():
        with open(config_path, 'r') as f:
            config = json.load(f)
            config = config.get("neuromem").get("CandyMemory_LTM")
        print("LTM Test:")
        test = CandyMemory(vector_dim = config.get("ltm_vector_dim")
                , search_algorithm = config.get("ltm_search_algorithm")
                , top_k = config.get("ltm_top_k")
                , retrieval_threshold = config.get("ltm_retrieval_threshold")
                , physical_data_path = config.get("ltm_physical_data_path")
                )
        return test

    def DCM_Test():
        with open(config_path, 'r') as f:
            config = json.load(f)
            config = config.get("neuromem").get("CandyMemory_DCM")
        print("DCM Test:")
        test = CandyMemory(vector_dim = config.get("dcm_vector_dim")
                , search_algorithm = config.get("dcm_search_algorithm")
                , top_k = config.get("dcm_top_k")
                , retrieval_threshold = config.get("dcm_retrieval_threshold")
                , physical_data_path = config.get("dcm_physical_data_path")
                )
        return test

    # test = DCM_Test()
    test = LTM_Test()

    import torch.nn.functional as F
    vectors = torch.randn(5, 128)

    vectors[1] = vectors[0] * 0.7 + vectors[2] * 0.3  
    vectors[2] = vectors[1] * 0.6 + vectors[3] * 0.4 
    vectors[4] = vectors[3] * 0.5 + vectors[2] * 0.5 
    vectors = F.normalize(vectors, p=2, dim=1)

    words = ["apple", "banana", "orange", "pear", "grape"]

    for i, word in enumerate(words):
        test.store(vectors[i], word)

    print(test.retrieve(vectors[1]))
    print(test.retrieve(vectors[2]))
    print(test.retrieve(vectors[3]))
    # python -m sage.core.neuromem.storage_engine.candy_impl