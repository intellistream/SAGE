#!/bin/bash
set -e

echo "Building SAGE DB - Vector Database Module..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
BUILD_TYPE="Release"
BUILD_DIR="build"
INSTALL_PREFIX="$SCRIPT_DIR/install"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --clean)
            echo "Cleaning previous build..."
            rm -rf "$BUILD_DIR" "$INSTALL_PREFIX"
            shift
            ;;
        --install-deps)
            echo "Installing dependencies..."
            # Install FAISS and other dependencies
            if command -v conda &> /dev/null; then
                echo "Installing FAISS via conda..."
                conda install -c conda-forge faiss-cpu pybind11 -y
            elif command -v pip &> /dev/null; then
                echo "Installing FAISS via pip..."
                pip install faiss-cpu pybind11[global]
            else
                echo "Warning: Neither conda nor pip found. Please install FAISS manually."
            fi
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --debug        Build in debug mode"
            echo "  --clean        Clean previous build"
            echo "  --install-deps Install dependencies (FAISS, pybind11)"
            echo "  --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for required tools
echo "Checking build dependencies..."

if ! command -v cmake &> /dev/null; then
    echo "❌ CMake not found. Please install CMake."
    exit 1
fi

if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    echo "❌ No C++ compiler found. Please install g++ or clang++."
    exit 1
fi

echo "✅ Build tools found"

# Try to find FAISS
echo "Checking for FAISS..."
FAISS_FOUND=false

# Check in conda environment
if [[ -n "$CONDA_PREFIX" ]] && [[ -f "$CONDA_PREFIX/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in conda environment: $CONDA_PREFIX"
    FAISS_FOUND=true
    export CMAKE_PREFIX_PATH="$CONDA_PREFIX:$CMAKE_PREFIX_PATH"
elif [[ -f "/usr/local/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in system path"
    FAISS_FOUND=true
elif [[ -f "/usr/include/faiss/IndexFlat.h" ]]; then
    echo "✅ Found FAISS in system path"
    FAISS_FOUND=true
else
    echo "⚠️  FAISS not found. Building with fallback implementation."
    echo "   For optimal performance, install FAISS:"
    echo "   conda install -c conda-forge faiss-cpu"
    echo "   or: pip install faiss-cpu"
fi

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with CMake
echo "Configuring build..."
CMAKE_ARGS=(
    "-DCMAKE_BUILD_TYPE=$BUILD_TYPE"
    "-DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX"
    "-DBUILD_TESTS=ON"
    "-DBUILD_PYTHON_BINDINGS=ON"
    "-DUSE_OPENMP=ON"
)

# Add conda prefix if available
if [[ -n "$CONDA_PREFIX" ]]; then
    CMAKE_ARGS+=("-DCMAKE_PREFIX_PATH=$CONDA_PREFIX")
    CMAKE_ARGS+=("-DPython3_ROOT_DIR=$CONDA_PREFIX")
fi

cmake "${CMAKE_ARGS[@]}" ..

# Build
echo "Building..."
make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

# Run tests if available
if [[ -f "test_sage_db" ]]; then
    echo "Running tests..."
    ./test_sage_db
fi

# Install
echo "Installing..."
make install

# Copy Python module to parent directory for easy import
if [[ -f "_sage_db"* ]]; then
    echo "Copying Python module..."
    cp _sage_db* ../
fi

# Create Python wrapper
cd "$SCRIPT_DIR"
cat > sage_db.py << 'EOF'
"""
SAGE DB - High-performance vector database with FAISS backend

This module provides a Python interface to the SAGE DB vector database,
which supports efficient similarity search with metadata filtering.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Callable, Tuple, Union
try:
    from . import _sage_db
except ImportError:
    import _sage_db

# Re-export C++ classes and enums
IndexType = _sage_db.IndexType
DistanceMetric = _sage_db.DistanceMetric
QueryResult = _sage_db.QueryResult
SearchParams = _sage_db.SearchParams
DatabaseConfig = _sage_db.DatabaseConfig
SageDBException = _sage_db.SageDBException

class SageDB:
    """
    High-performance vector database with FAISS backend.
    
    Supports efficient similarity search, metadata filtering, and hybrid search.
    """
    
    def __init__(self, dimension: int, 
                 index_type: IndexType = IndexType.AUTO,
                 metric: DistanceMetric = DistanceMetric.L2):
        """
        Initialize a new SageDB instance.
        
        Args:
            dimension: Vector dimension
            index_type: Index type for similarity search
            metric: Distance metric
        """
        self._db = _sage_db.create_database(dimension, index_type, metric)
    
    @classmethod
    def from_config(cls, config: DatabaseConfig):
        """Create SageDB from configuration object."""
        instance = cls.__new__(cls)
        instance._db = _sage_db.create_database(config)
        return instance
    
    def add(self, vector: Union[List[float], np.ndarray], 
            metadata: Optional[Dict[str, str]] = None) -> int:
        """Add a single vector with optional metadata."""
        if isinstance(vector, np.ndarray):
            vector = vector.tolist()
        return self._db.add(vector, metadata or {})
    
    def add_batch(self, vectors: Union[List[List[float]], np.ndarray],
                  metadata: Optional[List[Dict[str, str]]] = None) -> List[int]:
        """Add multiple vectors with optional metadata."""
        if isinstance(vectors, np.ndarray):
            if len(vectors.shape) != 2:
                raise ValueError("Vectors array must be 2-dimensional")
            return _sage_db.add_numpy(self._db, vectors, metadata or [])
        else:
            return self._db.add_batch(vectors, metadata or [])
    
    def search(self, query: Union[List[float], np.ndarray], 
               k: int = 10, include_metadata: bool = True) -> List[QueryResult]:
        """Search for similar vectors."""
        if isinstance(query, np.ndarray):
            return _sage_db.search_numpy(self._db, query, SearchParams(k))
        return self._db.search(query, k, include_metadata)
    
    def search_with_params(self, query: Union[List[float], np.ndarray],
                          params: SearchParams) -> List[QueryResult]:
        """Search with custom parameters."""
        if isinstance(query, np.ndarray):
            return _sage_db.search_numpy(self._db, query, params)
        return self._db.search(query, params)
    
    def filtered_search(self, query: Union[List[float], np.ndarray],
                       params: SearchParams,
                       filter_fn: Callable[[Dict[str, str]], bool]) -> List[QueryResult]:
        """Search with metadata filtering."""
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.filtered_search(query, params, filter_fn)
    
    def search_by_metadata(self, query: Union[List[float], np.ndarray],
                          params: SearchParams,
                          metadata_key: str,
                          metadata_value: str) -> List[QueryResult]:
        """Search with specific metadata constraint."""
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.query_engine().search_with_metadata(query, params, metadata_key, metadata_value)
    
    def hybrid_search(self, query: Union[List[float], np.ndarray],
                     params: SearchParams,
                     text_query: str = "",
                     vector_weight: float = 0.7,
                     text_weight: float = 0.3) -> List[QueryResult]:
        """Hybrid vector and text search."""
        if isinstance(query, np.ndarray):
            query = query.tolist()
        return self._db.query_engine().hybrid_search(query, params, text_query, vector_weight, text_weight)
    
    def build_index(self):
        """Build/train the search index."""
        self._db.build_index()
    
    def train_index(self, training_vectors: Optional[Union[List[List[float]], np.ndarray]] = None):
        """Train the index with training data."""
        if training_vectors is None:
            self._db.train_index()
        elif isinstance(training_vectors, np.ndarray):
            training_list = [training_vectors[i].tolist() for i in range(training_vectors.shape[0])]
            self._db.train_index(training_list)
        else:
            self._db.train_index(training_vectors)
    
    def is_trained(self) -> bool:
        """Check if the index is trained."""
        return self._db.is_trained()
    
    def set_metadata(self, vector_id: int, metadata: Dict[str, str]) -> bool:
        """Set metadata for a vector."""
        return self._db.set_metadata(vector_id, metadata)
    
    def get_metadata(self, vector_id: int) -> Optional[Dict[str, str]]:
        """Get metadata for a vector."""
        return self._db.get_metadata(vector_id)
    
    def find_by_metadata(self, key: str, value: str) -> List[int]:
        """Find vectors by metadata key-value."""
        return self._db.find_by_metadata(key, value)
    
    def save(self, filepath: str):
        """Save database to disk."""
        self._db.save(filepath)
    
    def load(self, filepath: str):
        """Load database from disk."""
        self._db.load(filepath)
    
    @property
    def size(self) -> int:
        """Number of vectors in the database."""
        return self._db.size()
    
    @property
    def dimension(self) -> int:
        """Vector dimension."""
        return self._db.dimension()
    
    @property
    def index_type(self) -> IndexType:
        """Index type."""
        return self._db.index_type()
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get last search statistics."""
        stats = self._db.query_engine().get_last_search_stats()
        return {
            'total_candidates': stats.total_candidates,
            'filtered_candidates': stats.filtered_candidates,
            'final_results': stats.final_results,
            'search_time_ms': stats.search_time_ms,
            'filter_time_ms': stats.filter_time_ms,
            'total_time_ms': stats.total_time_ms
        }

# Convenience functions
def create_database(dimension: int, 
                   index_type: IndexType = IndexType.AUTO,
                   metric: DistanceMetric = DistanceMetric.L2) -> SageDB:
    """Create a new SageDB instance."""
    return SageDB(dimension, index_type, metric)

def create_database_from_config(config: DatabaseConfig) -> SageDB:
    """Create SageDB from configuration."""
    return SageDB.from_config(config)

__all__ = [
    'SageDB', 'IndexType', 'DistanceMetric', 'QueryResult', 'SearchParams',
    'DatabaseConfig', 'SageDBException', 'create_database', 'create_database_from_config'
]
EOF

echo "✅ SAGE DB build completed!"
echo ""
echo "📁 Files created:"
echo "   - libsage_db.so (C++ library)"
echo "   - _sage_db.so (Python C++ extension)"
echo "   - sage_db.py (Python wrapper)"
echo ""
echo "🚀 Usage example:"
echo "   import sage_db"
echo "   db = sage_db.create_database(dimension=128)"
echo "   vector_id = db.add([0.1] * 128, {'text': 'example'})"
echo "   results = db.search([0.1] * 128, k=5)"
echo ""

if [[ "$FAISS_FOUND" == "false" ]]; then
    echo "⚠️  Note: Built with fallback implementation (no FAISS)."
    echo "   For better performance, install FAISS and rebuild:"
    echo "   ./build.sh --install-deps --clean"
fi
