"""
SAGE Database Extension

High-performance vector database with FAISS backend.
"""

__version__ = "0.1.0"

# 导入状态跟踪
_cpp_available = False
_python_wrapper_available = False

# 尝试导入C++扩展
try:
    from . import _sage_db
    _cpp_available = True
    
    # 从C++扩展中导入所有关键类和函数
    IndexType = _sage_db.IndexType
    DistanceMetric = _sage_db.DistanceMetric
    QueryResult = _sage_db.QueryResult
    SearchParams = _sage_db.SearchParams
    DatabaseConfig = _sage_db.DatabaseConfig
    SageDBException = _sage_db.SageDBException
    
    # 工厂函数
    create_database = _sage_db.create_database
    
    # 实用函数
    index_type_to_string = _sage_db.index_type_to_string
    string_to_index_type = _sage_db.string_to_index_type
    distance_metric_to_string = _sage_db.distance_metric_to_string
    string_to_distance_metric = _sage_db.string_to_distance_metric
    
    print("✓ C++ extension imported successfully")
    
except ImportError as e:
    import warnings
    warnings.warn(f"SAGE DB C++ extension not available: {e}")
    
    # 提供fallback类
    class IndexType:
        FLAT = "FLAT"
        IVF_FLAT = "IVF_FLAT"
        IVF_PQ = "IVF_PQ"
        HNSW = "HNSW"
        AUTO = "AUTO"
    
    class DistanceMetric:
        L2 = "L2"
        INNER_PRODUCT = "INNER_PRODUCT"
        COSINE = "COSINE"
    
    class QueryResult:
        def __init__(self, id, score, metadata=None):
            self.id = id
            self.score = score
            self.metadata = metadata or {}
    
    class SearchParams:
        def __init__(self, k=10):
            self.k = k
            self.nprobe = 1
            self.radius = 0.0
            self.include_metadata = True
    
    class DatabaseConfig:
        def __init__(self, dimension=128):
            self.dimension = dimension
            self.index_type = IndexType.AUTO
            self.metric = DistanceMetric.L2
    
    class SageDBException(Exception):
        pass

# 导入Python包装器
try:
    from .sage_db import SageDB
    _python_wrapper_available = True
    print("✓ Python wrapper imported successfully")
except ImportError as e:
    import warnings
    warnings.warn(f"SAGE DB Python wrapper not available: {e}")
    
    # 如果Python包装器不可用，提供fallback
    class SageDB:
        def __init__(self, *args, **kwargs):
            if _cpp_available:
                # 如果C++扩展可用，直接使用
                if len(args) == 1 and isinstance(args[0], int):
                    # SageDB(dimension)
                    config = DatabaseConfig(args[0])
                    self._db = create_database(config)
                elif len(args) == 1:
                    # SageDB(config)
                    self._db = create_database(args[0])
                else:
                    # SageDB(dimension, index_type, metric)
                    dimension = kwargs.get('dimension', args[0] if args else 128)
                    index_type = kwargs.get('index_type', args[1] if len(args) > 1 else IndexType.AUTO)
                    metric = kwargs.get('metric', args[2] if len(args) > 2 else DistanceMetric.L2)
                    self._db = create_database(dimension, index_type, metric)
            else:
                raise ImportError("SAGE DB is not available. Please build the C++ extensions.")
        
        def add(self, vector, metadata=None):
            return self._db.add(vector, metadata or {})
        
        def add_batch(self, vectors, metadata=None):
            return self._db.add_batch(vectors, metadata or [])
        
        def search(self, query, k=10, include_metadata=True):
            return self._db.search(query, k, include_metadata)

# 导出的API
__all__ = [
    'SageDB',
    'IndexType', 
    'DistanceMetric',
    'QueryResult',
    'SearchParams',
    'DatabaseConfig',
    'SageDBException',
    'create_database',
    'index_type_to_string',
    'string_to_index_type',
    'distance_metric_to_string', 
    'string_to_distance_metric',
    'is_available',
    'get_status'
]

# 状态检查函数
def is_available() -> bool:
    """Check if SAGE DB is available"""
    return _cpp_available

def get_status() -> dict:
    """Get detailed status information"""
    return {
        'cpp_extension': _cpp_available,
        'python_wrapper': _python_wrapper_available,
        'fully_available': _cpp_available and _python_wrapper_available
    }
