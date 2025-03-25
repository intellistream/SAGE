import hashlib

import torch
from pycandy import VectorDB

from sage.core.neuromem.memory.base_memory import BaseMemory
from sage.core.neuromem.memory.raw.local_raw_data_storage import LocalRawDataStorage
from sage.utils.file_path import RAW_FILE_DCM


def _generate_embedding_key(embedding):
    """
    Generate a unique, consistent hash key for the embedding.
    """
    # Ensure the tensor is on the CPU and detached
    if embedding.device.type != 'cpu':
        embedding = embedding.cpu()
    embedding = embedding.detach()  # Ensure no gradient tracking

    # Convert tensor to bytes without changing its type
    embedding_bytes = embedding.contiguous().view(-1).numpy().tobytes()

    # Create a SHA256 hash
    return hashlib.sha256(embedding_bytes).hexdigest()


class DynamicContextualMemory(BaseMemory):
    """
    Long-term memory layer that uses VectorDB for storage and retrieval.
    """

    def __init__(self, vector_dim, search_algorithm):
        """
        Initialize the LongTermMemory with a VectorDB and optional raw data retention.

        :param vector_dim: Dimensionality of the embeddings.
        :param search_algorithm: Search algorithm to use in VectorDB.
        """
        super().__init__()
        self.db = VectorDB(vector_dim, search_algorithm)
        self.raw_data_storage = LocalRawDataStorage(RAW_FILE_DCM)
        self.embedding_to_raw_map = {}

        self.logger.info("Persistent memory initialized with VectorDB.")

    def store(self, embedding, raw_data=None):
        """
        Store an embedding and its raw data.
        """
        if raw_data is None:
            raise ValueError("Raw data must be provided for persistent memory.")

        # Save the raw data and get its ID
        raw_id = self.raw_data_storage.add_text_as_rawdata(raw_data)

        # Generate a hash key for the embedding
        embedding_key = _generate_embedding_key(embedding)

        # Insert the embedding into VectorDB

        self.db.insert_tensor(embedding.clone())

        # Map the embedding hash to the raw ID
        self.embedding_to_raw_map[embedding_key] = raw_id

        self.logger.info(f"Stored embedding with Raw ID: {raw_id}")
        return raw_id

    def retrieve(self, query_embedding, k=1, **kwargs):
        """
        Retrieve the raw data contents associated with the query's nearest embeddings.
        """
        try:
            # Query the database for nearest neighbors
            embeddings = self.db.query_nearest_tensors(query_embedding.clone(), k)

            # Retrieve raw data contents
            results = []
            for embedding in embeddings:
                # Generate the same hash key for retrieval
                embedding_key = _generate_embedding_key(embedding)

                # Retrieve the raw ID using the hash key
                raw_id = self.embedding_to_raw_map.get(embedding_key)

                if raw_id is not None:
                    # Retrieve raw data file path using the raw ID
                    raw_data_path = self.raw_data_storage.get_rawdata(raw_id)
                    if raw_data_path:
                        try:
                            # Read the contents of the file
                            with open(raw_data_path, 'r') as file:
                                raw_data = file.read()
                            results.append(raw_data)
                            self.logger.debug(f"Retrieved context: {raw_data}.")
                        except Exception as e:
                            self.logger.error(f"Error reading raw data file {raw_data_path}: {str(e)}")
                            results.append(None)  # Handle file read error
                    else:
                        results.append(None)  # Handle missing file path
                else:
                    results.append(None)  # Handle missing raw ID

            self.logger.info(f"Retrieved {len(results)} raw data items from persistent memory.")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving items: {str(e)}")
            raise RuntimeError(f"Failed to retrieve items: {str(e)}")

    def delete(self, embedding):
        """
        Delete an embedding and its associated raw data.
        """
        try:
            # Remove the embedding from VectorDB
            tensor = torch.from_numpy(embedding)
            self.db.remove_tensor(tensor.clone())

            # Remove the embedding-to-raw mapping and raw data
            embedding_key = tuple(embedding.tolist())
            raw_id = self.embedding_to_raw_map.pop(embedding_key, None)
            if raw_id:
                self.raw_data_storage.delete_rawdata(raw_id)

            self.logger.info("Deleted embedding and its associated raw data.")
        except Exception as e:
            self.logger.error(f"Error deleting embedding: {str(e)}")
            raise RuntimeError(f"Failed to delete embedding: {str(e)}")

    def clean(self):
        """
        Clear all items in memory.
        """
        self.raw_data_storage.delete_all_data()
        self.logger.info("Memory cleared.")
