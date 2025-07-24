from typing import Iterator, Any, TYPE_CHECKING, List, Optional, Union, Callable
from sage_core.function.base_function import BaseFunction

if TYPE_CHECKING:
    from sage_runtime.runtime_context import RuntimeContext


class SimpleBatchIteratorFunction(BaseFunction):
    """
    简化的批处理迭代器函数
    
    只需要提供数据迭代器，不需要复杂的状态管理
    """
    
    def __init__(self, data: List[Any], ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.data = data
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法（为了满足BaseFunction抽象方法）"""
        # 对于简化的批处理函数，execute方法不被直接调用
        # 实际的数据处理通过get_data_iterator完成
        return data
    
    def get_data_iterator(self) -> Iterator[Any]:
        """返回数据迭代器"""
        return iter(self.data)
    
    def get_total_count(self) -> int:
        """返回总数量（可选）"""
        return len(self.data)


class FileBatchIteratorFunction(BaseFunction):
    """
    简化的文件批处理函数
    
    逐行迭代文件内容
    """
    
    def __init__(self, file_path: str, encoding: str = 'utf-8', ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.file_path = file_path
        self.encoding = encoding
        self._cached_total_count: Optional[int] = None
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法（为了满足BaseFunction抽象方法）"""
        return data
    
    def get_data_iterator(self) -> Iterator[Any]:
        """返回文件行迭代器"""
        try:
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                for line in f:
                    yield line.strip()
        except Exception as e:
            self.logger.error(f"Failed to read file {self.file_path}: {e}")
            return iter([])
    
    def get_total_count(self) -> int:
        """返回文件行数（可选）"""
        if self._cached_total_count is None:
            try:
                with open(self.file_path, 'r', encoding=self.encoding) as f:
                    self._cached_total_count = sum(1 for _ in f)
            except Exception as e:
                self.logger.error(f"Failed to count lines in {self.file_path}: {e}")
                self._cached_total_count = 0
        return self._cached_total_count


class RangeBatchIteratorFunction(BaseFunction):
    """
    简化的范围批处理函数
    
    生成指定范围的数字序列
    """
    
    def __init__(self, start: int, end: int, step: int = 1, ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.start = start
        self.end = end
        self.step = step
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法（为了满足BaseFunction抽象方法）"""
        return data
    
    def get_data_iterator(self) -> Iterator[Any]:
        """返回范围迭代器"""
        return iter(range(self.start, self.end, self.step))
    
    def get_total_count(self) -> int:
        """返回范围大小（可选）"""
        return max(0, (self.end - self.start + self.step - 1) // self.step)


class GeneratorBatchIteratorFunction(BaseFunction):
    """
    简化的生成器批处理函数
    
    包装用户提供的生成器函数
    """
    
    def __init__(self, generator_func: Callable[[], Iterator[Any]], 
                 total_count: Optional[int] = None, ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.generator_func = generator_func
        self.total_count = total_count
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法（为了满足BaseFunction抽象方法）"""
        return data
    
    def get_data_iterator(self) -> Iterator[Any]:
        """返回生成器迭代器"""
        return self.generator_func()
    
    def get_total_count(self) -> Optional[int]:
        """返回总数量（如果已知）"""
        return self.total_count


class IterableBatchIteratorFunction(BaseFunction):
    """
    通用的可迭代对象批处理函数
    
    可以处理任何实现了__iter__的对象
    """
    
    def __init__(self, iterable: Any, total_count: Optional[int] = None, 
                 ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.iterable = iterable
        self.total_count = total_count
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法（为了满足BaseFunction抽象方法）"""
        return data
    
    def get_data_iterator(self) -> Iterator[Any]:
        """返回可迭代对象的迭代器"""
        return iter(self.iterable)
    
    def get_total_count(self) -> Optional[int]:
        """返回总数量（如果已知）"""
        if self.total_count is not None:
            return self.total_count
        
        # 尝试获取长度
        try:
            return len(self.iterable)
        except (TypeError, AttributeError):
            # 如果不支持len()，返回None
            return None
        except (TypeError, AttributeError):
            return None


# 为了兼容性，保留旧的函数名
SimpleBatchFunction = SimpleBatchIteratorFunction
FileBatchFunction = FileBatchIteratorFunction
NumberRangeBatchFunction = RangeBatchIteratorFunction
CustomDataBatchFunction = GeneratorBatchIteratorFunction
