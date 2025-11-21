"""
Simple dataset wrapper for ANNS benchmarking
"""
import numpy as np
import os
import struct


class SimpleDataset:
    """
    Simple dataset wrapper that loads vectors from binary files.
    Compatible with the neurips23 data format.
    """
    
    def __init__(self, name, data_path, dtype='float32', metric='euclidean'):
        """
        Args:
            name: Dataset name
            data_path: Path to the dataset directory
            dtype: Data type ('float32', 'uint8', 'int8')
            metric: Distance metric ('euclidean', 'angular')
        """
        self.name = name
        self.data_path = data_path
        self.dtype = dtype
        self.metric = metric
        
        # Dataset properties (to be loaded)
        self.nb = 0  # Number of base vectors
        self.nq = 0  # Number of query vectors
        self.d = 0   # Dimensionality
        
        self._base_data = None
        self._query_data = None
        self._groundtruth = None

    def load_fvecs(self, filename):
        """
        Load vectors from .fvecs file format.
        
        Format: Each vector is stored as [dim, v1, v2, ..., vdim] where dim is int32
        and vi are float32 values.
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(filename, 'rb') as f:
            # Read dimension from first vector
            dim_bytes = f.read(4)
            if len(dim_bytes) < 4:
                return np.array([])
            
            dim = struct.unpack('i', dim_bytes)[0]
            f.seek(0)
            
            # Calculate number of vectors
            file_size = os.path.getsize(filename)
            vec_size = 4 + dim * 4  # 4 bytes for dim + dim * 4 bytes for floats
            num_vecs = file_size // vec_size
            
            # Read all vectors
            vectors = []
            for _ in range(num_vecs):
                d = struct.unpack('i', f.read(4))[0]
                vec = struct.unpack('f' * d, f.read(4 * d))
                vectors.append(vec)
            
            return np.array(vectors, dtype=np.float32)

    def load_bvecs(self, filename):
        """Load vectors from .bvecs file format (uint8)."""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(filename, 'rb') as f:
            dim_bytes = f.read(4)
            if len(dim_bytes) < 4:
                return np.array([])
            
            dim = struct.unpack('i', dim_bytes)[0]
            f.seek(0)
            
            file_size = os.path.getsize(filename)
            vec_size = 4 + dim  # 4 bytes for dim + dim bytes for uint8
            num_vecs = file_size // vec_size
            
            vectors = []
            for _ in range(num_vecs):
                d = struct.unpack('i', f.read(4))[0]
                vec = struct.unpack('B' * d, f.read(d))
                vectors.append(vec)
            
            return np.array(vectors, dtype=np.uint8)

    def load_ivecs(self, filename):
        """Load vectors from .ivecs file format (int32)."""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")
        
        with open(filename, 'rb') as f:
            dim_bytes = f.read(4)
            if len(dim_bytes) < 4:
                return np.array([])
            
            dim = struct.unpack('i', dim_bytes)[0]
            f.seek(0)
            
            file_size = os.path.getsize(filename)
            vec_size = 4 + dim * 4
            num_vecs = file_size // vec_size
            
            vectors = []
            for _ in range(num_vecs):
                d = struct.unpack('i', f.read(4))[0]
                vec = struct.unpack('i' * d, f.read(4 * d))
                vectors.append(vec)
            
            return np.array(vectors, dtype=np.int32)

    def load_base(self, filename=None):
        """Load base vectors"""
        if filename is None:
            filename = os.path.join(self.data_path, f"{self.name}_base.fvecs")
        
        if filename.endswith('.fvecs'):
            self._base_data = self.load_fvecs(filename)
        elif filename.endswith('.bvecs'):
            self._base_data = self.load_bvecs(filename)
        else:
            raise ValueError(f"Unsupported file format: {filename}")
        
        if self._base_data.size > 0:
            self.nb = self._base_data.shape[0]
            self.d = self._base_data.shape[1]
        
        print(f"Loaded {self.nb} base vectors of dimension {self.d}")
        return self._base_data

    def load_queries(self, filename=None):
        """Load query vectors"""
        if filename is None:
            filename = os.path.join(self.data_path, f"{self.name}_query.fvecs")
        
        if filename.endswith('.fvecs'):
            self._query_data = self.load_fvecs(filename)
        elif filename.endswith('.bvecs'):
            self._query_data = self.load_bvecs(filename)
        else:
            raise ValueError(f"Unsupported file format: {filename}")
        
        if self._query_data.size > 0:
            self.nq = self._query_data.shape[0]
        
        print(f"Loaded {self.nq} query vectors")
        return self._query_data

    def load_groundtruth(self, filename=None):
        """Load groundtruth nearest neighbors"""
        if filename is None:
            filename = os.path.join(self.data_path, f"{self.name}_groundtruth.ivecs")
        
        self._groundtruth = self.load_ivecs(filename)
        print(f"Loaded groundtruth with shape {self._groundtruth.shape}")
        return self._groundtruth

    def get_dataset(self):
        """Get base dataset vectors"""
        if self._base_data is None:
            self.load_base()
        return self._base_data

    def get_queries(self):
        """Get query vectors"""
        if self._query_data is None:
            self.load_queries()
        return self._query_data

    def get_groundtruth(self):
        """Get groundtruth"""
        if self._groundtruth is None:
            self.load_groundtruth()
        return self._groundtruth


# Simple dataset registry
DATASETS = {}


def register_dataset(name, dataset_factory):
    """Register a dataset factory function"""
    DATASETS[name] = dataset_factory


def get_dataset(name):
    """Get a dataset by name"""
    if name not in DATASETS:
        raise ValueError(f"Dataset '{name}' not registered. Available: {list(DATASETS.keys())}")
    return DATASETS[name]()
