"""
SAGE Database Extension

High-performance vector database with FAISS backend.
"""

import os
import sys
import warnings
from typing import List, Optional

__version__ = "0.1.0"

# 设置库路径以便找到依赖的 .so 文件
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# 设置 LD_LIBRARY_PATH 环境变量
if "LD_LIBRARY_PATH" in os.environ:
    os.environ["LD_LIBRARY_PATH"] = f"{_current_dir}:{os.environ['LD_LIBRARY_PATH']}"
else:
    os.environ["LD_LIBRARY_PATH"] = _current_dir

# 尝试导入C++扩展
_cpp_available = False
_import_error = None

try:
    # 直接导入 C++ 扩展模块
    from . import _sage_db
    
    # 导入所有必要的类和函数
    IndexType = _sage_db.IndexType
    DistanceMetric = _sage_db.DistanceMetric
    QueryResult = _sage_db.QueryResult
    SearchParams = _sage_db.SearchParams
    DatabaseConfig = _sage_db.DatabaseConfig
    SageDBException = _sage_db.SageDBException
    
    # 检查是否有工厂函数
    if hasattr(_sage_db, 'create_database'):
        create_database = _sage_db.create_database
    else:
        # 如果没有工厂函数，创建一个简单的包装器
        def create_database(dimension, index_type=None, metric=None):
            if index_type is None:
                index_type = IndexType.AUTO
            if metric is None:
                metric = DistanceMetric.L2
            
            config = DatabaseConfig()
            config.dimension = dimension
            config.index_type = index_type
            config.distance_metric = metric
            return _sage_db.SageDB(config)
    
    # 导入核心 SageDB 类
    SageDB = _sage_db.SageDB
    
    _cpp_available = True
    print("✓ SAGE DB C++ extension loaded successfully")
    
except ImportError as e:
    _import_error = str(e)
    warnings.warn(f"SAGE DB C++ extension not available: {e}")
    
    # 提供 fallback 实现
    class SageDB:
        """Fallback SageDB implementation"""
        def __init__(self, *args, **kwargs):
            raise ImportError(f"SAGE DB C++ extension not available: {_import_error}")
    
    class IndexType:
        FLAT = "FLAT"
        IVF_FLAT = "IVF_FLAT"
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
    
    class DatabaseConfig:
        def __init__(self):
            self.dimension = 128
            self.index_type = IndexType.AUTO
            self.distance_metric = DistanceMetric.L2
    
    class SageDBException(Exception):
        pass
    
    def create_database(*args, **kwargs):
        raise ImportError(f"SAGE DB C++ extension not available: {_import_error}")

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
        'import_error': _import_error,
        'fully_available': _cpp_available
    }
