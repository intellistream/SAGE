# File: sage/api/memory/memory_api.py

from sage.core.neuromem.memory_manager import NeuronMemManager
from sage.core.neuromem.memory_collection import MemoryCollection


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
    memory = MemoryCollection(memory_table_name, embedding_model, memory_table_backend)
    manager.register(memory_table_name, memory)
    return memory


def connect(manager: NeuronMemManager, *memory_names: str):
    """
    Connect to one or more registered memory collections by name.

    Args:
        *memory_names: one or more memory names previously registered.

    Returns:
        A composite object allowing unified memory access (e.g., for retrieval).
    """
    memory_list = [manager.get(name) for name in memory_names]

    class CompositeMemory:
        
        def retrieve(self, raw_data: str, retrieve_func=None):
            results = []
            for mem in memory_list:
                results.extend(mem.retrieve(raw_data, retrieve_func)) # type: ignore 
            return list(dict.fromkeys(results))

        def store(self, raw_data: str, write_func=None):
            for mem in memory_list:
                mem.store(raw_data, write_func) # type: ignore 

        def flush_kv_to_vdb(self, kv, vdb):
            """
            Transfer data from KV to VDB.
            """

            # Retrieve all KV data
            kv_data = kv.memory.retrieve(k=len(kv.memory.storage))
            if not kv_data:
                return

            # Convert to embeddings and store in VDB
            for item in kv_data:
                vdb.store(item)

            # Clear KV storage after transfer
            kv.clean()
    
    return CompositeMemory()

def retrieve_func():
    return None

def write_func():
    return None