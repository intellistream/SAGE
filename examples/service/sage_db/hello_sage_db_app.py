import logging
import time

import numpy as np

# Add repo package paths if needed
try:
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.middleware.components.sage_db.python.sage_db import (
        DatabaseConfig,
        IndexType,
        SageDB,
    )
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    here = Path(__file__).resolve()
    repo_root = None
    for p in here.parents:
        if (p / "packages").exists():
            repo_root = p
            break
    assert repo_root is not None
    for p in [
        repo_root / "packages" / "sage" / "src",
        repo_root / "packages" / "sage-common" / "src",
        repo_root / "packages" / "sage-kernel" / "src",
        repo_root / "packages" / "sage-middleware" / "src",
        repo_root / "packages" / "sage-libs" / "src",
        repo_root / "packages" / "sage-tools" / "src",
    ]:
        sys.path.insert(0, str(p))

    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.middleware.components.sage_db.python.sage_db import (
        DatabaseConfig,
        IndexType,
        SageDB,
    )


def main():
    dim = 4
    # Create DB with config
    cfg = DatabaseConfig(dim)
    cfg.index_type = IndexType.AUTO
    db = SageDB.from_config(cfg)

    # Add few vectors
    total = 5
    for uid in range(total):
        vec = np.arange(dim, dtype=np.float32) + uid
        db.add(vec, {"tag": "demo", "uid": str(uid)})

    # Search
    query = np.array([0, 1, 2, 3], dtype=np.float32)
    results = db.search(query, k=3)
    print("Top-3 results:")
    for r in results:
        print(f"  id={r.id}, score={r.score:.4f}, md={dict(r.metadata)}")

    # Stats
    print("DB size:", db.size)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    CustomLogger.disable_global_console_debug()
    main()
