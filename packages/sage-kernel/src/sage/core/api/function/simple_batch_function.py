from typing import Iterator, Any, TYPE_CHECKING, List, Optional, Union, Callable
from sage.core.api.function.base_function import BaseFunction

if TYPE_CHECKING:
    from sage.kernel import TaskContext


class SimpleBatchIteratorFunction(BaseFunction):
    """
    简化的批处理迭代器函数
    
    每次execute调用返回一个数据项，完成后返回None触发停止信号
    """
    
    def __init__(self, data: List[Any], ctx: 'TaskContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.data = data
        self.processed_count = 0
        self.iterator = iter(self.data)
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法 - 每次返回一个数据项"""
        try:
            item = next(self.iterator)
            self.processed_count += 1
            if self.logger:
                self.logger.debug(f"Processing item {self.processed_count}/{len(self.data)}: {item}")
            return item
        except StopIteration:
            if self.logger:
                self.logger.info(f"Batch processing completed: {self.processed_count} items processed")
            # 返回None表示批处理完成，BatchOperator会捕获并发送停止信号
            return None
    
    def get_total_count(self) -> int:
        """返回总数量（可选）"""
        return len(self.data)


class FileBatchIteratorFunction(BaseFunction):
    """
    简化的文件批处理函数
    
    每次execute调用返回文件的一行，完成后返回None触发停止信号
    """
    
    def __init__(self, file_path: str, encoding: str = 'utf-8', ctx: 'TaskContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.file_path = file_path
        self.encoding = encoding
        self._cached_total_count: Optional[int] = None
        self.processed_count = 0
        self._file_iterator = None
        self._file_handle = None
    
    def _get_file_iterator(self):
        """懒加载文件迭代器"""
        if self._file_iterator is None:
            try:
                self._file_handle = open(self.file_path, 'r', encoding=self.encoding)
                self._file_iterator = iter(self._file_handle)
                if self.logger:
                    self.logger.info(f"Started file batch processing: {self.file_path}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to open file {self.file_path}: {e}")
                self._file_iterator = iter([])  # 空迭代器
        return self._file_iterator
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法 - 每次返回文件的一行"""
        try:
            iterator = self._get_file_iterator()
            line = next(iterator)
            self.processed_count += 1
            line_content = line.strip()
            
            if self.logger:
                self.logger.debug(f"Processing line {self.processed_count}: {line_content[:50]}...")
            
            return line_content
            
        except StopIteration:
            if self.logger:
                self.logger.info(f"File batch processing completed: {self.processed_count} lines processed")
            
            # 关闭文件句柄
            if self._file_handle:
                self._file_handle.close()
                self._file_handle = None
                self._file_iterator = None
            
            # 返回None表示批处理完成
            return None
    
    def get_total_count(self) -> int:
        """返回文件行数（可选）"""
        if self._cached_total_count is None:
            try:
                with open(self.file_path, 'r', encoding=self.encoding) as f:
                    self._cached_total_count = sum(1 for _ in f)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to count lines in {self.file_path}: {e}")
                self._cached_total_count = 0
        return self._cached_total_count


class RangeBatchIteratorFunction(BaseFunction):
    """
    简化的范围批处理函数
    
    每次execute调用返回范围中的一个数字，完成后返回None触发停止信号
    """
    
    def __init__(self, start: int, end: int, step: int = 1, ctx: 'TaskContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.start = start
        self.end = end
        self.step = step
        self.processed_count = 0
        self.iterator = iter(range(start, end, step))
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法 - 每次返回范围中的一个数字"""
        try:
            value = next(self.iterator)
            self.processed_count += 1
            total_count = self.get_total_count()
            
            if self.logger:
                self.logger.debug(f"Processing range item {self.processed_count}/{total_count}: {value}")
            
            return value
            
        except StopIteration:
            if self.logger:
                self.logger.info(f"Range batch processing completed: {self.processed_count} items processed")
            # 返回None表示批处理完成
            return None
    
    def get_total_count(self) -> int:
        """返回范围大小（可选）"""
        return max(0, (self.end - self.start + self.step - 1) // self.step)


class GeneratorBatchIteratorFunction(BaseFunction):
    """
    简化的生成器批处理函数
    
    每次execute调用返回生成器的一个项目，完成后返回None触发停止信号
    """
    
    def __init__(self, generator_func: Callable[[], Iterator[Any]], 
                 total_count: Optional[int] = None, ctx: 'TaskContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.generator_func = generator_func
        self.total_count = total_count
        self.processed_count = 0
        self._generator = None
    
    def _get_generator(self):
        """懒加载生成器"""
        if self._generator is None:
            try:
                self._generator = iter(self.generator_func())
                if self.logger:
                    total_info = f" ({self.total_count} items)" if self.total_count else ""
                    self.logger.info(f"Started generator batch processing{total_info}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to create generator: {e}")
                self._generator = iter([])  # 空迭代器
        return self._generator
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法 - 每次返回生成器的一个项目"""
        try:
            generator = self._get_generator()
            item = next(generator)
            self.processed_count += 1
            
            if self.logger:
                progress_info = f"{self.processed_count}/{self.total_count}" if self.total_count else str(self.processed_count)
                self.logger.debug(f"Processing generator item {progress_info}: {item}")
            
            return item
            
        except StopIteration:
            if self.logger:
                self.logger.info(f"Generator batch processing completed: {self.processed_count} items processed")
            # 返回None表示批处理完成
            return None
    
    def get_total_count(self) -> Optional[int]:
        """返回总数量（如果已知）"""
        return self.total_count


class IterableBatchIteratorFunction(BaseFunction):
    """
    通用的可迭代对象批处理函数
    
    每次execute调用返回可迭代对象的一个项目，完成后返回None触发停止信号
    """
    
    def __init__(self, iterable: Any, total_count: Optional[int] = None, 
                 ctx: 'TaskContext' = None, **kwargs):
        super().__init__(ctx, **kwargs)
        self.iterable = iterable
        self.total_count = total_count
        self.processed_count = 0
        self._iterator = None
    
    def _get_iterator(self):
        """懒加载迭代器"""
        if self._iterator is None:
            try:
                self._iterator = iter(self.iterable)
                calculated_total = self.get_total_count()
                if self.logger:
                    total_info = f" ({calculated_total} items)" if calculated_total else ""
                    self.logger.info(f"Started iterable batch processing{total_info}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to create iterator: {e}")
                self._iterator = iter([])  # 空迭代器
        return self._iterator
    
    def execute(self, data: Any = None):
        """批处理函数的执行方法 - 每次返回可迭代对象的一个项目"""
        try:
            iterator = self._get_iterator()
            item = next(iterator)
            self.processed_count += 1
            calculated_total = self.get_total_count()
            
            if self.logger:
                progress_info = f"{self.processed_count}/{calculated_total}" if calculated_total else str(self.processed_count)
                self.logger.debug(f"Processing iterable item {progress_info}: {item}")
            
            return item
            
        except StopIteration:
            if self.logger:
                self.logger.info(f"Iterable batch processing completed: {self.processed_count} items processed")
            # 返回None表示批处理完成
            return None
    
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


# 为了兼容性，保留旧的函数名
SimpleBatchFunction = SimpleBatchIteratorFunction
FileBatchFunction = FileBatchIteratorFunction
NumberRangeBatchFunction = RangeBatchIteratorFunction
CustomDataBatchFunction = GeneratorBatchIteratorFunction
