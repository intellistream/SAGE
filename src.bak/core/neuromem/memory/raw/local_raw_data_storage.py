# import os
# import json
# import threading
#
# from sage.utils.file_path import RAW_FILE_DCM
#
#
# # Utility for file and directory operations
# class FileManager:
#     @staticmethod
#     def create_directory_if_not_exists(directory_path):
#         if not os.path.exists(directory_path):
#             os.makedirs(directory_path)
#
#     @staticmethod
#     def delete_file(file_path):
#         if os.path.exists(file_path):
#             os.remove(file_path)
#
#     @staticmethod
#     def delete_directory(directory_path):
#         if os.path.exists(directory_path):
#             for file_name in os.listdir(directory_path):
#                 file_path = os.path.join(directory_path, file_name)
#                 os.remove(file_path)
#             os.rmdir(directory_path)
#
#     @staticmethod
#     def read_json(file_path):
#         with open(file_path, "r") as f:
#             return json.load(f)
#
#     @staticmethod
#     def write_json(file_path, data):
#         os.makedirs(os.path.dirname(file_path), exist_ok=True)
#         with open(file_path, "w") as f:
#             json.dump(data, f, indent=4)
#
# # Storage manager for metadata
# class MetadataManager:
#     def __init__(self, storage_file):
#         self.storage_file = storage_file
#         self.data = {}
#         self.next_id = 0
#
#     def load_metadata(self):
#         if os.path.exists(self.storage_file):
#             storage = FileManager.read_json(self.storage_file)
#             self.data = storage.get("data", {})
#             self.next_id = storage.get("next_id", 1)
#
#     def save_metadata(self):
#         FileManager.write_json(self.storage_file, {
#             "data": self.data,
#             "next_id": self.next_id
#         })
#
# # Main class for raw data storage
# class LocalRawDataStorage:
#     def __init__(self, storage_file_path):
#         self.metadata_manager = MetadataManager(storage_file_path)
#         self.data_dir = os.path.splitext(storage_file_path)[0] + "_data"
#         self.lock = threading.Lock()
#
#         FileManager.create_directory_if_not_exists(self.data_dir)
#         self.metadata_manager.load_metadata()
#
#     def add_text_as_rawdata(self, text):
#         with self.lock:
#             raw_id = self.metadata_manager.next_id
#             self.metadata_manager.next_id += 1
#
#         file_name = f"raw_{raw_id}.txt"
#         file_path = os.path.join(self.data_dir, file_name)
#
#         try:
#             with open(file_path, "w") as f:
#                 f.write(text)
#             with self.lock:
#                 self.metadata_manager.data[raw_id] = file_path
#                 self.metadata_manager.save_metadata()
#             return raw_id
#         except Exception as e:
#             print(f"Error saving text as RawData: {e}")
#             return None
#
#     def get_rawdata(self, raw_id):
#         with self.lock:
#             return self.metadata_manager.data.get(raw_id, None)
#
#     def delete_rawdata(self, raw_id):
#         with self.lock:
#             file_path = self.metadata_manager.data.get(raw_id)
#             if file_path:
#                 try:
#                     FileManager.delete_file(file_path)
#                     print(f"Deleted file for RawID {raw_id}: {file_path}")
#                     del self.metadata_manager.data[raw_id]
#                     self.metadata_manager.save_metadata()
#                     return True
#                 except Exception as e:
#                     print(f"Error deleting file for RawID {raw_id}: {e}")
#                     return False
#             else:
#                 print(f"RawID {raw_id} not found.")
#                 return False
#
#     def delete_all_data(self):
#         with self.lock:
#             try:
#                 FileManager.delete_directory(self.data_dir)
#                 print(f"Deleted data directory: {self.data_dir}")
#                 self.metadata_manager.data.clear()
#                 self.metadata_manager.next_id = 0
#                 self.metadata_manager.save_metadata()
#                 return True
#             except Exception as e:
#                 print(f"Error deleting all data: {e}")
#                 return False
#
#     def display_raw_data(self):
#         print(self.metadata_manager.data)
#
# # Interactive console for user operations
# class ConsoleInterface:
#     def __init__(self, storage):
#         self.storage = storage
#
#     def run(self):
#         while True:
#             print("\nLocalRawDataStorage Interactive Console")
#             print("1. Add Text Data")
#             print("2. Get RawData by ID")
#             print("3. Delete RawData by ID")
#             print("4. Delete All Data")
#             print("5. Exit")
#             choice = input("\nEnter your choice: ")
#
#             if choice == "1":
#                 text = input("Enter text data to add: ")
#                 self.storage.add_text_as_rawdata(text)
#             elif choice == "2":
#                 raw_id = int(input("Enter RawData ID: "))
#                 file_path = self.storage.get_rawdata(raw_id)
#                 if file_path:
#                     print(f"RawData found at: {file_path}")
#                 else:
#                     print(f"RawData with ID {raw_id} not found.")
#             elif choice == "3":
#                 raw_id = int(input("Enter RawData ID to delete: "))
#                 success = self.storage.delete_rawdata(raw_id)
#                 if success:
#                     print(f"RawData with ID {raw_id} deleted successfully.")
#             elif choice == "4":
#                 confirm = input("Are you sure you want to delete all data? (y/n): ")
#                 if confirm.lower() == "y":
#                     success = self.storage.delete_all_data()
#                     if success:
#                         print("All data deleted successfully.")
#                 else:
#                     print("Operation cancelled.")
#             elif choice == "5":
#                 break
#             else:
#                 print("Invalid choice. Please try again.")
#
# if __name__ == "__main__":
#     storage = LocalRawDataStorage(storage_file_path=RAW_FILE_DCM)
#     console = ConsoleInterface(storage)
#     console.run()
