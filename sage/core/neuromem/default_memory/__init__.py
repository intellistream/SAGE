DEFAULT_MEMORY = {
    "short_term_memory": "sage.core.neuromem.default_memory.short_term_memory",
    "long_term_memory": "sage.core.neuromem.default_memory.long_term_memory",
    "dynamic_contextual_memory": "sage.core.neuromem.default_memory.dynamic_contextual_memory"
}

MEMORY_BACKEND_MAPPING = {
    ("vector_db.candy", "long_term_memory"): {
        "config_key": "LTM_Physical_Memory",
        "memory_class": "CandyMemory",
    },
    ("vector_db.candy", "dynamic_contextual_memory"): {
        "config_key": "DCM_Physical_Memory",
        "memory_class": "CandyMemory",
    },
    ("vector_db.faiss", "long_term_memory"): {
        "config_key": "LTM_Physical_Memory",
        "memory_class": "FaissMemory",
    },
    ("vector_db.faiss", "dynamic_contextual_memory"): {
        "config_key": "DCM_Physical_Memory",
        "memory_class": "FaissMemory",
    },
}

import importlib
import inspect
import os
import json

def get_default_memory_class(default_memory_name: str, memory_table_backend: str | None = None):
    """Dynamically instantiation of default memory classes, automatically filtering out invalid parameters"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "default_memory_config.json")
    with open(config_path, 'r') as f:
        config = json.load(f).get("neuromem")

    if memory_table_backend is not None:
        mapping_key = (memory_table_backend, default_memory_name)
        if mapping_key in MEMORY_BACKEND_MAPPING:
            mapping = MEMORY_BACKEND_MAPPING[mapping_key]
            config[mapping["config_key"]] = mapping["memory_class"]

    # 1. Verify the legality of memory names
    if default_memory_name not in DEFAULT_MEMORY:
        raise ValueError(f"Unknown default memory: {default_memory_name}")
    
    # 2. Dynamic import module
    import_path = DEFAULT_MEMORY[default_memory_name]
    try:
        module = importlib.import_module(import_path)
        class_name = default_memory_name.title().replace("_", "")
        memory_class = getattr(module, class_name)
    except Exception as e:
        raise ImportError(f"Load {default_memory_name} failed: {str(e)}")
    
    # Check if the class's __init__ accepts config
    init_signature = inspect.signature(memory_class.__init__)
    parameters = init_signature.parameters
    
    # Skip 'self' parameter, check if there are any other required parameters
    has_config_param = any(
        param.name != 'self' and 
        param.default == param.empty  # Parameter is required (no default)
        for param in parameters.values()
    )
    
    if has_config_param:
        return memory_class(config)
    else:
        return memory_class()
