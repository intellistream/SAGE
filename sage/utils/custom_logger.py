import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

class CustomLogger:
    """
    自定义Logger类，支持：
    1. 单次执行中所有Logger共享同一个时间戳文件夹
    2. 为每个对象创建独立的日志文件
    3. 自定义日志路径
    """
    
    # 类级别的共享变量，确保所有实例使用同一个session
    _session_folder: Optional[str] = None
    _base_log_path: str = "logs"
    _session_started: bool = False
    
    @classmethod
    def set_base_log_path(cls, path: str):
        """设置基础日志路径"""
        cls._base_log_path = path
    
    @classmethod
    def start_new_session(cls):
        """开始新的session，生成新的时间戳文件夹"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cls._session_folder = os.path.join(cls._base_log_path, timestamp)
        # 创建文件夹
        Path(cls._session_folder).mkdir(parents=True, exist_ok=True)
        cls._session_started = True
        print(f"Logger session started: {cls._session_folder}")
    
    @classmethod
    def get_session_folder(cls) -> str:
        """获取当前会话的日志文件夹，如果没有则自动创建"""
        if cls._session_folder is None or not cls._session_started:
            cls.start_new_session()
        return cls._session_folder
    
    @classmethod
    def end_session(cls):
        """结束当前session"""
        if cls._session_started:
            print(f"Logger session ended: {cls._session_folder}")
        cls._session_folder = None
        cls._session_started = False
    
    def __init__(self, 
                 object_name: str, 
                 log_level: int = logging.DEBUG,
                 console_output: bool = True,
                 file_output: bool = True):
        """
        初始化自定义Logger
        
        Args:
            object_name: 对象名称，用作logger名称和文件名
            log_level: 日志级别
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
        """
        self.object_name = object_name
        self.logger = logging.getLogger(f"CustomLogger.{object_name}")
        self.logger.setLevel(log_level)
        
        # 清除已有的handlers，避免重复
        self.logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台输出
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 文件输出
        if file_output:
            session_folder = self.get_session_folder()
            log_file_path = os.path.join(session_folder, f"{object_name}.log")
            
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # 不传播到父logger
        self.logger.propagate = False
    
    def debug(self, message: str):
        """Debug级别日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Info级别日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Warning级别日志"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Error级别日志"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str):
        """Critical级别日志"""
        self.logger.critical(message)
    
    def get_log_file_path(self) -> Optional[str]:
        """获取当前对象的日志文件路径"""
        session_folder = self.get_session_folder()
        return os.path.join(session_folder, f"{self.object_name}.log")
    
    @classmethod
    def get_current_session_path(cls) -> Optional[str]:
        """获取当前session的文件夹路径"""
        return cls._session_folder