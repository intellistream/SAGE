# sage/api/execution/env.py

import logging
import inspect
from typing import Optional, Union, Type

from sage.api.function.base import Function as ApiFunction
from sage.api.function.registry import get_function
from sage.api.operator.base import Operator as ApiOperator
from sage.api.operator.registry import get_operator


class StreamingExecutionEnvironment:
    """
    Fl仿照 Flink 的 StreamingExecutionEnvironment，
    负责作业提交、并行度、生命周期管理等。
    """

    def __init__(
        self,
        job_name: str,
        config: dict,
        parallelism: Optional[int] = None,
        use_ray: bool = False,
    ):
        self.job_name = job_name
        self.config = config
        self.parallelism = parallelism or 1
        self.use_ray = use_ray
        self._source_stream: Optional[DataStream] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def from_source(
        self,
        function: Union[str, Type[ApiFunction], ApiFunction],
    ) -> "DataStream":
        """
        定义作业起点，从指定 Function 读取数据。
        :param function: 注册名、Function 子类或实例
        """
        fn = self._create_function(function)
        ds = DataStream(self, fn)
        self._source_stream = ds
        return ds

    def execute(self):
        """
        提交并执行整个流式任务（当前实现为同步递归调用）。
        """
        if self._source_stream is None:
            raise RuntimeError("No source defined; call from_source() first.")
        self.logger.info(f"Executing job '{self.job_name}' "
                         f"(parallelism={self.parallelism}, use_ray={self.use_ray})")
        # 从源头启动执行
        self._source_stream._execute(None)
        self.logger.info(f"Job '{self.job_name}' completed.")

    def _create_function(
        self,
        function: Union[str, Type[ApiFunction], ApiFunction],
    ) -> ApiFunction:
        """
        将名称、类或实例统一为已 open() 的 Function 实例。
        """
        # 1) 名称：从全局注册表获取
        if isinstance(function, str):
            return get_function(function, self.config)
        # 2) 子类：直接实例化
        if inspect.isclass(function) and issubclass(function, ApiFunction):
            fn = function(self.config)
            fn.open()
            return fn
        # 3) 已实例化
        if isinstance(function, ApiFunction):
            function.open()
            return function
        raise TypeError(
            "function must be a registered name, Function subclass, or Function instance"
        )


class DataStream:
    """
    DataStream 表示一条数据流及其下游 Operator 链。
    """

    def __init__(
        self,
        env: StreamingExecutionEnvironment,
        fn: Union[ApiFunction, ApiOperator],
    ):
        self.env = env
        # 如果传入的是 Operator，则直接使用；否则包装成无状态 Operator
        if isinstance(fn, ApiOperator):
            self.op = fn
        else:
            # 默认将 Function 包装到一个 MapOperator
            self.op = get_operator("map", fn, self.env.config)
        self.children: list[DataStream] = []
        self.logger = logging.getLogger(
            f"{self.__class__.__name__}-{self.op.__class__.__name__}"
        )

    def map(
        self,
        function: Union[str, Type[ApiFunction], ApiFunction]
    ) -> "DataStream":
        """
        在流上添加一个 MapOperator，包装指定 Function。
        """
        fn = self.env._create_function(function)
        op = get_operator("map", fn, self.env.config)
        ds = DataStream(self.env, op)
        self.children.append(ds)
        return ds

    def sink(
        self,
        function: Union[str, Type[ApiFunction], ApiFunction]
    ) -> "DataStream":
        """
        在流上添加一个 SinkOperator，包装指定 Function。
        """
        fn = self.env._create_function(function)
        op = get_operator("sink", fn, self.env.config)
        ds = DataStream(self.env, op)
        self.children.append(ds)
        return ds

    def _execute(self, record):
        """
        递归执行当前 Operator 和所有下游子流。
        :param record: 上游传入数据（源头为 None）
        """
        # 调用 Operator.run；它会调用底层 Function.process
        out = self.op.run(record)
        # 统一成列表
        recs = out if isinstance(out, list) else [out]

        for r in recs:
            for child in self.children:
                child._execute(r)

        # 如果是末端（无 children），触发 teardown
        if not self.children:
            try:
                self.op.teardown()
            except AttributeError:
                pass
