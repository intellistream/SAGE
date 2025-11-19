# @test:skip - 跳过测试
import os

from sage.benchmark.benchmark_memory.experiment.utils.time_geter import get_time_filename
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.data.locomo.dataloader import LocomoDataLoader
from sage.benchmark.benchmark_memory.experiment.libs.locomo_source import LocomoSource
from sage.benchmark.benchmark_memory.experiment.libs.memory_sink import MemorySink


# ==== 测试代码 ====
if __name__ == "__main__":


    # 禁用debug日志
    CustomLogger.disable_global_console_debug()

    # 获取第一个sample_id进行测试
    loader = LocomoDataLoader()
    sample_ids = loader.get_sample_id()
    test_sample_id = sample_ids[0]

    print(f"🧪 使用样本 ID 进行测试: {test_sample_id}")
    print("=" * 60)

    # 创建环境和pipeline
    env = LocalEnvironment("Test_Locomo_IO")
    outfile = f"{get_time_filename()}_test"
    env.from_batch(LocomoSource, sample_id=test_sample_id).sink(MemorySink, dataset_name="locomo", output_name=outfile)
    env.submit(autostop=True)

    print("=" * 60)
    print(f"✅ 测试完成！请查看输出文件: {outfile}.txt")