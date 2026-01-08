import logging

import numpy as np

# Try direct imports; fallback to repo paths if needed
try:
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (
        SageDBService,
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
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.middleware.components.sage_db.python.micro_service.sage_db_service import (
        SageDBService,
    )


def main():
    env = LocalEnvironment("hello_sage_db_service")

    # Register service
    env.register_service(
        "hello_sage_db_service",
        SageDBService,
        dimension=4,
        index_type="AUTO",
    )

    # Create service instance
    svc_factory = env.service_factories["hello_sage_db_service"]
    svc: SageDBService = svc_factory.create_service()

    # Insert demo vectors
    for uid in range(3):
        vec = np.arange(4, dtype=np.float32) + uid
        svc.add(vec, {"uid": str(uid), "tag": "svc_demo"})

    # Search
    results = svc.search([0, 1, 2, 3], k=2)
    print("Service search results:")
    for r in results:
        print(r)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    CustomLogger.disable_global_console_debug()
    main()
