from typing import Optional, TYPE_CHECKING
from sage_utils.embedding_methods.embedding_model import apply_embedding_model
from sage.service.memory.memory_manager import MemoryManager
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    pass


_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager

def get_memory(config = None, remote:bool = False, env_name: Optional[str] = None):
    # 1.获取全局的manager示例
    manager = get_manager()
    
    if config is not None and not (isinstance(config, dict) and config.keys() == {"collection_name"}):
        collection = manager.get_collection(config.get("collection_name"))
        if collection:
            # 如果已存在该collection，则直接返回
            return collection
        
        
        # 这里给个config的示例
        # VDB类型的collection配置示例
        # config = {
        #   'collection_name': 'memprompt_collection',
        #   'backend_type': 'VDB',
        #   'embedding_model_name': 'default',
        #   'dim': 384,
        #   'description': 'A collection for locomo experiment'
        # }
        # 
        # KV类型的collection配置示例
        # config = {
        #   'collection_name': 'kvtest_collection',
        #   'backend_type': 'KV',
        #   'description': 'A collection for key-value storage'
        # }
        
        # 如果不存在则创建相应类型的collection
        if config.get("backend_type") == "VDB":
            col = manager.create_collection(
                    name=config["collection_name"],
                    backend_type="VDB",
                    embedding_model=apply_embedding_model(name=config["embedding_model_name"]),
                    dim=config["dim"],
                    description=config["description"],
                    as_ray_actor=remote, 
                )

        elif config.get("backend_type") == "KV":
            col = manager.create_collection(
                    name=config["collection_name"],
                    backend_type="KV",
                    description=config["description"],
                    as_ray_actor=remote, 
            )
            
        else:
            raise ValueError(f"Unsupported backend type: {config.get('backend_type')}")
        
        return col
    
    # 使用默认collection配置
    else:
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
    

