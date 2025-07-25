from abc import ABC, abstractmethod
from typing import Type, List, Tuple, Any, TYPE_CHECKING, Union, Optional, Iterator
from core.function.base_function import BaseFunction
from core.function.source_function import StopSignal
from utils.custom_logger import CustomLogger

if TYPE_CHECKING:
    from runtime.runtime_context import RuntimeContext

class BatchFunction(BaseFunction):
    """
    批处理函数基类 - 预定义批次大小的数据生产者
    
    BatchFunction允许用户预先定义要处理的记录数量，
    并在处理完所有记录后由operator发送停止信号。
    这提供了更友好的用户接口，用户不需要手动管理停止逻辑。
    """

    def __init__(self, *args, **kwargs):
        self._total_count: Optional[int] = None
        self._current_count: int = 0
        self._data_source: Optional[Iterator] = None
        self._is_finished: bool = False

    @abstractmethod
    def get_total_count(self) -> int:
        """
        获取批处理的总记录数
        
        子类必须实现此方法来声明要处理的记录总数
        
        Returns:
            int: 总记录数
        """
        pass

    @abstractmethod
    def get_data_source(self) -> Iterator[Any]:
        """
        获取数据源迭代器
        
        子类必须实现此方法来提供数据源
        
        Returns:
            Iterator[Any]: 数据源迭代器
        """
        pass

    def initialize(self):
        """
        初始化批处理函数
        """
        if self._total_count is None:
            self._total_count = self.get_total_count()
            self.logger.info(f"Batch function {self.name} initialized with {self._total_count} total records")
        
        if self._data_source is None:
            self._data_source = self.get_data_source()

    def execute(self) -> Any:
        """
        执行批处理函数逻辑
        
        Returns:
            Any: 生产的数据，如果已完成则返回None
        """
        # 延迟初始化，确保在运行时才获取数据源和总数
        if self._total_count is None or self._data_source is None:
            self.initialize()
        
        # 如果已经完成，返回None
        if self._is_finished:
            return None
        
        try:
            # 尝试获取下一个数据项
            data = next(self._data_source)
            self._current_count += 1
            
            self.logger.debug(f"Batch function {self.name} processed {self._current_count}/{self._total_count} records")
            
            # 检查是否已完成所有记录
            if self._current_count >= self._total_count:
                self._is_finished = True
                self.logger.info(f"Batch function {self.name} completed all {self._total_count} records")
            
            return data
            
        except StopIteration:
            # 数据源耗尽
            self._is_finished = True
            self.logger.info(f"Batch function {self.name} data source exhausted after {self._current_count} records")
            return None

    def is_finished(self) -> bool:
        """
        检查批处理是否已完成
        
        Returns:
            bool: 是否已完成
        """
        return self._is_finished

    def get_progress(self) -> Tuple[int, int]:
        """
        获取当前进度
        
        Returns:
            Tuple[int, int]: (当前处理数量, 总数量)
        """
        total = self._total_count if self._total_count is not None else 0
        return self._current_count, total

    def get_completion_rate(self) -> float:
        """
        获取完成率
        
        Returns:
            float: 完成率 (0.0 到 1.0)
        """
        if self._total_count is None or self._total_count == 0:
            return 0.0
        return min(self._current_count / self._total_count, 1.0)

    def reset(self):
        """
        重置批处理状态
        """
        self._current_count = 0
        self._is_finished = False
        self._data_source = None
        self.logger.info(f"Batch function {self.name} reset")


class SimpleBatchFunction(BatchFunction):
    """
    简单批处理函数实现
    
    用于演示和测试的简单批处理函数，
    从给定的数据列表中逐个返回数据。
    """

    def __init__(self, data: List[Any], ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self._data = data

    def get_total_count(self) -> int:
        return len(self._data)

    def get_data_source(self) -> Iterator[Any]:
        return iter(self._data)


class FileBatchFunction(BatchFunction):
    """
    文件批处理函数
    
    从文件中逐行读取数据的批处理函数
    """

    def __init__(self, file_path: str, encoding: str = 'utf-8', ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self._file_path = file_path
        self._encoding = encoding
        self._cached_total_count: Optional[int] = None

    def get_total_count(self) -> int:
        if self._cached_total_count is None:
            try:
                with open(self._file_path, 'r', encoding=self._encoding) as f:
                    self._cached_total_count = sum(1 for _ in f)
            except Exception as e:
                self.logger.error(f"Failed to count lines in {self._file_path}: {e}")
                self._cached_total_count = 0
        return self._cached_total_count

    def get_data_source(self) -> Iterator[Any]:
        try:
            with open(self._file_path, 'r', encoding=self._encoding) as f:
                for line in f:
                    yield line.strip()
        except Exception as e:
            self.logger.error(f"Failed to read file {self._file_path}: {e}")
            return iter([])


class NumberRangeBatchFunction(BatchFunction):
    """
    数字范围批处理函数
    
    生成指定范围内的数字序列
    """
    
    def __init__(self, start: int, end: int, step: int = 1, ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.start = start
        self.end = end
        self.step = step
    
    def get_total_count(self) -> int:
        return max(0, (self.end - self.start + self.step - 1) // self.step)
    
    def get_data_source(self) -> Iterator[Any]:
        return iter(range(self.start, self.end, self.step))


class CustomDataBatchFunction(BatchFunction):
    """
    自定义数据批处理函数
    
    处理用户提供的自定义数据生成逻辑
    """
    
    def __init__(self, data_generator_func: callable, total_count: int, ctx: 'RuntimeContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.data_generator_func = data_generator_func
        self.total_count = total_count
    
    def get_total_count(self) -> int:
        return self.total_count
    
    def get_data_source(self) -> Iterator[Any]:
        return self.data_generator_func()
