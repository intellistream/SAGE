import hashlib
import torch
from pycandy import VectorDB

from sage.core.neuromem.memory.base_memory import BaseMemory
from sage.core.neuromem.memory.raw.local_raw_data_storage import LocalRawDataStorage
from sage.utils.text_processing import process_session_text_to_embedding
from sage.utils.file_path import RAW_FILE_LTM


def _generate_embedding_key(embedding):
    """
    Generate a unique, consistent hash key for the embedding_model.
    """
    # Ensure the tensor is on the CPU and detached
    if embedding.device.type != 'cpu':
        embedding = embedding.cpu()
    embedding = embedding.detach()  # Ensure no gradient tracking

    # Convert tensor to bytes without changing its type
    embedding_bytes = embedding.contiguous().view(-1).numpy().tobytes()

    # Create a SHA256 hash
    return hashlib.sha256(embedding_bytes).hexdigest()


class LongTermMemory(BaseMemory):
    """
    Long-term memory layer that stores entire sessions in a VectorDB for retrieval based on similarity.
    """

    def __init__(self, vector_dim, search_algorithm):
        """
        Initialize the LongTermMemory with a VectorDB for session storage and retrieval.

        :param vector_dim: Dimensionality of the embeddings.
        :param search_algorithm: Search algorithm to use in VectorDB.
        """
        super().__init__()
        self.db = VectorDB(vector_dim, search_algorithm)
        self.raw_data_storage = LocalRawDataStorage(RAW_FILE_LTM)
        self.session_to_raw_map = {}

        self.logger.info("Long-term memory initialized with VectorDB for session storage.")

    def store(self, session_embedding, raw_data=None):
        """
        Store a session embedding_model and its corresponding raw session data.

        :param session_embedding: The aggregated embedding_model representing the session.
        :param raw_data: The raw session data (e.g., list of queries and answers).
        """
        if not raw_data:
            raise ValueError("Session data must be provided for long-term memory storage.")

        # Save the raw session data and get its ID
        raw_id = self.raw_data_storage.add_text_as_rawdata(str(raw_data))

        # Generate a unique key for the session embedding_model
        session_key = _generate_embedding_key(session_embedding)

        # Insert the session embedding_model into VectorDB
        self.db.insert_tensor(session_embedding.clone())

        # Map the session key to the raw session ID
        self.session_to_raw_map[session_key] = raw_id

        self.logger.info(f"Stored session with Raw ID: {raw_id}")
        return raw_id

    def retrieve(self, query_embedding, k=1, **kwargs):
        """
        Retrieve sessions most similar to the given query embedding_model.

        :param query_embedding: The embedding_model of the query.
        :param k: Number of similar sessions to retrieve.
        :return: A list of raw session data.
        """
        try:
            # Query the database for the nearest neighbors
            embeddings = self.db.query_nearest_tensors(query_embedding.clone(), k)

            # Retrieve the raw session data for the similar embeddings
            results = []
            for embedding in embeddings:
                # Generate a hash key for the embedding_model
                session_key = _generate_embedding_key(embedding)

                # Retrieve the raw ID using the hash key
                raw_id = self.session_to_raw_map.get(session_key)

                if raw_id is not None:
                    # Retrieve raw session data file path
                    raw_data_path = self.raw_data_storage.get_rawdata(raw_id)
                    if raw_data_path:
                        try:
                            with open(raw_data_path, 'r') as file:
                                raw_data = file.read()
                            results.append(raw_data)
                            self.logger.debug(f"Retrieved session: {raw_data}.")
                        except Exception as e:
                            self.logger.error(f"Error reading session data file {raw_data_path}: {str(e)}")
                            results.append(None)  # Handle file read error
                    else:
                        results.append(None)  # Handle missing file path
                else:
                    results.append(None)  # Handle missing raw ID

            self.logger.info(f"Retrieved {len(results)} similar sessions from long-term memory.")
            return results
        except Exception as e:
            self.logger.error(f"Error retrieving similar sessions: {str(e)}")
            raise RuntimeError(f"Failed to retrieve similar sessions: {str(e)}")

    def delete_session(self, session_embedding):
        """
        Delete a session and its associated embedding_model.

        :param session_data: The raw session data to delete.
        """
        try:
            # Generate a session key
            session_key = _generate_embedding_key(session_embedding)

            # Remove the embedding_model and raw data
            raw_id = self.session_to_raw_map.pop(session_key, None)
            if raw_id:
                self.raw_data_storage.delete_rawdata(raw_id)
                self.logger.info(f"Deleted session raw data with ID: {raw_id}")
            else:
                self.logger.warning(f"Session key not found for deletion: {session_key}")
        except Exception as e:
            self.logger.error(f"Error deleting session: {str(e)}")
            raise RuntimeError(f"Failed to delete session: {str(e)}")

    def clean(self):
        """
        Clear all session data and embeddings from long-term memory.
        """
        self.raw_data_storage.delete_all_data()
        self.session_to_raw_map.clear()
        self.logger.info("Cleared all sessions from long-term memory.")
