# python -m sage.core.neuromem.mem_test.memory_api_test_ray


import ray
from ray import serve
import asyncio
import torch
from typing import Optional
from sage.api.memory.memory_service import MemoryManagerService
from transformers import AutoTokenizer, AutoModel

# 文本嵌入器 | Text Embedder
class TextEmbedder:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2', fixed_dim: int = 128):
        """初始化预训练模型和固定输出维度 | Initialize with pre-trained model and fixed dimension."""
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.fixed_dim = fixed_dim
        
    def encode(self, text: str, max_length: int = 512, stride: Optional[int] = None) -> torch.Tensor:
        """为文本生成固定维度嵌入 | Generate fixed-dimension embedding for text."""
        if not text.strip():
            return torch.zeros(self.fixed_dim)
        if stride is None or len(text.split()) <= max_length:
            return self._embed_single(text)
        return self._embed_with_sliding_window(text, max_length, stride)
    
    def _embed_single(self, text: str) -> torch.Tensor:
        """直接嵌入短文本 | Embed short text directly."""
        inputs = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
        return self._adjust_dimension(embedding)
    
    def _embed_with_sliding_window(self, text: str, max_length: int, stride: int) -> torch.Tensor:
        """使用滑动窗口嵌入长文本 | Embed long text with sliding window."""
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
            for window in inputs["input_ids"]:
                output = self.model(window.unsqueeze(0))
                embeddings.append(output.last_hidden_state.mean(dim=1).squeeze())
        return self._adjust_dimension(torch.stack(embeddings).mean(dim=0))
    
    def _adjust_dimension(self, embedding: torch.Tensor) -> torch.Tensor:
        """确保输出维度固定 | Ensure fixed output dimension."""
        if embedding.size(0) > self.fixed_dim:
            return embedding[:self.fixed_dim]
        elif embedding.size(0) < self.fixed_dim:
            padding = torch.zeros(self.fixed_dim - embedding.size(0), device=embedding.device)
            return torch.cat((embedding, padding))
        return embedding

# 默认嵌入模型 | Default embedding model
default_model = TextEmbedder()

async def test_memory_manager():
    """测试MemoryManagerService功能 | Test MemoryManagerService functionality."""

    # 初始化Ray和Serve | Initialize Ray and Serve
    ray.init(ignore_reinit_error=True)
    serve.shutdown()
    serve.start(detached=True)

    # 部署MemoryManagerService | Deploy MemoryManagerService
    app = MemoryManagerService.bind()
    serve.run(app, name="MemoryApp")
    manager_handle = serve.get_deployment_handle(deployment_name="MemoryManagerService", app_name="MemoryApp")

    print("=" * 30)

    # 创建表 | Create tables
    stm = await manager_handle.create_table.remote("short_term_memory", default_model)
    ltm = await manager_handle.create_table.remote("long_term_memory", default_model)
    dcm = await manager_handle.create_table.remote("dynamic_contextual_memory", default_model)
    # print(type(ltm))
    # test = await manager_handle.get_table.remote("long_term_memory")
    # print(type(test))
    # STM-TEST
    await stm.store.remote("This is STM data")
    print("STM retrieval test (store): This is STM data")
    stm_retrieval_results = str(ray.get(stm.retrieve.remote()))
    print("STM retrieval test (retrieve): " + stm_retrieval_results)
    if stm_retrieval_results == "['This is STM data']":
        print("\033[92mSTM retrieval test pass!\033[0m")
    else:
        print("\033[91mSTM retrieval test error!\033[0m")
    print("=" * 30)
    # print(str(ray.get(test.retrieve.remote("test"))))
    # LTM-TEST
    await ltm.store.remote("This is LTM data")
    print("LTM retrieval test (store): This is LTM data")
    ltm_retrieval_results = str(ray.get(ltm.retrieve.remote("This is LTM data")))
    print("LTM retrieval test (retrieve): " + ltm_retrieval_results)
    if ltm_retrieval_results == "['This is LTM data']":
        print("\033[92mLTM retrieval test pass!\033[0m")
    else:
        print("\033[91mLTM retrieval test error!\033[0m")
    print("=" * 30)

    # DCM-TEST
    await dcm.store.remote("This is DCM data")
    print("DCM retrieval test (store): This is DCM data")
    dcm_retrieval_results = str(ray.get(dcm.retrieve.remote("This is DCM data")))
    print("DCM retrieval test (retrieve): " + dcm_retrieval_results)
    if dcm_retrieval_results == "['This is DCM data', '苹果', '香蕉']":
        print("\033[92mDCM retrieval test pass!\033[0m")
    else:
        print("\033[91mDCM retrieval test error!\033[0m")
    print("=" * 30)

    # CONNECT-TEST
    composite = await manager_handle.connect.remote("short_term_memory", "long_term_memory")
    await composite.store.remote("This is Composite data")
    composite_retrieval_results = str(ray.get(composite.retrieve.remote("This is Composite data")))
    print("Composite retrieval test: " + composite_retrieval_results)
    if composite_retrieval_results == "['This is Composite data', 'This is LTM data']":
        print("\033[92mComposite retrieval test pass!\033[0m")
    else:
        print("\033[91mComposite retrieval test error!\033[0m")
    print("=" * 30)

    # CONNECT-FUNC-TEST
    def test_write_func(raw_data, embedding, memory):
        embedding = torch.full((128,), 0.5)
        print("Custom store function called with embedding: [0.5,,,0.5] x 128")
        # 假设 LongTermMemory 有 store 方法
        memory.store(raw_data, embedding)
        return None

    def test_retrieve_func(embedding, memory):
        embedding = torch.full((128,), 0.5)
        print("Custom retrieve function called with embedding: [0.5,,,0.5] x 128")
        # 假设 LongTermMemory 有 retrieve 方法
        return memory.retrieve(embedding, k=1)

    await composite.store.remote("This is a Storage & Retrieval Test", write_func=test_write_func)
    composite_func_results = str(ray.get(composite.retrieve.remote("This is a Storage & Retrieval Test", retrieve_func=test_retrieve_func)))
    print("Composite func results: " + composite_func_results)
    if composite_func_results == "['This is a Storage & Retrieval Test']":
        print("\033[92mComposite func test pass!\033[0m")
    else:
        print("\033[91mComposite func test error!\033[0m")
    print("=" * 30)

    # CONNECT-FLUSH-TEST
    # await composite.flush_kv_to_vdb.remote(stm, ltm)
    # stm_flush = ray.get(stm.retrieve.remote("test"))
    # ltm_flush = ray.get(ltm.retrieve.remote(""))
    # print(f"STM flush result: {stm_flush}, length: {len(stm_flush)}")
    # print(f"LTM flush result: {ltm_flush}, length: {len(ltm_flush)}")
    # if len(stm_flush) == 0 and len(ltm_flush) == 4:
    #     print("\033[92mComposite flush test pass!\033[0m")
    # else:
    #     print("\033[91mComposite flush test error!\033[0m")
    # print("=" * 30)

    # MANAGER-TEST
    collections = await manager_handle.list_collections.remote()
    print("Manager collections:", collections)

    # 清理表 | Clean tables
    await ltm.clean.remote()
    await dcm.clean.remote()

    # 清理Serve | Clean up Serve
    serve.shutdown()

if __name__ == "__main__":
    asyncio.run(test_memory_manager())