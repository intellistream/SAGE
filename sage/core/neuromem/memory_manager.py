# file sage/core/neuromem/memory_manager.py
# python -m sage.core.neuromem.memory_manager

# TODO:
import os
import json
from typing import Dict, Optional, Any, List,Callable
import logging

from torch import embedding 

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO, # 设置日志级别为 INFO
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler() # 输出到控制台
                        # logging.FileHandler("manager.log") # 如果需要输出到文件，可以添加
                    ])
logger = logging.getLogger("Manager") 
from sage.core.neuromem.memory_collection import BaseMemoryCollection, VDBMemoryCollection

class Manager:
    """
    Manager class for creating, retrieving, deleting, and listing Collection instances.
    This version operates purely in-memory and does not handle persistence for Collection configurations.
    It assumes all Collection dependencies (like embedding models and storage engines)
    are handled by the Collection classes themselves or are provided as direct instances.
    """
    def __init__(self):
        # In-memory dictionary to store active Collection instances.
        self._collections: Dict[str, BaseMemoryCollection] = {} 
        logger.info("Manager: Initialized collection manager.")

    def create_collection(
        self,
        name: str,
        collection_type: str = "BaseMemoryCollection",
        embedding_model: Any = None, # Direct instance of the embedding model, passed to VDBMemoryCollection
        dim: Optional[int] = None,
        **extra_config_for_collection # Allows passing additional configuration to Collection constructors
    ) -> BaseMemoryCollection:
        """
        Creates a new Collection instance in memory.
        This version does not persist collection configurations.

        Args:
            name (str): The unique name for the new collection.
            collection_type (str): The type of collection to create (e.g., 'BaseMemoryCollection' or 'VDBMemoryCollection').
            embedding_model (Any, optional): The embedding model instance required by VDBMemoryCollection.
                                             Manager will pass this directly to the Collection.
            dim (int, optional): The dimension of the embeddings, required by VDBMemoryCollection.
            **extra_config_for_collection: Any additional keyword arguments to pass to the Collection's constructor.

        Returns:
            BaseMemoryCollection: The newly created Collection instance.

        Raises:
            ValueError: If a collection with the given name already exists, or if the collection type is unsupported,
                        or if required parameters for VDBMemoryCollection are missing.
            Exception: If any error occurs during the Collection instantiation.
        """
        if name in self._collections:
            logger.error(f"Collection '{name}' already exists in memory.")
            raise ValueError(f"Collection '{name}' already exists.")

        collection_instance = None
        try:
            if collection_type == "VDBMemoryCollection":
                if embedding_model is None or dim is None:
                    raise ValueError("For VDBMemoryCollection, 'embedding_model' instance and 'dim' are required.")
                # Manager directly passes the provided embedding_model instance to VDBMemoryCollection
                collection_instance = VDBMemoryCollection(name=name, embedding_model=embedding_model, dim=dim)
            elif collection_type == "BaseMemoryCollection":
                collection_instance = BaseMemoryCollection(name=name)
            else:
                raise ValueError(f"Unsupported collection type: {collection_type}")
        except Exception as e:
            logger.error(f"Error creating collection '{name}' of type '{collection_type}': {e}", exc_info=True)
            raise 

        self._collections[name] = collection_instance
        logger.info(f"Manager: Created collection '{name}' of type '{collection_type}' (in-memory only).")
        return collection_instance

    def get_collection(self, name: str) -> BaseMemoryCollection:
        """
        Retrieves an existing Collection instance from memory.

        Args:
            name (str): The name of the collection to retrieve.

        Returns:
            BaseMemoryCollection: The requested Collection instance.

        Raises:
            KeyError: If the collection with the given name is not found in memory.
        """
        if name not in self._collections:
            logger.error(f"Collection '{name}' not found in memory.")
            raise KeyError(f"Collection '{name}' not found.")
        logger.info(f"Manager: Retrieved collection '{name}'.")
        return self._collections[name]

    def delete_collection(self, name: str) -> bool:
        """
        Deletes a Collection instance from memory and triggers its internal cleanup.
        This version does not handle persistence deletion for collection configurations.

        Args:
            name (str): The name of the collection to delete.

        Returns:
            bool: True if the collection was successfully deleted.

        Raises:
            KeyError: If the collection with the given name is not found in memory.
            Exception: If the Collection's clean() method fails, indicating potential
                       issues with underlying data cleanup.
        """
        if name not in self._collections:
            logger.error(f"Attempted to delete non-existent collection '{name}'.")
            raise KeyError(f"Collection '{name}' not found.")

        collection_instance = self._collections[name]
        
        logger.info(f"Cleaning data for collection '{name}'...")
        try:
            # Call the Collection's clean method to clear its internal storage.
            # This method should handle clearing data in TextStorage, MetadataStorage, VectorStorage, etc.
            collection_instance.clean() 
            logger.info(f"Data cleaned for collection '{name}'.")
            print(f"Data cleaned for collection '{name}'.")
        except Exception as e:
            logger.error(f"Error cleaning data for collection '{name}': {e}. Proceeding with instance removal from Manager.", exc_info=True)
            # Re-raise the exception to indicate that the cleanup of underlying data failed,
            # even if the instance is removed from the Manager's memory.
            raise 

        del self._collections[name] 
        logger.info(f"Successfully deleted collection '{name}' from memory.")
        return True

    def list_collections(self) -> List[Dict]:
        """
        Lists basic information (name and type) for all currently managed Collection instances in memory.

        Returns:
            List[Dict]: A list of dictionaries, where each dictionary contains the 'name'
                        and 'type' (class name) of a managed collection.
        """
        logger.info("Listing all in-memory collection configurations.")
        return [{"name": name, "type": type(col).__name__} for name, col in self._collections.items()]



# --- Test Cases for Manager ---
from sage.core.neuromem_before.mem_test.memory_api_test_ray import default_model

# Re-configure logging for tests to capture output
# This ensures that test logs are also captured and displayed

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler()
                    ])
test_logger = logging.getLogger("TestManager")

def run_test(test_func: Callable, description: str):
    """Helper to run a test and print success/failure."""
    test_logger.info(f"\n--- Running Test: {description} ---")
    try:
        test_func()
        test_logger.info(f"--- Test Passed: {description} ---")
    except Exception as e:
        test_logger.error(f"--- Test FAILED: {description} --- Error: {e}", exc_info=True)

def test_create_base_collection():
    """Test creating a basic memory collection."""
    manager = Manager()
    col_name = "my_base_collection"
    collection = manager.create_collection(name=col_name, collection_type="BaseMemoryCollection")
    assert collection.name == col_name
    assert isinstance(collection, BaseMemoryCollection)
    assert len(manager.list_collections()) == 1
    assert manager.list_collections()[0]['name'] == col_name
    assert manager.list_collections()[0]['type'] == "BaseMemoryCollection"
    test_logger.info(f"Created BaseMemoryCollection '{col_name}' successfully.")

def test_create_vdb_collection():
    """Test creating a VDB memory collection."""
    manager = Manager()
    vdb_col_name = "my_vdb_collection"
    mock_embedding_model = default_model
    collection = manager.create_collection(
        name=vdb_col_name,
        collection_type="VDBMemoryCollection",
        embedding_model=mock_embedding_model,
        dim=128
    )
    assert collection.name == vdb_col_name
    assert isinstance(collection, VDBMemoryCollection)
    assert collection.embedding_model is mock_embedding_model
    assert collection.dim == 128
    assert len(manager.list_collections()) == 1
    assert manager.list_collections()[0]['name'] == vdb_col_name
    assert manager.list_collections()[0]['type'] == "VDBMemoryCollection"
    test_logger.info(f"Created VDBMemoryCollection '{vdb_col_name}' successfully.")

def test_create_duplicate_collection_fails():
    """Test that creating a collection with an existing name raises ValueError."""
    manager = Manager()
    col_name = "duplicate_test_collection"
    manager.create_collection(name=col_name, collection_type="BaseMemoryCollection")
    try:
        manager.create_collection(name=col_name, collection_type="BaseMemoryCollection")
        assert False, "ValueError was not raised for duplicate collection."
    except ValueError as e:
        test_logger.info(f"Caught expected error: {e}")
        assert str(e) == f"Collection '{col_name}' already exists."
    test_logger.info("Duplicate collection creation test passed.")

def test_get_existing_collection():
    """Test retrieving an existing collection."""
    manager = Manager()
    col_name = "get_test_collection"
    created_col = manager.create_collection(name=col_name, collection_type="BaseMemoryCollection")
    retrieved_col = manager.get_collection(name=col_name)
    assert retrieved_col is created_col # Should be the exact same instance in memory
    test_logger.info(f"Retrieved collection '{col_name}' successfully.")

def test_get_non_existent_collection_fails():
    """Test that retrieving a non-existent collection raises KeyError."""
    manager = Manager()
    try:
        manager.get_collection(name="non_existent_collection")
        assert False, "KeyError was not raised for non-existent collection."
    except KeyError as e:
        test_logger.info(f"Caught expected error: {e}")
        assert e.args[0] == "Collection 'non_existent_collection' not found."
    test_logger.info("Non-existent collection retrieval test passed.")

def test_delete_collection():
    """Test deleting an existing collection."""
    manager = Manager()
    col_name = "delete_test_collection"
    manager.create_collection(name=col_name, collection_type="BaseMemoryCollection")
    
    # Insert some data to ensure clean() is called
    col_instance = manager.get_collection(col_name)
    col_instance.add_metadata_field("source")
    col_instance.insert("test data for deletion", {"source": "test"})
    
    deleted = manager.delete_collection(name=col_name)
    assert deleted is True
    assert len(manager.list_collections()) == 0
    try:
        manager.get_collection(name=col_name)
        assert False, "Collection was not deleted from memory."
    except KeyError:
        test_logger.info(f"Collection '{col_name}' successfully deleted from memory.")
    test_logger.info("Collection deletion test passed.")

def test_delete_non_existent_collection_fails():
    """Test that deleting a non-existent collection raises KeyError."""
    manager = Manager()
    try:
        manager.delete_collection(name="non_existent_delete_collection")
        assert False, "KeyError was not raised for non-existent collection deletion."
    except KeyError as e:
        test_logger.info(f"Caught expected error: {e}")
        assert e.args[0] == "Collection 'non_existent_delete_collection' not found."
    test_logger.info("Non-existent collection deletion test passed.")

def test_list_collections():
    """Test listing multiple collections."""
    manager = Manager()
    manager.create_collection(name="col1", collection_type="BaseMemoryCollection")
    manager.create_collection(name="col2", collection_type="VDBMemoryCollection", embedding_model=default_model, dim=64)
    manager.create_collection(name="col3", collection_type="BaseMemoryCollection")
    
    collections_list = manager.list_collections()
    assert len(collections_list) == 3
    names = {c['name'] for c in collections_list}
    types = {c['type'] for c in collections_list}
    assert "col1" in names and "col2" in names and "col3" in names
    assert "BaseMemoryCollection" in types and "VDBMemoryCollection" in types
    test_logger.info(f"Listed {len(collections_list)} collections successfully.")

def test_clean_method_called_on_delete():
    """Verify that the clean method of the collection is called upon deletion."""
    manager = Manager()
    col_name = "clean_test_collection"
    col_instance = manager.create_collection(name=col_name, collection_type="BaseMemoryCollection")
    col_instance.add_metadata_field("tag")
    col_instance.insert("some text", {"tag": "temp"})
    
    # Redirect stdout to capture print statements from clean()
    import sys
    from io import StringIO
    old_stdout = sys.stdout
    redirected_output = StringIO()
    sys.stdout = redirected_output

    try:
        manager.delete_collection(col_name)
        output = redirected_output.getvalue()
        assert "Data cleaned" in output
        test_logger.info("Collection clean() method verified to be called.")
    finally:
        sys.stdout = old_stdout # Restore stdout
    

# --- Run all tests ---
if __name__ == "__main__":
    test_logger.info("Starting Manager Tests...")
    
    run_test(test_create_base_collection, "Create BaseMemoryCollection")
    run_test(test_create_vdb_collection, "Create VDBMemoryCollection")
    run_test(test_create_duplicate_collection_fails, "Create Duplicate Collection")
    run_test(test_get_existing_collection, "Get Existing Collection")
    run_test(test_get_non_existent_collection_fails, "Get Non-Existent Collection")
    run_test(test_delete_collection, "Delete Existing Collection")
    run_test(test_delete_non_existent_collection_fails, "Delete Non-Existent Collection")
    run_test(test_list_collections, "List Collections")
    run_test(test_clean_method_called_on_delete, "Verify clean() called on delete")
    
    test_logger.info("\nAll Manager Tests Completed.")