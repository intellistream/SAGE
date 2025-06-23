import time
import sage
import logging
import yaml
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder


# logging.basicConfig(level=logging.DEBUG)
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def memory_init():
    """初始化内存管理器并创建测试集合"""
    default_model = MockTextEmbedder(fixed_dim=128)
    manager = MemoryManager()
    col = manager.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=default_model,
        dim=128,
        description="test vdb collection",
        as_ray_actor=False,
    )
    col.add_metadata_field("owner")
    col.add_metadata_field("show_type")
    texts = [
        ("hello world", {"owner": "ruicheng", "show_type": "text"}),
        ("你好，世界", {"owner": "Jun", "show_type": "text"}),
        ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
    ]
    for text, metadata in texts:
        col.insert(text, metadata)
    col.create_index(index_name="vdb_index")
    config_for_qa["retriever"]["ltm_collection"] = col

if __name__ == '__main__':

    config_for_qa= load_config('./app/config_for_qa.yaml')
    memory_init()
    while(True):
        user_input = input("\n>>> ").strip()
        if user_input.lower() == "exit":
            logging.info("Exiting SAGE Interactive Console")
            print("Goodbye!")
            break
        sage.query.run_query(user_input,config_for_qa)



