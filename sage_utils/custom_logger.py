import logging
import os
import sys
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
    COLOR_RESET = "\033[0m"
    COLOR_DEBUG = "\033[36m"  # 青色
    COLOR_INFO = "\033[32m"   # 绿色
    COLOR_WARNING = "\033[33m" # 黄色
    COLOR_ERROR = "\033[31m"  # 红色
    COLOR_CRITICAL = "\033[35m" # 紫色


    def format(self, record):

        if record.levelno == logging.DEBUG:
            color = self.COLOR_DEBUG
        elif record.levelno == logging.INFO:
            color = self.COLOR_INFO
        elif record.levelno == logging.WARNING:
            color = self.COLOR_WARNING
        elif record.levelno == logging.ERROR:
            color = self.COLOR_ERROR
        elif record.levelno == logging.CRITICAL:
            color = self.COLOR_CRITICAL
        else:
            color = self.COLOR_RESET

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
        formatted_message = f"{timestamp} | {level:<5} | {name} | {pathname}:{lineno} →\n\t {color}{message}{self.COLOR_RESET}\n"

        return formatted_message



class CustomLogger:
    """
    简化的自定义Logger类
    每个Logger产生三份输出：
    1. 对象专用文件：{object_name}.log
    2. 全局时间顺序文件：all_logs.log
    3. 控制台输出
    支持动态调整各输出渠道的日志等级
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
        'WARN': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
        'FATAL': logging.CRITICAL,
    }

    def __init__(self,
                 filename: str,
                 session_folder: str = None,
                 env_name: Optional[str] = None,
                 console_output: Union[bool, str, int] = False,
                 file_output: Union[bool, str, int] = True,
                 global_output: Union[bool, str, int] = True,
                 name: str = None):
        """
        初始化自定义Logger
        
        Args:
            filename: 对象名称，用作logger名称和文件名
            session_folder: session文件夹路径
            console_output: 控制台输出设置
                          - False: 不输出到控制台
                          - True: 输出所有级别到控制台 (相当于 DEBUG)
                          - str/int: 指定日志级别，只输出 >= 该级别的日志
            file_output: 对象专用文件输出设置
                        - False: 不输出到专用文件
                        - True: 输出所有级别到专用文件 (相当于 DEBUG)
                        - str/int: 指定日志级别，只输出 >= 该级别的日志
            global_output: 全局汇总文件输出设置
                          - False: 不输出到全局文件
                          - True: 输出所有级别到全局文件 (相当于 DEBUG)
                          - str/int: 指定日志级别，只输出 >= 该级别的日志
            name: 自定义logger名称，默认使用filename
        """
        self.object_name = filename if name is None else name
        self.filename = filename
        self.env_name = env_name or None
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
        if self.env_name:
            self.session_folder = os.path.join(self.session_folder, self.env_name)

        self.logger = logging.getLogger(f"{self.object_name}")

        # 避免重复初始化同一个logger
        if self.logger.handlers:
            return

        # 提取各输出渠道的日志级别
        self.console_level = self._extract_log_level(console_output, default_level=logging.DEBUG)
        self.file_level = self._extract_log_level(file_output, default_level=logging.DEBUG)
        self.global_level = self._extract_log_level(global_output, default_level=logging.DEBUG)
        
        # 记录输出开关状态
        self.console_enabled = console_output is not False
        self.file_enabled = file_output is not False
        self.global_enabled = global_output is not False
        
        # 设置logger的最低级别（取所有启用输出中的最低级别）
        enabled_levels = []
        if self.console_enabled:
            enabled_levels.append(self.console_level)
        if self.file_enabled:
            enabled_levels.append(self.file_level)
        if self.global_enabled:
            enabled_levels.append(self.global_level)
            
        min_level = min(enabled_levels) if enabled_levels else logging.INFO
        self.logger.setLevel(min_level)

        # 创建统一的自定义格式化器
        formatter = CustomFormatter()

        # 存储handler引用以便动态调整
        self.console_handler = None
        self.file_handler = None
        self.global_handler = None

        # 控制台输出
        if self.console_enabled and self._global_console_debug_enabled:
            self.console_handler = logging.StreamHandler()
            self.console_handler.setLevel(self.console_level)
            self.console_handler.setFormatter(formatter)
            self.logger.addHandler(self.console_handler)

        # 文件输出
        if self.file_enabled or self.global_enabled:
            # 确保session文件夹存在
            Path(self.session_folder).mkdir(parents=True, exist_ok=True)

            # 1. 对象专用日志文件
            if self.file_enabled:
                object_log_file_path = os.path.join(self.session_folder, f"{self.filename}.log")
                log_dir = os.path.dirname(object_log_file_path)
                os.makedirs(log_dir, exist_ok=True)

                self.file_handler = logging.FileHandler(object_log_file_path, encoding='utf-8')
                self.file_handler.setLevel(self.file_level)
                self.file_handler.setFormatter(formatter)
                self.logger.addHandler(self.file_handler)

            # 2. 全局时间顺序日志文件
            if self.global_enabled:
                global_log_file_path = os.path.join(self.session_folder, "all_logs.log")
                log_dir = os.path.dirname(global_log_file_path)
                os.makedirs(log_dir, exist_ok=True)
                
                self.global_handler = logging.FileHandler(global_log_file_path, encoding='utf-8')
                self.global_handler.setLevel(self.global_level)
                self.global_handler.setFormatter(formatter)
                self.logger.addHandler(self.global_handler)

        # 不传播到父logger
        self.logger.propagate = False

    def _extract_log_level(self, output_setting: Union[bool, str, int], default_level: int = logging.DEBUG) -> int:
        """
        从输出设置中提取日志级别
        
        Args:
            output_setting: 输出设置
                          - False: 返回最高级别（不会实际使用，因为不会创建handler）
                          - True: 返回默认级别
                          - str: 日志级别名称，转换为对应的数值
                          - int: 直接返回该数值
            default_level: 当 output_setting 为 True 时使用的默认级别
            
        Returns:
            int: 对应的日志级别数值
            
        Raises:
            ValueError: 当字符串级别名称无效时
            TypeError: 当类型不支持时
        """
        if output_setting is False:
            # 返回最高级别，实际上不会使用因为不会创建handler
            return logging.CRITICAL + 1
        elif output_setting is True:
            return default_level
        elif isinstance(output_setting, str):
            level_str = output_setting.upper()
            if level_str not in self._LEVEL_MAPPING:
                raise ValueError(f"Invalid log level: {output_setting}. "
                               f"Valid levels are: {list(self._LEVEL_MAPPING.keys())}")
            return self._LEVEL_MAPPING[level_str]
        elif isinstance(output_setting, int):
            return output_setting
        else:
            raise TypeError(f"output_setting must be bool, str or int, got {type(output_setting)}")

    def set_console_level(self, level: Union[str, int, bool]):
        """
        动态设置控制台输出级别
        
        Args:
            level: 新的日志级别
                  - False: 禁用控制台输出
                  - True: 启用控制台输出，级别为DEBUG
                  - str/int: 指定具体级别
        """
        old_enabled = self.console_enabled
        new_level = self._extract_log_level(level)
        self.console_enabled = level is not False
        self.console_level = new_level
        
        # 移除现有的控制台handler
        if self.console_handler:
            self.logger.removeHandler(self.console_handler)
            self.console_handler = None
        
        # 如果启用控制台输出，添加新的handler
        if self.console_enabled and self._global_console_debug_enabled:
            self.console_handler = logging.StreamHandler()
            self.console_handler.setLevel(self.console_level)
            self.console_handler.setFormatter(CustomFormatter())
            self.logger.addHandler(self.console_handler)
        
        # 更新logger的最低级别
        self._update_logger_level()
        
        status = "enabled" if self.console_enabled else "disabled"
        level_str = logging.getLevelName(self.console_level) if self.console_enabled else "N/A"
        print(f"Console output {status} with level: {level_str}")

    def set_file_level(self, level: Union[str, int, bool]):
        """
        动态设置对象专用文件输出级别
        
        Args:
            level: 新的日志级别
        """
        old_enabled = self.file_enabled
        new_level = self._extract_log_level(level)
        self.file_enabled = level is not False
        self.file_level = new_level
        
        # 移除现有的文件handler
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler = None
        
        # 如果启用文件输出，添加新的handler
        if self.file_enabled:
            Path(self.session_folder).mkdir(parents=True, exist_ok=True)
            object_log_file_path = os.path.join(self.session_folder, f"{self.filename}.log")
            
            self.file_handler = logging.FileHandler(object_log_file_path, encoding='utf-8')
            self.file_handler.setLevel(self.file_level)
            self.file_handler.setFormatter(CustomFormatter())
            self.logger.addHandler(self.file_handler)
        
        # 更新logger的最低级别
        self._update_logger_level()
        
        status = "enabled" if self.file_enabled else "disabled"
        level_str = logging.getLevelName(self.file_level) if self.file_enabled else "N/A"
        self.info(f"File output {status} with level: {level_str}")

    def set_global_level(self, level: Union[str, int, bool]):
        """
        动态设置全局汇总文件输出级别
        
        Args:
            level: 新的日志级别
        """
        old_enabled = self.global_enabled
        new_level = self._extract_log_level(level)
        self.global_enabled = level is not False
        self.global_level = new_level
        
        # 移除现有的全局handler
        if self.global_handler:
            self.logger.removeHandler(self.global_handler)
            self.global_handler = None
        
        # 如果启用全局输出，添加新的handler
        if self.global_enabled:
            Path(self.session_folder).mkdir(parents=True, exist_ok=True)
            global_log_file_path = os.path.join(self.session_folder, "all_logs.log")
            
            self.global_handler = logging.FileHandler(global_log_file_path, encoding='utf-8')
            self.global_handler.setLevel(self.global_level)
            self.global_handler.setFormatter(CustomFormatter())
            self.logger.addHandler(self.global_handler)
        
        # 更新logger的最低级别
        self._update_logger_level()
        
        status = "enabled" if self.global_enabled else "disabled"
        level_str = logging.getLevelName(self.global_level) if self.global_enabled else "N/A"
        self.info(f"Global output {status} with level: {level_str}")

    def _update_logger_level(self):
        """更新logger的最低级别"""
        enabled_levels = []
        if self.console_enabled:
            enabled_levels.append(self.console_level)
        if self.file_enabled:
            enabled_levels.append(self.file_level)
        if self.global_enabled:
            enabled_levels.append(self.global_level)
            
        min_level = min(enabled_levels) if enabled_levels else logging.INFO
        self.logger.setLevel(min_level)

    def get_current_levels(self) -> dict:
        """
        获取当前各输出渠道的级别设置
        
        Returns:
            dict: 包含各渠道级别信息的字典
        """
        return {
            'console': {
                'enabled': self.console_enabled,
                'level': logging.getLevelName(self.console_level) if self.console_enabled else None,
                'level_num': self.console_level if self.console_enabled else None
            },
            'file': {
                'enabled': self.file_enabled,
                'level': logging.getLevelName(self.file_level) if self.file_enabled else None,
                'level_num': self.file_level if self.file_enabled else None
            },
            'global': {
                'enabled': self.global_enabled,
                'level': logging.getLevelName(self.global_level) if self.global_enabled else None,
                'level_num': self.global_level if self.global_enabled else None
            },
            'logger_min_level': {
                'level': logging.getLevelName(self.logger.level),
                'level_num': self.logger.level
            }
        }

    def print_current_levels(self):
        """打印当前各输出渠道的级别设置"""
        levels = self.get_current_levels()
        print(f"\n=== Logger '{self.object_name}' Current Levels ===")
        for channel, info in levels.items():
            if channel == 'logger_min_level':
                print(f"Logger minimum level: {info['level']} ({info['level_num']})")
            else:
                if info['enabled']:
                    print(f"{channel.capitalize()} output: {info['level']} ({info['level_num']})")
                else:
                    print(f"{channel.capitalize()} output: DISABLED")
        print("=" * 50)

    # ...existing code...

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
                # 如果 exc_info=True，就取当前异常信息元组；否则为 None
                err = sys.exc_info() if exc_info else None
                # 创建一个临时的LogRecord，手动设置调用者信息
                record = self.logger.makeRecord(
                    name=self.logger.name,
                    level=level,
                    fn=pathname,
                    lno=lineno,
                    msg=message,
                    args=(),
                    exc_info=err
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
        return os.path.join(self.session_folder, f"{self.filename}.log")

    def get_global_log_file_path(self) -> str:
        """获取全局日志文件路径"""
        return os.path.join(self.session_folder, "all_logs.log")

    @staticmethod
    def create_session_folder(base_path: str = "logs") -> str:
        """
        创建session文件夹的工具方法, 始终在项目根目录下创建.
        项目根目录被定义为本文件所在目录的上两级目录.
        """
        # 将项目根目录定义为当前文件的上两级目录
        project_root = Path(os.getcwd())  # 获取当前工作目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 将 base_path (默认为 "logs") 置于项目根目录下
        session_folder = project_root / base_path / timestamp
        session_folder.mkdir(parents=True, exist_ok=True)
        return str(session_folder)

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

    def exception(self, param):
        self.error(param)
