from typing import Any, Callable, Union, Iterable, Optional

from sage_core.function.flatmap_function import FlatMapFunction





class WordSplitFunction(FlatMapFunction):
    """
    示例：文本分词FlatMap函数
    """
    
    def __init__(self, delimiter: str = " ", **kwargs):
        super().__init__(**kwargs)
        self.delimiter = delimiter
        self.logger.debug(f"WordSplitFunction initialized with delimiter: '{delimiter}'")

    def execute(self, raw_data) -> Optional[Iterable[Any]]:
        """
        将文本数据分割成单词
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            Optional[Iterable[Any]]: 分割后的单词列表
        """
        try:
            # 获取文本内容
            if hasattr(raw_data, 'data'):
                text = raw_data
            elif isinstance(raw_data, str):
                text = raw_data
            else:
                text = str(raw_data)
            
            # 分割文本
            words = text.split(self.delimiter)
            # 过滤空字符串
            words = [word.strip() for word in words if word.strip()]
            
            self.logger.debug(f"Split '{text}' into {len(words)} words")
            return words
        except Exception as e:
            self.logger.error(f"Error splitting text for data {raw_data}: {e}", exc_info=True)
            return None