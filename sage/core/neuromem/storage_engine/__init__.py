PHYSICAL_MEMORY_IMPLEMENTATIONS = {
    "VECTOR_MEMORY": {
        "implementations": [
            "CandyMemory",
            "FaissMemory",
        ],
        "required_methods": ["store", "retrieve", "delete", "clean"],
    },
}

PHYSICAL_MEMORY_ENV_REQUIREMENTS: dict[str, list[str]] = {
    # Vector Physical Memory Implementations
    "CandyMemory": [],
    "FaissMemory": [],
}

# Physical Memory implementation module mapping
PHYSICAL_MEMORY = {
    "FaissMemory": "sage.core.neuromem.storage_engine.faiss_impl",
    "CandyMemory": "sage.core.neuromem.storage_engine.candy_impl",
}

def verify_physical_memory_implementation(physical_memory_type: str, physical_memory_name: str) -> None:
    """Verify if physical memory implementation is compatible with specified physical_memory type
    """
    if physical_memory_type not in PHYSICAL_MEMORY_IMPLEMENTATIONS:
        raise ValueError(f"Unknown physical memory type: {physical_memory_type}")

    physical_memory_info = PHYSICAL_MEMORY_IMPLEMENTATIONS[physical_memory_type]
    if physical_memory_name not in physical_memory_info["implementations"]:
        raise ValueError(
            f"Physical memory implementation '{physical_memory_type}' is not compatible with {physical_memory_name}. "
            f"Compatible implementations are: {', '.join(physical_memory_info['implementations'])}"
        )
    
def check_physical_memory_env_vars(physical_memory_name: str) -> None:
    """Check if all required environment variables for physical_memory implementation exist
    """
    import os
    required_vars = PHYSICAL_MEMORY_ENV_REQUIREMENTS.get(physical_memory_name, [])
    missing_vars = [var for var in required_vars if var not in os.environ]

    if missing_vars:
        raise ValueError(
            f"Physical Memory implementation '{physical_memory_name}' requires the following "
            f"environment variables: {', '.join(missing_vars)}"
        )

import importlib
import inspect

def get_physical_memory_class(physical_memory_name: str, **kwargs):
    """动态实例化物理内存类，自动过滤无效参数"""
    
    # 1. 验证内存名称合法性
    if physical_memory_name not in PHYSICAL_MEMORY:
        raise ValueError(f"Unknown physical memory: {physical_memory_name}")
    
    # 2. 动态导入模块
    import_path = PHYSICAL_MEMORY[physical_memory_name]
    try:
        module = importlib.import_module(import_path)
        memory_class = getattr(module, physical_memory_name)
    except Exception as e:
        raise ImportError(f"Load {physical_memory_name} failed: {str(e)}")

    # 3. 获取构造函数签名并过滤参数
    sig = inspect.signature(memory_class.__init__)
    valid_params = {
        k: v for k, v in kwargs.items() 
        if k in sig.parameters and k != "self"
    }

    # 4. 验证必需参数是否齐全
    required_params = [
        p.name for p in sig.parameters.values() 
        if p.default == inspect.Parameter.empty 
        and p.name not in ("self", "args", "kwargs")
    ]
    missing_params = [p for p in required_params if p not in valid_params]
    if missing_params:
        raise ValueError(f"Missing required params for {physical_memory_name}: {missing_params}")

    # 5. 实例化并返回
    return memory_class(**valid_params)

def get_filtered_config(config, prefix = None):
    if prefix is None:
        raise ValueError(f"Undefined prefix!")
    """从config中提取参数并自动去除指定前缀"""
    return {
        k.replace(prefix, ""): v 
        for k, v in config.items() 
        if k.startswith(prefix)
    }