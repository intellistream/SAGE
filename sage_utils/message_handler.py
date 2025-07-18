import abc
from typing import Dict, Any, Callable, Optional, Type
from sage_utils.custom_logger import CustomLogger


class MessageHandler(abc.ABC):
    """
    消息处理器基类，支持根据消息类型自动路由
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        """
        初始化消息处理器
        
        Args:
            logger: 日志记录器，如果不提供会创建默认的
        """
        self.logger = logger or CustomLogger(
            filename="MessageHandler",
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING"
        )
        
        # 消息类型到处理函数的映射
        self._handlers: Dict[str, Callable[[Dict[str, Any], tuple], None]] = {}
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认的消息类型处理器"""
        # 子类可以重写此方法来注册自己的处理器
        pass
    
    def register_handler(self, message_type: str, handler: Callable[[Dict[str, Any], tuple], None]):
        """
        注册消息类型处理器
        
        Args:
            message_type: 消息类型字符串
            handler: 处理函数，接收 (message, client_address) 参数
        """
        self._handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")
    
    def unregister_handler(self, message_type: str):
        """
        取消注册消息类型处理器
        
        Args:
            message_type: 消息类型字符串
        """
        if message_type in self._handlers:
            del self._handlers[message_type]
            self.logger.debug(f"Unregistered handler for message type: {message_type}")
    
    def handle_message(self, message: Dict[str, Any], client_address: tuple):
        """
        处理消息的主入口点
        
        Args:
            message: 消息字典，必须包含 "type" 字段
            client_address: 客户端地址
        """
        try:
            # 验证消息格式
            if not isinstance(message, dict):
                self.logger.error(f"Invalid message format from {client_address}: not a dict")
                return
            
            message_type = message.get("type")
            if not message_type:
                self.logger.error(f"Missing 'type' field in message from {client_address}")
                self.handle_invalid_message(message, client_address, "Missing 'type' field")
                return
            
            # 查找并调用对应的处理器
            if message_type in self._handlers:
                self.logger.debug(f"Handling message type '{message_type}' from {client_address}")
                self._handlers[message_type](message, client_address)
            else:
                self.logger.warning(f"No handler registered for message type '{message_type}' from {client_address}")
                self.handle_unknown_message_type(message, client_address)
                
        except Exception as e:
            self.logger.error(f"Error handling message from {client_address}: {e}", exc_info=True)
            self.handle_processing_error(message, client_address, e)
    
    def handle_invalid_message(self, message: Any, client_address: tuple, reason: str):
        """
        处理无效消息
        
        Args:
            message: 无效的消息
            client_address: 客户端地址
            reason: 无效原因
        """
        self.logger.warning(f"Invalid message from {client_address}: {reason}")
        # 子类可以重写此方法来自定义处理逻辑
    
    def handle_unknown_message_type(self, message: Dict[str, Any], client_address: tuple):
        """
        处理未知消息类型
        
        Args:
            message: 消息字典
            client_address: 客户端地址
        """
        message_type = message.get("type", "unknown")
        self.logger.warning(f"Unknown message type '{message_type}' from {client_address}")
        # 子类可以重写此方法来自定义处理逻辑
    
    def handle_processing_error(self, message: Dict[str, Any], client_address: tuple, error: Exception):
        """
        处理消息处理过程中的错误
        
        Args:
            message: 消息字典
            client_address: 客户端地址
            error: 发生的错误
        """
        message_type = message.get("type", "unknown")
        self.logger.error(f"Error processing message type '{message_type}' from {client_address}: {error}")
        # 子类可以重写此方法来自定义错误处理逻辑
    
    def get_registered_types(self) -> list:
        """获取所有已注册的消息类型"""
        return list(self._handlers.keys())
    
    def __call__(self, message: Dict[str, Any], client_address: tuple):
        """使对象可调用，直接转发到 handle_message"""
        self.handle_message(message, client_address)


class DecoratorMessageHandler(MessageHandler):
    """
    支持装饰器注册的消息处理器
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        super().__init__(logger)
    
    def message_handler(self, message_type: str):
        """
        装饰器：注册消息类型处理器
        
        Args:
            message_type: 消息类型字符串
        """
        def decorator(func: Callable[[Dict[str, Any], tuple], None]):
            self.register_handler(message_type, func)
            return func
        return decorator


# 示例具体实现
class DefaultMessageHandler(DecoratorMessageHandler):
    """
    默认的消息处理器实现
    """
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.register_handler("ping", self._handle_ping)
        self.register_handler("status", self._handle_status)
        self.register_handler("shutdown", self._handle_shutdown)
    
    def _handle_ping(self, message: Dict[str, Any], client_address: tuple):
        """处理 ping 消息"""
        self.logger.debug(f"Received ping from {client_address}")
        # 这里可以实现 pong 回复逻辑
    
    def _handle_status(self, message: Dict[str, Any], client_address: tuple):
        """处理状态查询消息"""
        self.logger.debug(f"Received status request from {client_address}")
        # 这里可以实现状态回复逻辑
    
    def _handle_shutdown(self, message: Dict[str, Any], client_address: tuple):
        """处理关闭消息"""
        self.logger.info(f"Received shutdown request from {client_address}")
        # 这里可以实现关闭逻辑
    
    # 使用装饰器注册新的处理器
    @DecoratorMessageHandler.message_handler("custom_task")
    def handle_custom_task(self, message: Dict[str, Any], client_address: tuple):
        """处理自定义任务消息"""
        task_id = message.get("task_id")
        self.logger.info(f"Received custom task {task_id} from {client_address}")
        # 处理自定义任务逻辑