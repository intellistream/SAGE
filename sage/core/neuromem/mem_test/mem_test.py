from sage.api.memory.memory_api import create_table, connect, retrieve_func, write_func, init_default_manager, get_default_manager
import logging
# python -m sage.core.neuromem.mem_test.mem_test
def configure_logging(level=logging.INFO, log_file=None):
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file)) # type: ignore 

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
    
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

if __name__ == "__main__":

    configure_logging(level=logging.INFO)

    manager_test = init_default_manager()
    manager = get_default_manager()

    stm = manager.create_table("short_term_memory", default_model)
    ltm = manager.create_table("long_term_memory", default_model)
    dcm = manager.create_table("dynamic_contextual_memory", default_model)

    print("=" * 30)

    # STM-TEST
    stm.store("This is STM data")
    print("STM retrieval test(store): This is STM data")
    stm_retrieval_results = str(stm.retrieve())
    print("STM retrieval test:(retrieve): " + stm_retrieval_results)
    if stm_retrieval_results == "['This is STM data']":
        print("\033[92mSTM retrieval test pass!\033[0m")
    else:
        print("\033[91mSTM retrieval test error!\033[0m")
    print("=" * 30)

    # LTM-TEST
    ltm.store("This is LTM data")
    print("LTM retrieval test(store): This is LTM data")
    ltm_retrieval_results = str(ltm.retrieve("This is LTM data"))
    print("LTM retrieval test(retrieve): " + ltm_retrieval_results)
    if ltm_retrieval_results == "['This is LTM data']":
        print("\033[92mLTM retrieval test pass!\033[0m")
    else:
        print("\033[91mLTM retrieval test error!\033[0m")
    print("=" * 30)

    # DCM-TEST
    dcm.store("This is DCM data")
    print("DCM retrieval test(store): This is DCM data")
    dcm_retrieval_results = str(dcm.retrieve("This is DCM data"))
    print("DCM retrieval test(retrieve): " + dcm_retrieval_results)
    if dcm_retrieval_results == "['This is DCM data', '苹果', '香蕉']":
        print("\033[92mDCM retrieval test pass!\033[0m")
    else:
        print("\033[91mDCM retrieval test error!\033[0m")
    print("=" * 30)

    # CONNECT-TEST
    composite = manager.connect("short_term_memory", "long_term_memory")
    composite.store("This is Composite data.")
    composite_retrieval_results = str(composite.retrieve("This is composite data"))
    print("composite retrieval test: " + composite_retrieval_results)
    if composite_retrieval_results == "['This is Composite data.', 'This is LTM data']":
        print("\033[92mComposite retrieval test pass!\033[0m")
    else:
        print("\033[91mComposite retrieval test error!\033[0m")
    print("=" * 30)

    # CONNECT-FUNC-TEST
    import torch

    def test_write_func(raw_data, embedding, memory):
        embedding = torch.full((128,), 0.5)
        print("Custom store function called with embedding: [0.5,,,0.5] x 128")
        memory.store(raw_data, embedding)

    def test_retrieve_func(embedding, memory):
        embedding = torch.full((128,), 0.5)
        print("Custom retrieve function called with embedding: [0.5,,,0.5] x 128")
        return memory.retrieve(embedding, k=1)

    composite.store("This is a Storage & Retrieval Test.", write_func=test_write_func)

    composite_func_results = str(composite.retrieve("This is a Storage & Retrieval Test.", retrieve_func=test_retrieve_func))
    print("composite func results: " + composite_func_results)
    if composite_func_results == "['This is a Storage & Retrieval Test.']":
        print("\033[92mComposite func test pass!\033[0m")
    else:
        print("\033[91mComposite func test error!\033[0m")
    print("=" * 30)

    # CONNECT-FLUSH-TEST
    composite.flush_kv_to_vdb(stm, ltm)
    if len(stm.retrieve("test")) == 0 and len(ltm.retrieve("")) == 4:
        print("\033[92mComposite flush test pass!\033[0m")
    else:
        print("\033[91mComposite flush test error!\033[0m") 

    # MANAGER-TEST
    print(manager.list_collections())

    ltm.clean()
    dcm.clean()
      
