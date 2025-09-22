import logging
import time
import numpy as np

# Try standard imports first; fall back to adding local package src paths when running from repo
try:
    try:
        from sage.common.utils.logging.custom_logger import CustomLogger
        from sage.middleware.components.sage_flow.sage_flow import (
            SimpleStreamSource,
            StreamEnvironment,
        )
    except ImportError:
        raise
except ModuleNotFoundError:
    import os
    import sys
    from pathlib import Path

    # Detect repository root by locating the directory that contains 'packages/'
    here = Path(__file__).resolve()
    repo_root = None
    for p in here.parents:
        if (p / "packages").exists():
            repo_root = p
            break
    if repo_root is None:
        # Fallback to 4-levels up (…/SAGE)
        repo_root = here.parents[3]

    # Insert package src paths, ensuring namespace package 'sage' is loaded first
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
    from sage.middleware.components.sage_flow.sage_flow import (
        SimpleStreamSource,
        StreamEnvironment,
    )


def main():
    # 直接使用 sage_flow 的绑定构建一个最小 pipeline
    env = StreamEnvironment()
    source = SimpleStreamSource("hello_source")

    # 通过 Python 回调挂载一个 sink，用于验证处理的记录数
    processed = {"count": 0}

    def on_sink(uid: int, ts: int):
        # 简单累加计数，验证 pipeline 正常运行
        processed["count"] += 1

    # 将 sink 直接挂在 source 上（返回下游 stream，但无需手动加入 env）
    source.write_sink_py("py_sink", on_sink)

    # 注入几条向量
    dim = 4
    total = 5
    for uid in range(total):
        vec = np.arange(dim, dtype=np.float32) + uid
        ts = int(time.time() * 1000)
        source.addRecord(uid, ts, vec)

    # 将源加入环境并执行
    env.addStream(source)
    logging.info("execute start")
    env.execute()
    logging.info("execute done")

    # 简单校验：处理的记录数应等于注入的记录数
    assert processed["count"] == total, (
        f"processed count {processed['count']} != expected {total}"
    )
    logging.info(f"processed count: {processed['count']}")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()
    main()
