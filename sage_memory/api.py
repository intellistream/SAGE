from typing import TYPE_CHECKING
from sage_utils.embedding_model import apply_embedding_model
from sage_memory.memory_manager import MemoryManager
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from sage_core.api.env import BaseEnvironment

    
# TODO: 
# 1.在API层维护一个全局的MemoryManager实例
#   在用户调用get_memory时，首先会执行manager的检测函数get_manager，该函数检测manager是否存在，
#   如果不存在则创建一个新的MemoryManager实例，并将其存储在全局。
# 2.create_memory函数将转换为get_memory函数
#   检测完manager之后，展开config的配置创建collection并返回
#   在创建collection时，config = config["collection_name"]， 
#   随后展开config的配置，首先检查是不是VDB类型，if config["backend_type"] == "VDB"，是则直接创建该类型的collection，然后再插入数据
#   至于当前已有的一些remote相关操作，可以考虑保留

_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager

def get_memory(env:'BaseEnvironment', config, remote:bool = False):
    
    # config 示例，可注释
    collection_name = "vdb_test"
    if config is not None :
        collection_name = config.get("collection_name", "vdb_test")
    config = {
        "collection_name": collection_name ,
        "backend_type": "VDB",
        "embedding_model_name": "mockembedder",
        "dim": 128,
        "description": "VDB collection as Ray actor",
    }
    
    # 1.获取全局的manager示例
    manager = get_manager()
    # 2.判断所需memory类型
    if config.get("backend_type") == "VDB":
        collection = manager.get_collection(collection_name)
        if collection:
            # 如果已存在该collection，则直接返回
            return collection
        # 3.创建VDB类型的collection
        col = manager.create_collection(
            name=config["collection_name"],
            backend_type="VDB",
            # 4.加载embedding模型并嵌入
            embedding_model=apply_embedding_model(name=config["embedding_model_name"]),
            dim=config["dim"],
            description=config["description"],
            as_ray_actor=remote, 
            session_folder = CustomLogger.get_session_folder() if remote else None,
            env_name = env.name
        )
    
    else:    
        raise ValueError(f"Unsupported backend type: {config.get('backend_type')}")
    
    # 插入测试数据，可注释
    if(remote is False):
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
    else:
        col.add_metadata_field.remote("owner")
        col.add_metadata_field.remote("show_type")
        texts = [
            ("hello world", {"owner": "ruicheng", "show_type": "text"}),
            ("你好，世界", {"owner": "Jun", "show_type": "text"}),
            ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
        ]
        for text, metadata in texts:
            col.insert.remote(text, metadata)
        col.create_index.remote(index_name="vdb_index")
    return col

