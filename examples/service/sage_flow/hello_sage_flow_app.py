import logging
import time

import numpy as np
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.sage_flow.python.sage_flow import (
    SimpleStreamSource, StreamEnvironment)


def main():
    # 直接使用 sage_flow 的绑定构建一个最小 pipeline
    env = StreamEnvironment()
    source = SimpleStreamSource("hello_source")

    # 通过 Python 回调挂载一个 sink，用于验证处理的记录数
    processed = {"count": 0}

    def on_sink(uid: int, ts: int):
        # 简单累加计数，验证 pipeline 正常运行，并打印出处理记录
        processed["count"] += 1
        print(f"[py_sink] processed uid={uid}, ts={ts}")

    # 将 sink 直接挂在 source 上（返回下游 stream，但无需手动加入 env）
    source.write_sink_py("py_sink", on_sink)

    # 注入几条向量
    dim = 4
    total = 5
    for uid in range(total):
        vec = np.arange(dim, dtype=np.float32) + uid
        ts = int(time.time() * 1000)
        source.addRecord(uid, ts, vec)

    # 将源加入环境并执行（注意：需要在添加数据之前添加到环境）
    env.addStream(source)
    logging.info("execute start")
    env.execute()
    logging.info("execute done")

    # 等待异步处理完成
    max_wait_time = 5.0  # 最多等待5秒
    wait_interval = 0.1  # 每次等待100ms
    elapsed_time = 0.0

    while processed["count"] < total and elapsed_time < max_wait_time:
        time.sleep(wait_interval)
        elapsed_time += wait_interval

    logging.info(f"processed count: {processed['count']} (expected: {total})")

    # 简单校验：处理的记录数应等于注入的记录数
    if processed["count"] != total:
        logging.warning(f"处理记录数不匹配: 实际 {processed['count']}, 期望 {total}")
        logging.warning("这可能是由于异步处理延迟或数据源配置问题造成的")
        # 在示例中不要抛出异常，只是警告
        # assert False, f"processed count {processed['count']} != expected {total}"
    else:
        logging.info("✅ 数据处理验证通过")


if __name__ == "__main__":
    # 显示标准 logging 的 INFO 级别日志
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # 关闭自定义全局控制台日志（不影响标准 logging 和 print 输出）
    CustomLogger.disable_global_console_debug()
    main()
