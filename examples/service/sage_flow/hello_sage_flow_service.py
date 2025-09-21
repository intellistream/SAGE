import time
import numpy as np

# Try direct imports; if running from repo without installation, add local package paths
try:
    try:
        from sage.common.utils.logging.custom_logger import CustomLogger
        from sage.core.api.local_environment import LocalEnvironment
        from sage.middleware.components.sage_flow.micro_service.sage_flow_service import (
            SageFlowService,
        )
    except ImportError as e:
        if os.getenv("SAGE_EXAMPLES_MODE") == "test" or os.getenv("SAGE_TEST_MODE") == "true":
            print("[skip] candyFlow extension not available; skipping hello_sage_flow_service in test mode")
            import sys as _sys

            _sys.exit(0)
        raise
except ModuleNotFoundError:
    import os
    import sys
    from pathlib import Path

    here = Path(__file__).resolve()
    repo_root = None
    for p in here.parents:
        if (p / "packages").exists():
            repo_root = p
            break
    if repo_root is None:
        repo_root = here.parents[3]

    src_paths = [
        repo_root / "packages" / "sage" / "src",
        repo_root / "packages" / "sage-common" / "src",
        repo_root / "packages" / "sage-kernel" / "src",
        repo_root / "packages" / "sage-middleware" / "src",
        repo_root / "packages" / "sage-libs" / "src",
        repo_root / "packages" / "sage-tools" / "src",
    ]
    for p in src_paths:
        sys.path.insert(0, str(p))

    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.core.api.local_environment import LocalEnvironment
    from sage.middleware.components.sage_flow.micro_service.sage_flow_service import (
        SageFlowService,
    )


def main():
    env = LocalEnvironment("hello_sage_flow_service")

    # 注册 SageFlowService（与 neuromem_vdb 风格一致）
    env.register_service(
        "hello_sage_flow_service",
        SageFlowService,
        dim=4,
        dtype="Float32",
    )

    # 获取服务实例
    service_factory = env.service_factories["hello_sage_flow_service"]
    svc: SageFlowService = service_factory.create_service()

    # 推入几条数据
    for uid in range(3):
        vec = np.arange(4, dtype=np.float32) + uid
        svc.push(uid, vec)

    # 运行一次，将队列中的数据消费（内部会执行 env.execute()）
    svc.run()

    print("Service demo done")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
