# file sage/core/neuromem/storage_engine/storage_engine_locked.py
# python sage/core/neuromem/storage_engine/storage_engine_locked.py

"""
Locked storage-engine implementations that extend your existing in‑memory
classes (`TextStorage`, `MetadataStorage`, `VectorStorage`).

Added capabilities
------------------
* **Persistent append** to disk with crash‑safe file locking (`fcntl`).
* **load()** to rebuild in‑memory cache from disk.
* **clear_cache()** to free RAM during `release()`.

File layout
-----------
<collection_dir>/
    text.jsonl          – one JSON per line {"id", "text"}
    meta.jsonl          – one JSON per line {"id", <fields…>}
    vec.npy             – float32 binary matrix (N×D)
    vec_ids.jsonl       – one JSON per line {"id"} (row alignment)

These classes can seamlessly replace the original ones in collections that
require persistence, while pure in‑memory collections can keep using the
base versions.
"""

from __future__ import annotations

import json
import os
import fcntl
from turtle import fd
from typing import Dict, Any
from pathlib import Path
import mmap

import numpy as np

from sage.core.neuromem.storage_engine.text_storage import TextStorage
from sage.core.neuromem.storage_engine.metadata_storage import MetadataStorage
from sage.core.neuromem.storage_engine.vector_storage import VectorStorage

# Locked text storage

class TextStorageLocked(TextStorage):
    def __init__(self, file_path: Path|str):
        super().__init__()
        self.file_path = Path(file_path)

    #------------persistence---------------

    def append(self, item_id: str, text: str):
        """
        Append text to the storage with file locking.
        使用文件锁定将文本追加到存储中。
        """
        line = json.dumps({"id": item_id, "text": text})
        self._atomic_append(line)
        # update in-memory cache via parent helper
        self.store(item_id, text)

    def load(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"Storage file {self.file_path} does not exist.")
        with self.file_path.open("r", encoding='utf-8') as f:
            for line in f:
                obj = json.loads(line)
                super().store(obj["id"], obj["text"])
            

    def clear_cache(self):
        """
        Clear the in-memory cache.
        清除内存缓存。
        """
        super().clear()

    #---------------locking helper---------------
    def _atomic_append(self, line: str):
        """
        Append a line to the file atomically with file locking.
        原子性地将一行追加到文件中，使用文件锁定。
        """
        with self.file_path.open("a",encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line+ "\n")
            f.flush();os.fsync((f.fileno()))
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# Locked metadata storage
class MetadataStorageLocked(MetadataStorage):
    def __init__(self, file_path: Path|str):
        super().__init__()
        self.file_path = Path(file_path)

    #------------persistence---------------

    def append(self, item_id: str, metadata: Dict[str, Any]):
        """
        Append metadata to the storage with file locking.
        使用文件锁定将元数据追加到存储中。
        """
        self.validate_fields(metadata)
        line = json.dumps({"id": item_id, **metadata})
        self._atomic_append(line)
        # update in-memory cache via parent helper
        self.store(item_id, metadata)

    def load(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"Storage file {self.file_path} does not exist.")
        with self.file_path.open("r", encoding='utf-8') as f:
            for line in f:
                obj = json.loads(line)
                _id = obj.pop("id", None)
                super().store(_id, obj)
    
    def clear_cache(self):
        """
        Clear the in-memory cache.
        清除内存缓存。
        """
        super().clear()

    #---------------locking helper---------------
    def _atomic_append(self, line: str):
        """
        Append a line to the file atomically with file locking.
        原子性地将一行追加到文件中，使用文件锁定。
        """
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("a",encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(line+ "\n")
            f.flush();os.fsync((f.fileno()))
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# Locked vector storage
"""
vec_path 对应的是 .npy 文件，存储的是实际向量矩阵

id_path 对应的是 .jsonl 文件，按行存的是向量 ID，跟 .npy 按行对齐
"""
class VectorStorageLocked(VectorStorage):
    def __init__(self, file_path: Path|str,id_path: Path|str,dim:int):
        super().__init__()
        self.vec_path = Path(file_path)
        self.id_path = Path(id_path)
        self.dim = dim
        self._id2row: Dict[str, int] = {}  # id -> row index mapping
        self._vec_mmap: np.memmap | None = None

    #------------persistence---------------
    def append(self,item_id:str,vec:np.ndarray):
        """
        Append a vector to the storage with file locking.
        使用文件锁定将向量追加到存储中。
        """
        if not isinstance(vec, np.ndarray):
            raise TypeError("vec must be a numpy ndarray")
        if vec.shape != (self.dim,):
            raise ValueError(f"vec must have shape ({self.dim},)")

        row_idx = self._append_id_file(item_id)
        self._append_vec_binary(vec)
        self._id2row[item_id] = row_idx
    # update in-memory cache via parent helper
        self.store(item_id, vec)

    
    def load(self):
        if not (self.vec_path.exists() and self.id_path.exists()):
            raise FileNotFoundError(f"Storage files {self.vec_path} or {self.id_path} do not exist.")
        with self.id_path.open("r", encoding="utf-8") as f:
            for row_idx, line in enumerate(f):
                obj = json.loads(line)
                item_id = obj["id"]
                self._id2row[item_id] = row_idx
        total = len(self._id2row)
        self._vec_mmap = np.memmap(self.vec_path, dtype="float32", mode="r", shape=(total, self.dim))
        # hydrate parent dict lazily (only ids) – vectors fetched on demand
        for item_id in self._id2row:
            super().store(item_id, None)  # placeholder

    def clear_cache(self): 
        """
        Clear the in-memory cache.
        清除内存缓存。
        """
        super().clear()
        self._id2row.clear()
        if self._vec_mmap is not None:
            self._vec_mmap = None      
    
    def get(self, item_id: str) -> np.ndarray | None:
        """
        Retrieve a vector by its ID.
        使用 ID 获取向量。
        """
        if item_id not in self._id2row:
            return None
        row_idx = self._id2row[item_id]
        if self._vec_mmap is None:
            raise RuntimeError("Storage not loaded. Call load() first.")
        return self._vec_mmap[row_idx]
    




    
#------------internal helpers---------------
    def _append_id_file(self, item_id: str) -> int:
        self.id_path.parent.mkdir(parents=True, exist_ok=True)
        with self.id_path.open("a+", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.seek(0)  # 移到开头以便读取行数
            row_idx = sum(1 for _ in f)  # count existing lines
            f.write(json.dumps({"id": item_id}) + "\n")
            f.flush(); os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return row_idx

    
    def _append_vec_binary(self, vec: np.ndarray):
        vec = vec.astype("float32", copy=False)  # 强制转换
        vec_bytes = vec.tobytes()
        append_size = len(vec_bytes)

        fd = os.open(self.vec_path, os.O_RDWR | os.O_CREAT)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            file_size = os.path.getsize(self.vec_path) if os.path.exists(self.vec_path) else 0
            new_size = file_size + append_size
            os.ftruncate(fd, new_size)
            mm = mmap.mmap(fd, new_size)
            mm[file_size:new_size] = vec_bytes  # now guaranteed to match
            mm.flush(); mm.close()
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
