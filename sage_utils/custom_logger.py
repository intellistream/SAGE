import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Union, Optional
import threading
import inspect

class CustomFormatter(logging.Formatter):
    """
    自定义格式化器，合并IDE格式和两行格式：
    第一行：时间 | 级别 | 对象名 | 文件路径:行号
    第二行：	→ 日志消息
    第三行： 留空
    """

    def format(self, record):
        # 第一行：时间 | 级别 | 对象名 | 文件路径:行号
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        level = record.levelname
        name = record.name
        pathname = record.pathname
        lineno = record.lineno
        
        # 第二行：→ 消息内容
        message = record.getMessage()
        
        # 如果有异常信息，添加到消息后面
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = message + '\n' + record.exc_text
        if record.stack_info:
            message = message + '\n' + self.formatStack(record.stack_info)
        
        # 组合格式：既美观又支持IDE点击
        formatted_message = f"{timestamp} | {level:<5} | {name} |\n\t {pathname}:{lineno}\n\t→ {message}\n"
        
        return formatted_message

class CustomLogger:
    """
    简化的自定义Logger类
    每个Logger产生两份输出文件：
    1. 对象专用文件：{object_name}.log
    2. 全局时间顺序文件：all_logs.log
    支持自动使用默认session_folder
    """
    # 类级别的默认session管理
    _default_session_folder: Optional[str] = None
    _lock = threading.Lock()
    # 全局console debug开关
    _global_console_debug_enabled: bool = True
    # 日志级别映射
    _LEVEL_MAPPING = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,  # 别名
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.CRITICAL,  # 别名
    }
    
    def __init__(self, 
                 object_name: str,
                 session_folder: str = None,
                 console_output: Union[bool, str, int] = True,
                 file_output: Union[bool, str, int] = True):
        """
        初始化自定义Logger
        
        Args:
            object_name: 对象名称，用作logger名称和文件名
            session_folder: session文件夹路径
            console_output: 控制台输出设置
                          - False: 不输出到控制台
                          - True: 输出所有级别到控制台 (相当于 DEBUG)
                          - str/int: 指定日志级别，只输出 >= 该级别的日志
            file_output: 文件输出设置
                        - False: 不输出到文件
                        - True: 输出所有级别到文件 (相当于 DEBUG)
                        - str/int: 指定日志级别，只输出 >= 该级别的日志
        """
        self.object_name = object_name
        # 处理session_folder：空字符串检查和默认值处理
        if not session_folder:  # None 或空字符串
            if self._default_session_folder is None:
                # 如果没有默认session，创建一个新的
                with self._lock:
                    if self._default_session_folder is None:
                        self._default_session_folder = self.create_session_folder()
            self.session_folder = self._default_session_folder
        else:
            self.session_folder = session_folder
            # 如果这是第一次设置session_folder，将其设为默认值
            if self._default_session_folder is None:
                self.set_default_session_folder(session_folder)
        self.logger = logging.getLogger(f"{object_name}")
        
        # 避免重复初始化同一个logger
        if self.logger.handlers:
            return
            
        # Logger本身设置为最低级别，让handler控制过滤
        self.logger.setLevel(logging.DEBUG)
        
        # 创建统一的自定义格式化器
        formatter = CustomFormatter()
        
        # 处理控制台输出
        console_level = self._parse_output_level(console_output)
        if console_level is not None and self._global_console_debug_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(console_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 处理文件输出
        file_level = self._parse_output_level(file_output)
        if file_level is not None:
            # 确保session文件夹存在
            Path(self.session_folder).mkdir(parents=True, exist_ok=True)
            
            # 1. 对象专用日志文件
            object_log_file_path = os.path.join(self.session_folder, f"{object_name}.log")
            object_file_handler = logging.FileHandler(object_log_file_path, encoding='utf-8')
            object_file_handler.setLevel(file_level)
            object_file_handler.setFormatter(formatter)
            self.logger.addHandler(object_file_handler)
            
            # 2. 全局时间顺序日志文件
            global_log_file_path = os.path.join(self.session_folder, "all_logs.log")
            global_file_handler = logging.FileHandler(global_log_file_path, encoding='utf-8')
            global_file_handler.setLevel(file_level)
            global_file_handler.setFormatter(formatter)
            self.logger.addHandler(global_file_handler)
        
        # 不传播到父logger
        self.logger.propagate = False
    
    def _parse_output_level(self, output_setting: Union[bool, str, int]) -> Optional[int]:
        """
        解析输出级别设置
        
        Args:
            output_setting: 输出设置 (False/True/str/int)
            
        Returns:
            日志级别数值，如果为False则返回None
        """
        if output_setting is False:
            return None
        elif output_setting is True:
            return logging.DEBUG  # True表示输出所有级别
        elif isinstance(output_setting, str):
            level_str = output_setting.upper()
            if level_str not in self._LEVEL_MAPPING:
                raise ValueError(f"Invalid log level: {output_setting}. "
                               f"Valid levels are: {list(self._LEVEL_MAPPING.keys())}")
            return self._LEVEL_MAPPING[level_str]
        elif isinstance(output_setting, int):
            return output_setting
        else:
            raise TypeError(f"Output setting must be bool, str or int, got {type(output_setting)}")
    
    def _log_with_caller_info(self, level: int, message: str, exc_info: bool = False):
        """
        使用调用者信息记录日志，而不是CustomLogger的信息
        """
        # 获取调用栈，跳过当前方法和调用的debug/info/等方法
        frame = inspect.currentframe()
        try:
            # 跳过 _log_with_caller_info -> debug/info/warning/error -> 实际调用位置
            caller_frame = frame.f_back.f_back
            if caller_frame:
                pathname = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno
                
                # 创建一个临时的LogRecord，手动设置调用者信息
                record = self.logger.makeRecord(
                    name=self.logger.name,
                    level=level,
                    fn=pathname,
                    lno=lineno,
                    msg=message,
                    args=(),
                    exc_info=exc_info if exc_info else None
                )
                
                # 直接调用handlers处理记录
                self.logger.handle(record)
            else:
                # 回退到普通logging
                self.logger.log(level, message, exc_info=exc_info)
        finally:
            del frame
    
    def debug(self, message: str):
        """Debug级别日志"""
        self._log_with_caller_info(logging.DEBUG, message)
    
    def info(self, message: str):
        """Info级别日志"""
        self._log_with_caller_info(logging.INFO, message)
    
    def warning(self, message: str):
        """Warning级别日志"""
        self._log_with_caller_info(logging.WARNING, message)
    
    def error(self, message: str, exc_info: bool = False):
        """Error级别日志"""
        self._log_with_caller_info(logging.ERROR, message, exc_info)
    
    def critical(self, message: str):
        """Critical级别日志"""
        self._log_with_caller_info(logging.CRITICAL, message)
    
    def get_log_file_path(self) -> str:
        """获取当前对象的日志文件路径"""
        return os.path.join(self.session_folder, f"{self.object_name}.log")
    
    def get_global_log_file_path(self) -> str:
        """获取全局日志文件路径"""
        return os.path.join(self.session_folder, "all_logs.log")
    
    @staticmethod
    def create_session_folder(base_path: str = "logs") -> str:
        """创建session文件夹的工具方法"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(base_path, timestamp)
        Path(session_folder).mkdir(parents=True, exist_ok=True)
        return session_folder
    
    @classmethod
    def get_available_levels(cls) -> list:
        """获取所有可用的日志级别"""
        return list(cls._LEVEL_MAPPING.keys())
    
    @classmethod
    def set_default_session_folder(cls, session_folder: str):
        """设置默认的session文件夹"""
        with cls._lock:
            cls._default_session_folder = session_folder
            Path(session_folder).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_session_folder(cls) -> Optional[str]:
        if cls._default_session_folder is None:
            # 如果没有设置默认session文件夹，创建一个新的
            cls._default_session_folder = cls.create_session_folder()
        """获取默认的session文件夹"""
        return cls._default_session_folder
    
    @classmethod
    def reset_default_session(cls):
        """重置默认session（用于测试或重新开始）"""
        with cls._lock:
            cls._default_session_folder = None

    @classmethod
    def disable_global_console_debug(cls):
        """全局禁用所有console debug输出"""
        with cls._lock:
            cls._global_console_debug_enabled = False
    
    @classmethod
    def enable_global_console_debug(cls):
        """全局启用所有console debug输出"""
        with cls._lock:
            cls._global_console_debug_enabled = True

    @classmethod
    def is_global_console_debug_enabled(cls) -> bool:
        """检查全局console debug是否启用"""
        return cls._global_console_debug_enabled