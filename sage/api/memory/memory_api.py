# File: sage/api/memory/memory_api.py

from sage.core.neuromem.memory_manager import NeuronMemManager
from sage.core.neuromem.memory_collection import MemoryCollection

# Global variable to store the default manager instance
# 模块全局变量，存储默认管理器
_default_manager = None

def init_default_manager() -> NeuronMemManager:
    """
    Initialize the global default manager
    初始化全局默认管理器
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = NeuronMemManager()
    return _default_manager

def get_default_manager() -> NeuronMemManager:
    """
    Get the global default manager (must be initialized first)
    获取全局默认管理器（如果没有则抛出异常，需要先初始化）
    
    Raises:
        RuntimeError: If default manager is not initialized
        运行时错误：如果默认管理器未初始化
    """
    if _default_manager is None:
        raise RuntimeError("Default manager not initialized, please call init_default_manager() first")
    return _default_manager

# TODO delete test model
from transformers import AutoTokenizer, AutoModel
import torch
from typing import Optional
import logging

class TextEmbedder:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2', fixed_dim: int = 128):
        """Initialize with a pre-trained model and fixed output dimension."""
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.fixed_dim = fixed_dim
        
    def encode(self, text: str, max_length: int = 512, stride: Optional[int] = None) -> torch.Tensor:
        """
        Generate fixed-dimension embedding for text.
        Uses sliding window approach for long texts if stride is specified.
        """
        if not text.strip():
            return torch.zeros(self.fixed_dim)
            
        if stride is None or len(text.split()) <= max_length:
            return self._embed_single(text)
        return self._embed_with_sliding_window(text, max_length, stride)
    
    def _embed_single(self, text: str) -> torch.Tensor:
        """Embed short text directly."""
        inputs = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
        return self._adjust_dimension(embedding)
    
    def _embed_with_sliding_window(self, text: str, max_length: int, stride: int) -> torch.Tensor:
        """Embed long text using sliding window approach."""
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            stride=stride,
            return_overflowing_tokens=True,
            padding="max_length",
            return_tensors="pt"
        )
        
        embeddings = []
        with torch.no_grad():
            for window in inputs["input_ids"]: # type: ignore 
                output = self.model(window.unsqueeze(0))
                embeddings.append(output.last_hidden_state.mean(dim=1).squeeze())
                
        return self._adjust_dimension(torch.stack(embeddings).mean(dim=0))
    
    def _adjust_dimension(self, embedding: torch.Tensor) -> torch.Tensor:
        """Ensure output has fixed dimension (truncate or pad)."""
        if embedding.size(0) > self.fixed_dim:
            return embedding[:self.fixed_dim]
        elif embedding.size(0) < self.fixed_dim:
            padding = torch.zeros(self.fixed_dim - embedding.size(0), device=embedding.device)
            return torch.cat((embedding, padding))
        return embedding

default_model = TextEmbedder()

def create_table(
    memory_table_name: str
    ,manager: NeuronMemManager
    , embedding_model = default_model
    , memory_table_backend: str | None = None
    ) -> MemoryCollection:
    """
    Create a new memory table/collection and register it with the manager.
    创建一个新的记忆表/集合并将其注册到管理器
    
    Args:
        memory_table_name: Name of the memory table to create
                          要创建的记忆表名称
        manager: Memory manager instance that handles registration
                 处理注册的内存管理器实例
        embedding_model: Model used for embedding generation (defaults to default_model)
                        用于生成嵌入向量的模型(默认为default_model)
        memory_table_backend: Optional backend for the memory table
                             记忆表的可选后端
                             
    Returns:
        The newly created MemoryCollection instance
        新创建的MemoryCollection实例
    """
    memory = MemoryCollection(memory_table_name, embedding_model, memory_table_backend)
    manager.register(memory_table_name, memory)
    return memory


def connect(manager: NeuronMemManager, *memory_names: str):
    """
    Connect to one or more registered memory collections by name.
    按名称连接到一个或多个已注册的记忆集合
    
    Args:
        *memory_names: one or more memory names previously registered.
                      一个或多个先前注册的记忆名称
                      
    Returns:
        A composite object allowing unified memory access (e.g., for retrieval).
        一个复合对象，允许统一的记忆访问(例如用于检索)
    """
    memory_list = [manager.get(name) for name in memory_names]

    class CompositeMemory:
        """
        Composite memory class that combines multiple memory collections
        组合多个记忆集合的复合记忆类
        """
        
        def retrieve(self, raw_data: str, retrieve_func=None):
            """
            Retrieve data from all connected memory collections
            从所有连接的记忆集合中检索数据
            
            Args:
                raw_data: Input data to retrieve matches for
                          用于检索匹配项的输入数据
                retrieve_func: Optional custom retrieval function
                              可选的自定义检索函数
                              
            Returns:
                List of unique results from all memory collections
                来自所有记忆集合的唯一结果列表
            """
            results = []
            for mem in memory_list:
                results.extend(mem.retrieve(raw_data, retrieve_func)) # type: ignore 
            return list(dict.fromkeys(results))

        def store(self, raw_data: str, write_func=None):
            """
            Store data to all connected memory collections
            将数据存储到所有连接的记忆集合中
            
            Args:
                raw_data: Data to be stored
                          要存储的数据
                write_func: Optional custom write function
                            可选的自定义写入函数
            """
            for mem in memory_list:
                mem.store(raw_data, write_func) # type: ignore 

        def flush_kv_to_vdb(self, kv, vdb):
            """
            Transfer data from KV to VDB.
            将数据从KV传输到VDB
            
            Args:
                kv: Key-Value store instance
                    Key-Value存储实例
                vdb: Vector database instance
                     向量数据库实例
            """
            # Retrieve all KV data
            # 检索所有KV数据
            kv_data = kv.memory.retrieve(k=len(kv.memory.storage))
            if not kv_data:
                return

            # Convert to embeddings and store in VDB
            # 转换为嵌入向量并存储到VDB中
            for item in kv_data:
                vdb.store(item)

            # Clear KV storage after transfer
            # 传输后清除KV存储
            kv.clean()
    
    return CompositeMemory()

def retrieve_func():
    return None

def write_func():
    return None

def get_default_manager():
    return None