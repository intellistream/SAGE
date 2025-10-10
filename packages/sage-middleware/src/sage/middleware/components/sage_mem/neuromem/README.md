# neuromem

**neuromem** is a standalone memory management engine designed for RAG (Retrieval-Augmented Generation) applications. It provides flexible memory collection abstractions with support for vector databases, key-value stores, and graph structures.

## Features

- **Multiple Backend Support**: VDB (Vector Database), KV (Key-Value), Graph
- **Flexible Storage Engine**: Pluggable storage backends for vectors, text, and metadata
- **Powerful Search Engine**: Multiple index types (FAISS, BM25s, etc.)
- **Collection Management**: Create, load, store, and manage memory collections
- **Memory Manager**: Centralized management of multiple collections

## Architecture

```
neuromem/
├── memory_manager.py          # Central manager for collections
├── memory_collection/         # Collection abstractions
│   ├── base_collection.py
│   ├── vdb_collection.py
│   ├── kv_collection.py
│   └── graph_collection.py
├── search_engine/             # Index implementations
│   ├── vdb_index/
│   ├── kv_index/
│   └── graph_index/
├── storage_engine/            # Storage backends
│   ├── vector_storage.py
│   ├── text_storage.py
│   └── metadata_storage.py
└── utils/                     # Utility functions
```

## Quick Start

```python
from neuromem.memory_manager import MemoryManager

# Create manager
manager = MemoryManager()

# Create a VDB collection
config = {
    "name": "my_collection",
    "backend_type": "VDB",
    "description": "My vector database collection"
}
collection = manager.create_collection(config)

# Insert data
collection.batch_insert_data(
    texts=["Hello world", "Goodbye world"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}]
)

# Create index
index_config = {
    "name": "my_index",
    "embedding_model": "mockembedder",
    "dim": 128,
    "backend_type": "FAISS"
}
collection.create_index(index_config)

# Retrieve
results = collection.retrieve(
    "Hello",
    index_name="my_index",
    topk=5
)
```

## Future Plans

This sub-project will eventually be separated into its own repository and may be rewritten in C++/Rust for better performance.

## License

See LICENSE file in the SAGE project root.
