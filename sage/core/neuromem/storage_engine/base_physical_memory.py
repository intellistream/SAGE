from abc import ABC, abstractmethod
import logging
import json
import os
import uuid
import numpy as np
import threading
from typing import Dict, List, Optional, Any

class BasePhysicalMemory(ABC):
		
		def __init__(self):
			self.logger = logging.getLogger(self.__class__.__name__)

		async def initialize(self):
				"""
				Initialize the storage.
				"""
				pass

		async def finalize(self):
				"""
				Finalize the storage (e.g., cleanup, close connections, etc.).
				"""
				pass

# VectorStorage STOREAGE，向量数据存储
class BaseVectorPhysicalMemory(BasePhysicalMemory, ABC):

		@abstractmethod
		def store(self, raw_data, embedding):
				"""
				Store the raw data and embedding into the storage system.
				"""

		@abstractmethod
		def retrieve(self, embedding):
				"""
				Query the vector storage and retrieve top_k results.
				"""

		@abstractmethod
		def delete(self, raw_data, embedding):
				"""
				Delete the specified entity from the storage.
				"""

# KeyValueStorage，KeyValue数据存储
class BaseKVPhysicalMemory(BasePhysicalMemory, ABC):
		def __init__(self):
			self.KVnum = 0

# GraphStorage，图数据存储
class BaseGraphPhysicalMemory(BasePhysicalMemory, ABC):
		def __init__(self):
			self.KVnum = 0	

# DocStorage，文档数据存储
class BaseDocPhysicalMemory(BasePhysicalMemory, ABC):
		def __init__(self):
			self.KVnum = 0

# RawData，原始数据管理
# class TextStorageLayer:
#     """A class to manage local storage of raw text data with metadata tracking."""
    
#     def __init__(self, storage_file_path: str):
#         """
#         Initialize the storage system.
#         """
#         self.storage_file = storage_file_path
#         self.data_dir = os.path.splitext(storage_file_path)[0] + "_data"
#         self.lock = threading.Lock()
        
#         # Initialize metadata
#         self._data: Dict[int, str] = {}  # Maps raw_id to file_path
#         self._next_id = 0
        
#         # Create directories and load existing data
#         self._initialize_storage()

#     def _initialize_storage(self) -> None:
#         """Create necessary directories and load existing metadata."""
#         os.makedirs(self.data_dir, exist_ok=True)
        
#         if os.path.exists(self.storage_file):
#             try:
#                 with open(self.storage_file, "r") as f:
#                     storage = json.load(f)
#                 self._data = storage.get("data", {})
#                 self._next_id = storage.get("next_id", 0)
#             except Exception as e:
#                 print(f"Error loading metadata: {e}. Starting with fresh storage.")

#     def _save_metadata(self) -> None:
#         """Save current metadata to the storage file."""
#         os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
#         with open(self.storage_file, "w") as f:
#             json.dump({
#                 "data": self._data,
#                 "next_id": self._next_id
#             }, f, indent=4)

#     def add_text(self, text: str) -> Optional[int]:
#         """
#         Add text as raw data to storage.
#         """
#         with self.lock:
#             raw_id = self._next_id
#             self._next_id += 1

#         file_name = f"raw_{raw_id}.txt"
#         file_path = os.path.join(self.data_dir, file_name)

#         try:
#             with open(file_path, "w") as f:
#                 f.write(text)
            
#             with self.lock:
#                 self._data[raw_id] = file_path
#                 self._save_metadata()
            
#             return raw_id
#         except Exception as e:
#             print(f"Error saving text as RawData: {e}")
#             return None

#     def get_text_path(self, raw_id: int) -> Optional[str]:
#         """
#         Get the file path for a given raw_id.
#         """
#         with self.lock:
#             return self._data.get(raw_id)

#     def get_text(self, raw_id: int) -> Optional[str]:
#         """
#         Get the content of a raw data file.
#         """
#         file_path = self.get_text_path(raw_id)
#         if file_path and os.path.exists(file_path):
#             try:
#                 with open(file_path, "r") as f:
#                     return f.read()
#             except Exception as e:
#                 print(f"Error reading file for RawID {raw_id}: {e}")
#         return None

#     def delete_text(self, raw_id: int) -> bool:
#         """
#         Delete a raw data entry and its associated file.
#         """
#         with self.lock:
#             file_path = self._data.get(raw_id)
#             if not file_path:
#                 print(f"RawID {raw_id} not found.")
#                 return False

#             try:
#                 if os.path.exists(file_path):
#                     os.remove(file_path)
#                 del self._data[raw_id]
#                 self._save_metadata()
#                 return True
#             except Exception as e:
#                 print(f"Error deleting file for RawID {raw_id}: {e}")
#                 return False

#     def delete_all_data(self) -> bool:
#         """
#         Delete all stored data and reset the storage.
#         """
#         with self.lock:
#             try:
#                 # Delete all files in data directory
#                 for filename in os.listdir(self.data_dir):
#                     file_path = os.path.join(self.data_dir, filename)
#                     try:
#                         if os.path.isfile(file_path):
#                             os.unlink(file_path)
#                     except Exception as e:
#                         print(f"Error deleting file {file_path}: {e}")
                
#                 # Reset metadata
#                 self._data.clear()
#                 self._next_id = 0
#                 self._save_metadata()
#                 return True
#             except Exception as e:
#                 print(f"Error deleting all data: {e}")
#                 return False

#     def display_metadata(self) -> None:
#         """Print the current metadata information."""
#         with self.lock:
#             print("Metadata:")
#             print(f"Next ID: {self._next_id}")
#             print("Stored items:")
#             for raw_id, path in self._data.items():
#                 print(f"  {raw_id}: {path}")
class TextStorageLayer:
    """A class to manage local storage of raw text data with metadata tracking."""
    
    def __init__(self, base_dir: str = "./data/raw_docs"):
        """
        Initialize the storage system with a unique directory.
        """
        self.unique_id = str(uuid.uuid4())  # Generate a unique identifier
        self.storage_root = os.path.join(base_dir, self.unique_id)
        self.data_dir = os.path.join(self.storage_root, "data")
        self.storage_file = os.path.join(self.storage_root, "metadata.json")
        self.lock = threading.Lock()
        
        # Initialize metadata
        self._data: Dict[int, str] = {}  # Maps raw_id to file_path
        self._next_id = 0
        
        # Create directories and load existing data
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Create necessary directories and load existing metadata."""
        try:
            os.makedirs(self.storage_root, exist_ok=True)
            os.makedirs(self.data_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creating storage directories: {e}")
        
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    storage = json.load(f)
                self._data = storage.get("data", {})
                self._next_id = storage.get("next_id", 0)
            except Exception as e:
                print(f"Error loading metadata: {e}. Starting with fresh storage.")

    def _save_metadata(self) -> None:
        """Save current metadata to the storage file."""
        os.makedirs(self.storage_root, exist_ok=True)
        with open(self.storage_file, "w") as f:
            json.dump({
                "data": self._data,
                "next_id": self._next_id
            }, f, indent=4)

    def add_text(self, text: str) -> Optional[int]:
        """
        Add text as raw data to storage.
        """
        with self.lock:
            raw_id = self._next_id
            self._next_id += 1

        file_name = f"raw_{raw_id}.txt"
        file_path = os.path.join(self.data_dir, file_name)

        try:
            # Ensure the data directory exists before writing
            os.makedirs(self.data_dir, exist_ok=True)
            
            with open(file_path, "w") as f:
                f.write(text)
            
            with self.lock:
                self._data[raw_id] = file_path
                self._save_metadata()
            
            return raw_id
        except Exception as e:
            print(f"Error saving text as RawData: {e}")
            return None

    def get_text_path(self, raw_id: int) -> Optional[str]:
        """
        Get the file path for a given raw_id.
        """
        with self.lock:
            return self._data.get(raw_id)

    def get_text(self, raw_id: int) -> Optional[str]:
        """
        Get the content of a raw data file.
        """
        file_path = self.get_text_path(raw_id)
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading file for RawID {raw_id}: {e}")
        return None

    def delete_text(self, raw_id: int) -> bool:
        """
        Delete a raw data entry and its associated file.
        """
        with self.lock:
            file_path = self._data.get(raw_id)
            if not file_path:
                print(f"RawID {raw_id} not found.")
                return False

            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                del self._data[raw_id]
                self._save_metadata()
                return True
            except Exception as e:
                print(f"Error deleting file for RawID {raw_id}: {e}")
                return False

    def delete_all_data(self) -> bool:
        """
        Delete all stored data and reset the storage.
        """
        with self.lock:
            try:
                if os.path.exists(self.storage_root):
                    import shutil
                    shutil.rmtree(self.storage_root)  # Delete the entire directory
                return True
            except Exception as e:
                print(f"Error deleting all data: {e}")
                return False

    def display_metadata(self) -> None:
        """Print the current metadata information."""
        with self.lock:
            print("Metadata:")
            print(f"Unique ID: {self.unique_id}")
            print(f"Next ID: {self._next_id}")
            print("Stored items:")
            for raw_id, path in self._data.items():
                print(f"  {raw_id}: {path}")
