import os
import json
import threading

class LocalRawDataStorage:
    def __init__(self, storage_file="/home/candy/CANDY/apps/Python/RawData/raw_data.json", data_dir="/home/candy/CANDY/apps/Python/RawData/raw_data_files"):
        self.storage_file = storage_file
        self.data_dir = data_dir
        self.data = {}
        self.next_id = 0
        self.lock = threading.Lock()  # 锁对象

        # 确保数据文件目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        if os.path.exists(self.storage_file):
            self._load_storage()
        else:
            print(f"Storage file {self.storage_file} not found. Creating a new one.")
            self._save_storage()

    def _load_storage(self):
        """从存储文件中加载数据"""
        with open(self.storage_file, "r") as f:
            storage = json.load(f)
            self.data = storage.get("data", {})
            self.next_id = storage.get("next_id", 1)

    def _save_storage(self):
        """将当前数据保存到存储文件"""
        try:
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            with open(self.storage_file, "w") as f:
                json.dump({"data": self.data, "next_id": self.next_id}, f, indent=4)
            print(f"Data saved successfully to {self.storage_file}")
        except Exception as e:
            print(f"Error saving storage file: {e}")

    def add_text_as_rawdata(self, text):
        """
        将用户输入的文本保存为文件，并注册为 RawData。
        Args:
            text (str): 用户输入的文本
        Returns:
            raw_id (int): 分配的 RawID
        """
        with self.lock:  # 确保分配 ID 和写操作线程安全
            raw_id = self.next_id
            self.next_id += 1

        file_name = f"raw_{raw_id}.txt"
        file_path = os.path.join(self.data_dir, file_name)

        try:
            # 保存文本到文件
            with open(file_path, "w") as f:
                f.write(text)

            # 更新存储数据
            with self.lock:
                self.data[raw_id] = file_path
                self._save_storage()
            return raw_id
        except Exception as e:
            print(f"Error saving text as RawData: {e}")
            return None

    def get_rawdata(self, raw_id):
        """根据 RawID 获取对应文件路径"""
        with self.lock:  # 确保读取操作线程安全
            return self.data.get(raw_id, None)

    def delete_rawdata(self, raw_id):
        """
        删除指定 RawID 的文件及其记录
        Args:
            raw_id (int): 要删除的 RawID
        Returns:
            bool: 删除成功返回 True，失败返回 False
        """
        with self.lock:
            file_path = self.data.get(raw_id)
            if file_path:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Deleted file for RawID {raw_id}: {file_path}")
                    del self.data[raw_id]
                    self._save_storage()
                    return True
                except Exception as e:
                    print(f"Error deleting file for RawID {raw_id}: {e}")
                    return False
            else:
                print(f"RawID {raw_id} not found.")
                return False

    def delete_all_data(self):
        """
        删除所有数据文件并清空存储记录
        Returns:
            bool: 删除成功返回 True，失败返回 False
        """
        with self.lock:
            try:
                # 删除数据目录中的所有文件
                for file_name in os.listdir(self.data_dir):
                    file_path = os.path.join(self.data_dir, file_name)
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")

                # 清空数据记录
                self.data.clear()
                self.next_id = 0

                # 删除数据目录
                os.rmdir(self.data_dir)
                print(f"Deleted data directory: {self.data_dir}")

                # 保存清空后的状态
                self._save_storage()
                return True
            except Exception as e:
                print(f"Error deleting all data: {e}")
                return False
    def displayRawData(self):
        print(self.data)

if __name__ == "__main__":
    storage = LocalRawDataStorage()
    while True:
        print("\nLocalRawDataStorage Interactive Console")
        print("1. Add Text Data")
        print("2. Get RawData by ID")
        print("3. Delete RawData by ID")
        print("4. Delete All Data")
        print("5. Exit")
        choice = input("\nEnter your choice: ")

        if choice == "1":
            text = input("Enter text data to add: ")
            storage.add_text_as_rawdata(text)
        elif choice == "2":
            raw_id = int(input("Enter RawData ID: "))
            file_path = storage.get_rawdata(raw_id)
            if file_path:
                print(f"RawData found at: {file_path}")
            else:
                print(f"RawData with ID {raw_id} not found.")
        elif choice == "3":
            raw_id = int(input("Enter RawData ID to delete: "))
            success = storage.delete_rawdata(raw_id)
            if success:
                print(f"RawData with ID {raw_id} deleted successfully.")
        elif choice == "4":
            confirm = input("Are you sure you want to delete all data? (y/n): ")
            if confirm.lower() == "y":
                success = storage.delete_all_data()
                if success:
                    print("All data deleted successfully.")
            else:
                print("Operation cancelled.")
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")