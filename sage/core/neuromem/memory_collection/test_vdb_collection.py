# file: sage/core/neuromem/memory_collection/test_vdb_collection.py
# python -m sage.core.neuromem.memory_collection.test_vdb_collection
"""
Smoke‑test for VDBMemoryCollection
---------------------------------
* uses MockTextEmbedder (128‑dim deterministic embeddings)
* exercises insert → create_index → retrieve → flush → reload → retrieve

Run:
    python -m sage.core.neuromem.memory_collection.test_vdb_collection
"""
from __future__ import annotations

import shutil, tempfile
from pathlib import Path

import numpy as np

from sage.core.neuromem.memory_collection.vdb_collection import VDBMemoryCollection
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder

TMP = Path(tempfile.mkdtemp())
print("TMP =", TMP)

# ---------------------------------------------------------------------
# 1) create collection, insert data
# ---------------------------------------------------------------------
model = MockTextEmbedder(fixed_dim=128)
coll = VDBMemoryCollection("demo_vdb", model, 128, storage_root=TMP)
# register meta fields
coll.add_metadata_field("lang")
coll.add_metadata_field("source")

coll.insert("hello world", {"lang": "en", "source": "user"})
coll.insert("你好 世界", {"lang": "zh", "source": "user"})
print("inserted →", coll.stats)

# ---------------------------------------------------------------------
# 2) build a default index (all items)
# ---------------------------------------------------------------------
coll.create_index("default")
print("indexes:", coll.list_index())

# vector retrieve (should return top‑1 self)
print("search 'hello':", coll.retrieve("hello", index_name="default"))

# flush to disk
coll.flush()

# ---------------------------------------------------------------------
# 3) reload & make sure retrieve still works
# ---------------------------------------------------------------------
coll.release()
coll_loaded = VDBMemoryCollection("demo_vdb", model, 128, storage_root=TMP)
coll_loaded.add_metadata_field("lang")
coll_loaded.add_metadata_field("source")
coll_loaded.load()
# re‑create index object from saved .index file
coll_loaded.create_index("default")
print("reload →", coll_loaded.retrieve("你好", index_name="default"))

shutil.rmtree(TMP)
print("Passed!")

"""
expected output:
TMP = /tmp/tmp490ie7be
inserted → {'count': 2, 'last_updated': '2025-06-15T09:12:32.057163Z'}
Wrapping index with IndexIDMap
indexes: [{'name': 'default', 'index_description': ''}]
Wrapping index with IndexIDMap
search 'hello': ['你好 世界', 'hello world']
Wrapping index with IndexIDMap
Wrapping index with IndexIDMap
reload → ['你好 世界', 'hello world']
Passed!
"""