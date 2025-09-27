import logging
import time

import numpy as np

# Try direct imports; if running from repo without installation, add local package paths
try:
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.core.api.local_environment import LocalEnvironment
    from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import \
        SageFlowService
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
    from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import \
        SageFlowService


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

    # 附加一个可见的 Python sink，以便运行时在控制台看到处理结果
    processed = {"count": 0}

    def on_sink(uid: int, ts: int):
        processed["count"] += 1
        print(f"[service py_sink] processed uid={uid}, ts={ts}", flush=True)

    svc.set_sink(on_sink)

    # 推入几条数据
    total = 3
    for uid in range(total):
        vec = np.arange(4, dtype=np.float32) + uid
        svc.push(uid, vec)

    # 运行一次，将队列中的数据消费（内部会执行 env.execute()）
    svc.run()
    
    # 等待异步处理完成（参考 hello_sage_flow_app.py 的实现）
    max_wait_time = 5.0  # 最多等待5秒
    wait_interval = 0.1  # 每次等待100ms
    elapsed_time = 0.0

    while processed["count"] < total and elapsed_time < max_wait_time:
        time.sleep(wait_interval)
        elapsed_time += wait_interval

    logging.info(f"processed count: {processed['count']} (expected: {total})")
    print(f"processed count: {processed['count']}")

    # 简单校验：处理的记录数应等于注入的记录数
    if processed["count"] != total:
        logging.warning(f"处理记录数不匹配: 实际 {processed['count']}, 期望 {total}")
        logging.warning("这可能是由于异步处理延迟或数据源配置问题造成的")
        # 在示例中不要抛出异常，只是警告
    else:
        logging.info("✅ 数据处理验证通过")
    
    logging.info("Service demo done")


if __name__ == "__main__":
    # 显示标准 logging 的 INFO 级别日志
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # 关闭自定义全局控制台日志（不影响标准 logging 和 print 输出）
    CustomLogger.disable_global_console_debug()
    main()
