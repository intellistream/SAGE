from sage.core.neuromem.default_memory import (
    get_default_memory_instance,
    is_default_memory_class,
    get_default_memory_backend_type,
)

from sage.core.neuromem.storage_engine import (
    verify_physical_memory_implementation,
    check_physical_memory_env_vars,
    get_physical_memory_class,
    get_filtered_config,
)

class MemoryBackend:
    @staticmethod
    def create_table(memory_name: str, backend: str | None = None):
        """Create and return an instance of the memory class based on the name."""
        if is_default_memory_class(memory_name):
            return get_default_memory_instance(memory_name, backend), get_default_memory_backend_type(memory_name)

        # TODO default pysical storage config
        import os
        import json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "default_memory/default_memory_config.json")
        with open(config_path, 'r') as f:
            config = json.load(f)
        config = config.get("neuromem")
        physical_name = config.get("LTM_Physical_Memory")
        config = config.get(physical_name + "_LTM")
        verify_physical_memory_implementation("VECTOR_MEMORY", physical_name)
        check_physical_memory_env_vars(physical_name)
        physical_memory = get_physical_memory_class(
            physical_memory_name = physical_name,
            **get_filtered_config(config, "ltm_")
        )
        return physical_memory, "test"
    
if __name__ == "__main__":
    print(MemoryBackend.create_table("test", "FaissMemory"))
