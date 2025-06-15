"""
Smoke-test for BaseMemoryCollection
$ python -m sage.core.neuromem.memory_collection.test_base_collection
"""
from pathlib import Path
import shutil, tempfile

from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection

# ── 临时目录 ─────────────────────────────────────────────────────────
tmp_root = Path(tempfile.mkdtemp())            # /tmp/xxxx
print("TMP =", tmp_root)

# ── 1. 创建新的 KV collection ───────────────────────────────────────
coll = BaseMemoryCollection("demo_kv", storage_root=tmp_root)
coll.add_metadata_field("lang")
coll.add_metadata_field("source")

# 写入 2 条
coll.insert("hello world", {"lang": "en", "source": "cli"})
coll.insert("你好 世界",    {"lang": "zh", "source": "cli"})
print("inserted →", coll.stats)

# ── 2. 读取 / 条件过滤 ───────────────────────────────────────────────
print("all:", coll.retrieve())
print("only zh:", coll.retrieve(metadata_filter_func=lambda m: m["lang"] == "zh"))

# ── 3. flush（落盘 manifest）+ release ──────────────────────────────
coll.flush(); coll.release()

# ── 4. 重新 load 再次检索 ────────────────────────────────────────────
coll_loaded = BaseMemoryCollection("demo_kv", storage_root=tmp_root)
coll_loaded.load()
print("after reload:", coll_loaded.retrieve(with_metadata=True))

# ── 清理 ────────────────────────────────────────────────────────────
shutil.rmtree(tmp_root)
"""
expected output:
TMP = /tmp/tmpinpn5s_0
inserted → {'count': 2, 'last_updated': '2025-06-15T08:25:14.311317Z'}
all: ['hello world', '你好 世界']
only zh: ['你好 世界']
after reload: [{'text': 'hello world', 'metadata': {'lang': 'en', 'source': 'cli'}}, {'text': '你好 世界', 'metadata': {'lang': 'zh', 'source': 'cli'}}]
"""
