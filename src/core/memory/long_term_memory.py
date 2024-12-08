import hashlib

import torch
from pycandy import VectorDB

from src.core.memory.base_memory import BaseMemory
from src.core.storage.local_raw_data_storage import LocalRawDataStorage, RAW_FILE


class LongTermMemory(BaseMemory):
    """
    Long-term memory layer that uses VectorDB for storage and retrieval.
    """

    def __init__(self, vector_dim, search_algorithm):
        super().__init__()
        self.db = VectorDB(vector_dim, search_algorithm)
        self.raw_data_storage = LocalRawDataStorage(
            RAW_FILE
        )
        self.embedding_to_raw_map = {}
        self.logger.info("Persistent memory initialized with VectorDB.")

    def _generate_embedding_key(self, embedding):
        """
        Generate a unique, consistent hash key for the embedding.
        """
        # Ensure the tensor is on the CPU and detached
        if embedding.device.type != 'cpu':
            embedding = embedding.cpu()
        embedding = embedding.detach()  # Ensure no gradient tracking

        # Convert tensor to bytes directly
        embedding_bytes = embedding.contiguous().view(-1).to(torch.uint8).numpy().tobytes()

        # Create a SHA256 hash
        return hashlib.sha256(embedding_bytes).hexdigest()

    def store(self, embedding, raw_data=None):
        """
        Store an embedding and its raw data.
        """
        if raw_data is None:
            raise ValueError("Raw data must be provided for persistent memory.")

        # Save the raw data and get its ID
        raw_id = self.raw_data_storage.add_text_as_rawdata(raw_data)

        # Generate a hash key for the embedding
        embedding_key = self._generate_embedding_key(embedding)

        # Insert the embedding into VectorDB

        self.db.insert_tensor(embedding.clone())

        # Map the embedding hash to the raw ID
        self.embedding_to_raw_map[embedding_key] = raw_id

        self.logger.info(f"Stored embedding with Raw ID: {raw_id}")
        return raw_id

    def retrieve(self, query, k=1, **kwargs):
        """
        Retrieve embeddings and their associated raw data.
        """
        try:
            # Query the database for nearest neighbors
            embeddings = self.db.query_nearest_tensors(query.clone(), k)

            # Map each embedding to its raw data
            results = []
            for embedding in embeddings:
                # Generate the same hash key for retrieval
                embedding_key = self._generate_embedding_key(embedding)

                # Retrieve the raw ID using the hash key
                raw_id = self.embedding_to_raw_map.get(embedding_key)

                if raw_id is not None:
                    # Retrieve raw data using the raw ID
                    raw_data = self.raw_data_storage.get_rawdata(raw_id)
                    results.append((embedding, raw_data))
                else:
                    results.append((embedding, None))  # Handle missing data

            self.logger.info(f"Retrieved {len(results)} items from persistent memory.")
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
