"""
SAGE Flow Stream Processing API

提供高层次的Python流处理接口，通过pybind11绑定调用C++核心实现。
所有DSL操作直接重定向到C++ DataStream，无Python fallback模拟。
确保纯C++后端执行，性能优化和内存安全。

示例：
    from sageflow import Stream
    data = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
    result = (Stream.from_list(data)
              .map(lambda x: {**x, "doubled": x["value"] * 2})
              .filter(lambda x: x["value"] > 15)
              .sink("file://output.txt")
              .execute())
    print(result)  # 处理后的数据列表
"""

from typing import Callable, Any, Optional, List, Union
try:
    from . import DataStream  # C++绑定DataStream，必须可用
    CPP_AVAILABLE = True
except (ImportError, NameError):
    CPP_AVAILABLE = False
    DataStream = None
    raise ImportError("SAGE Flow C++扩展不可用。请确保已正确构建和安装C++核心。")

class Stream:
    """
    流处理类，提供Pythonic DSL API，直接调用C++实现。

    支持链式操作：map、filter、join、aggregate、sink。
    sink()返回self实现fluent API，execute()触发C++执行。
    无Python模拟，所有操作通过pybind11调用C++后端。

    Args:
        cpp_stream: 可选的底层C++ DataStream实例。

    Raises:
        ImportError: C++扩展不可用时。
    """

    def __init__(self, cpp_stream: Optional[Any] = None) -> None:
        """
        初始化Stream，使用C++ DataStream实例。

        Args:
            cpp_stream: C++ DataStream实例。
        """
        if not CPP_AVAILABLE:
            raise ImportError("SAGE Flow需要C++扩展支持。")
        self._cpp_stream = cpp_stream or DataStream()

    @classmethod
    def from_list(cls, iterable: List[Any]) -> 'Stream':
        """
        从列表创建Stream。

        Args:
            iterable: 输入数据列表（dict/list等）。

        Returns:
            新Stream实例。

        示例:
            stream = Stream.from_list([{"id": 1}, {"id": 2}])
        """
        s = cls()
        s._cpp_stream.from_list(iterable)
        return s

    @classmethod
    def from_numpy(cls, array: Any) -> 'Stream':  # type: ignore
        """
        从NumPy数组创建Stream。

        Args:
            array: NumPy数组。

        Returns:
            新Stream实例。

        示例:
            import numpy as np
            stream = Stream.from_numpy(np.array([1.0, 2.0]))
        """
        s = cls()
        s._cpp_stream.from_numpy(array)
        return s

    def map(self, func: Callable[[Any], Any]) -> 'Stream':
        """
        应用map转换。

        Args:
            func: 转换函数。

        Returns:
            新Stream。

        示例:
            stream.map(lambda x: x["value"] * 2)
        """
        new_s = Stream(self._cpp_stream.map(func))
        return new_s

    def filter(self, func: Callable[[Any], bool]) -> 'Stream':
        """
        应用filter。

        Args:
            func: 过滤函数。

        Returns:
            新Stream。

        示例:
            stream.filter(lambda x: x["active"])
        """
        new_s = Stream(self._cpp_stream.filter(func))
        return new_s

    def join(self, other_stream: 'Stream', key_func: Callable[[Any], Any],
             join_func: Callable[[Any, Any], Any]) -> 'Stream':
        """
        Join操作。

        Args:
            other_stream: 另一个Stream。
            key_func: 键函数。
            join_func: 连接函数。

        Returns:
            新Stream。

        示例:
            def key(x): return x["id"]
            def join(a, b): return {**a, **b}
            stream.join(other, key, join)
        """
        new_s = Stream(self._cpp_stream.join(other_stream._cpp_stream, key_func, join_func))
        return new_s

    def aggregate(self, key_func: Callable[[Any], Any],
                  agg_func: Callable[[List[Any]], Any]) -> 'Stream':
        """
        聚合操作。

        Args:
            key_func: 键函数。
            agg_func: 聚合函数。

        Returns:
            新Stream。

        示例:
            def key(x): return x["group"]
            def agg(group): return {"sum": sum(g["val"] for g in group)}
            stream.aggregate(key, agg)
        """
        new_s = Stream(self._cpp_stream.aggregate(key_func, agg_func))
        return new_s

    def sink(self, sink_uri: str) -> 'Stream':
        """
        添加sink，返回self支持链式。

        支持"file://path.txt"、"print://"。

        Args:
            sink_uri: Sink URI。

        Returns:
            self。

        示例:
            stream.sink("file://results.txt")
        """
        self._cpp_stream.sink(sink_uri)
        return self

    def config(self, parallelism: Optional[int] = None, lazy: Optional[bool] = None) -> 'Stream':
        """
        配置参数。

        Args:
            parallelism: 并行度。
            lazy: 懒惰模式。

        Returns:
            self。
        """
        if parallelism is not None:
            self._cpp_stream.config_parallelism(parallelism)
        if lazy is not None:
            self._cpp_stream.config_lazy(lazy)
        return self

    def execute(self) -> Union[List[Any], Any]:  # type: ignore
        """
        执行流，返回结果。

        触发C++执行并收集结果。

        Returns:
            结果列表。

        Raises:
            RuntimeError: 执行错误。

        示例:
            result = stream.execute()
        """
        try:
            self._cpp_stream.execute()
            raw = self._cpp_stream.collect()
            return list(raw) if raw else []
        except Exception as e:
            raise RuntimeError(f"C++执行失败: {e}")