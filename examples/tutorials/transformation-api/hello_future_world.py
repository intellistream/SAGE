from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.keyby_function import KeyByFunction
from sage.core.api.function.join_function import BaseJoinFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.future_function import FutureFunction


            # # 1. 声明future stream
            # future_stream = env.from_future("feedback_loop")
            
            # # 2. 构建pipeline，使用future stream
            # result = source.connect(future_stream).comap(CombineFunction)
            
            # # 3. 填充future stream，创建反馈边
            # processed_result = result.filter(SomeFilter)
            # processed_result.fill_future(future_stream)


            # future_stream = env.from_future("feedback_loop")
            # # 使用future_stream参与pipeline构建
            # result = source.connect(future_stream).comap(CombineFunction)
            # # 最后填充future
            # result.fill_future(future_stream)