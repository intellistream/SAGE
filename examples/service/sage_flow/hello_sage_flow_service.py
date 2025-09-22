import time
import numpy as np

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
