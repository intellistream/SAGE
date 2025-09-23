import time
from pathlib import Path
from time import sleep
import socket
import json
import logging
from typing import Optional, Union
from sage.core.api.function.source_function import SourceFunction


class FileSource(SourceFunction):
    """
    A source rag that reads a file line by line and returns each line as a string.

    Input: None (reads directly from a file located at the specified `data_path`).
    Output: A Data object containing the next line of the file content.

    Attributes:
        config: Configuration dictionary containing various settings, including the file path.
        data_path: The path to the file to be read.
        file_pos: Tracks the current position in the file for sequential reading.
    """

    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        self.config = config
        self.data_path = self.resolve_data_path(
            config["data_path"]
        )  # → project_root/data/sample/question.txt
        self.file_pos = 0  # Track the file read position
        self.loop_reading = config.get(
            "loop_reading", False
        )  # Whether to restart from beginning when EOF reached

    def resolve_data_path(self, path: str | Path) -> Path:
        """
        传入相对路径则返回相对于项目根目录的绝对路径（默认假设项目根目录含有 'data/' 子目录），
        传入绝对路径则直接返回。
        """
        import os

        p = Path(path)
        if p.is_absolute():
            return p
        # 假设调用时 cwd 是项目的某个子目录，项目根为“当前工作目录的祖父目录”
        project_root = Path(os.getcwd()).resolve()
        return project_root / p

    def execute(self) -> str:
        """
        Reads the next line from the file and returns it as a string.

        :return: A Data object containing the next line of the file content.
        """
        try:
            while True:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    f.seek(self.file_pos)  # Move to the last read position
                    line = f.readline()
                    self.file_pos = f.tell()  # Update the new position
                    if line:
                        self.logger.info(
                            f"\033[32m[ {self.__class__.__name__}]: Read query: {line.strip()}\033[0m "
                        )
                        return line.strip()  # Return non-empty lines
                    else:
                        if self.loop_reading:
                            self.logger.info(
                                f"\033[33m[ {self.__class__.__name__}]: Reached end of file, restarting from beginning.\033[0m "
                            )
                            self.file_pos = 0  # Reset to beginning of file
                            continue
                        else:
                            self.logger.info(
                                f"\033[33m[ {self.__class__.__name__}]: Reached end of file, maintaining position.\033[0m "
                            )
                            # Reset position if end of file is reached (optional)
                            time.sleep(2)
                            continue
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.data_path}")
        except Exception as e:
            self.logger.error(f"Error reading file '{self.data_path}': {e}")




class SocketSource(SourceFunction):
    """
    从网络套接字读取数据的源函数，支持多机分布式环境
    
    配置参数:
    - host: 服务器主机名或IP地址
    - port: 服务器端口号
    - protocol: 协议类型 (tcp/udp)
    - reconnect: 连接断开时是否自动重连 (默认True)
    - reconnect_interval: 重连间隔秒数 (默认5秒)
    - load_balancing: 是否启用负载均衡 (默认False)
    - client_id: 客户端唯一标识符 (用于负载均衡)
    - buffer_size: 接收缓冲区大小 (默认1024字节)
    - timeout: 套接字超时时间 (默认1秒)
    - delimiter: 消息分隔符 (默认换行符)
    - encoding: 数据编码 (默认utf-8)
    """

    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", 8888)
        self.protocol = self.config.get("protocol", "tcp").lower()
        self.reconnect = self.config.get("reconnect", True)
        self.reconnect_interval = self.config.get("reconnect_interval", 5)
        self.load_balancing = self.config.get("load_balancing", False)
        self.client_id = self.config.get("client_id", socket.gethostname())
        self.buffer_size = self.config.get("buffer_size", 1024)
        self.timeout = self.config.get("timeout", 3)
        self.delimiter = self.config.get("delimiter", "\n").encode()
        self.encoding = self.config.get("encoding", "utf-8")
        
        self.socket = None
        self.buffer = b""
        self.last_connect_attempt = 0
        self.is_connected = False
      
        
        # 初始化连接
        self._initialize_connection()

    def _initialize_connection(self):
        """初始化套接字连接"""
        try:
            if self.protocol == "tcp":
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self._connect_tcp()
            elif self.protocol == "udp":
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket.settimeout(self.timeout)
                self.is_connected = True  # UDP是无连接的
            else:
                raise ValueError(f"不支持的协议类型: {self.protocol}")
        except Exception as e:
            self.logger.error(f"初始化连接失败: {e}")
            self.is_connected = False

    def _connect_tcp(self):
        """建立TCP连接"""
        try:
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            self.logger.info(f"成功连接到 {self.host}:{self.port} (TCP)")
            
            # 发送客户端ID用于负载均衡
            if self.load_balancing:
                self._send_client_id()
        except socket.error as e:
            self.logger.error(f"连接失败: {e}")
            self.is_connected = False

    def _send_client_id(self):
        """发送客户端ID到服务器用于负载均衡"""
        try:
            registration = json.dumps({
                "action": "register",
                "client_id": self.client_id
            }).encode(self.encoding) + self.delimiter
            self.socket.sendall(registration)
        except Exception as e:
            self.logger.error(f"发送客户端ID失败: {e}")

    def _reconnect(self):
        """尝试重新连接"""
        current_time = time.time()
        if current_time - self.last_connect_attempt < self.reconnect_interval:
            return False
        
        self.last_connect_attempt = current_time
        self.logger.info("尝试重新连接...")
        
        try:
            if self.socket:
                self.socket.close()
            self._initialize_connection()
            return self.is_connected
        except Exception as e:
            self.logger.error(f"重连失败: {e}")
            return False

    def _receive_data(self) -> Optional[bytes]:
        """从套接字接收数据"""
        if not self.is_connected and self.protocol == "tcp":
            if not self.reconnect or not self._reconnect():
                return None       
        try:
            if self.protocol == "tcp":

                data = self.socket.recv(self.buffer_size)
                print(f"recv data: {data}")
                return data
            else:  # UDP
                data, _ = self.socket.recvfrom(self.buffer_size)
                return data
        except socket.timeout:
            return None  # 超时是正常情况
        except socket.error as e:
            self.logger.error(f"接收数据错误: {e}")
            self.is_connected = False
            return None

    def _process_buffer(self) -> Optional[str]:
        """处理缓冲区并提取完整消息"""
        # 检查是否有完整消息
        if self.buffer:
            if self.delimiter in self.buffer:
                message, _, self.buffer = self.buffer.partition(self.delimiter)
                try:
                    return message.decode(self.encoding).strip()
                except UnicodeDecodeError:
                    self.logger.error("解码消息失败")
                    return None
            else:
                message = self.buffer.decode(self.encoding).strip()
                self.buffer = b""
                return message
        return None

    def execute(self) -> Union[str, dict, None]:
        """
        从套接字读取数据并返回完整消息
        
        返回:
        - 字符串: 当接收到完整消息时
        - None: 当没有完整消息或连接断开时
        """
        message = self._process_buffer()
        if message:
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: 接收到消息: {message}\033[0m")
            return message
        data= None
        # 接收新数据
        while data is None and message is None :
            data = self._receive_data()
            if data:
                self.buffer += data
                message = self._process_buffer()
                if message:
                    self.logger.info(f"\033[32m[ {self.__class__.__name__}]: 接收到消息: {message}\033[0m")
                    return message       
        # 没有完整消息
        return None

    def close(self):
        """关闭套接字连接"""
        if self.socket:
            try:
                if self.protocol == "tcp" and self.load_balancing:
                    # 发送注销请求
                    deregistration = json.dumps({
                        "action": "deregister",
                        "client_id": self.client_id
                    }).encode(self.encoding) + self.delimiter
                    self.socket.sendall(deregistration)
                self.socket.close()
                self.logger.info("连接已关闭")
            except Exception as e:
                self.logger.error(f"关闭连接时出错: {e}")
            finally:
                self.socket = None
                self.is_connected = False

    def __del__(self):
        self.close()

# def main():
#     """主函数：使用 SocketSource 持续接收服务端消息"""
#     # 配置日志
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     )
#     logger = logging.getLogger("SocketSourceMain")
    
#     # SocketSource 配置
#     config = {
#         "host": "localhost",      # 服务器地址
#         "port": 8888,             # 服务器端口
#         "protocol": "tcp",        # 使用 TCP 协议
#         "reconnect": True,        # 自动重连
#         "reconnect_interval": 3,  # 重连间隔 3 秒
#         "load_balancing": False,  # 不启用负载均衡
#         "client_id": "test-client",  # 客户端 ID
#         "buffer_size": 4096,      # 缓冲区大小 4KB
#         "timeout": 1,             # 超时时间 1 秒
#         "delimiter": "\n",        # 消息分隔符为换行符
#         "encoding": "utf-8"       # 使用 UTF-8 编码
#     }
    
#     # 创建 SocketSource 实例
#     logger.info("创建 SocketSource 实例...")
#     source = SocketSource(config=config)
    
#     # 消息计数器
#     message_count = 0
    
#     try:
#         logger.info("开始接收消息... (按 Ctrl+C 停止)")
#         logger.info(f"连接到 {config['host']}:{config['port']} ({config['protocol'].upper()})")
        
#         # 主循环
#         while True:
#             # 尝试获取消息
#             message = source.execute()
            
#             if message is not None:
#                 message_count += 1
#                 # 处理消息
#                 try:
#                     # 尝试解析 JSON 消息
#                     data = json.loads(message)
#                     logger.info(f"收到 JSON 消息 (#{message_count}): {json.dumps(data, indent=2)}")
#                 except json.JSONDecodeError:
#                     # 如果不是 JSON，直接显示原始消息
#                     logger.info(f"收到文本消息 (#{message_count}): {message}")
                
#                 # 示例：根据消息内容执行操作
#                 if "command" in message.lower():
#                     logger.warning("收到命令消息，可能需要特殊处理")
#             else:
#                 # 没有消息时短暂休眠
#                 time.sleep(0.1)
                
#     except KeyboardInterrupt:
#         logger.info("用户中断，停止接收消息")
#     except Exception as e:
#         logger.error(f"接收消息时发生错误: {e}")
#     finally:
#         # 关闭连接
#         source.close()
#         logger.info(f"共接收 {message_count} 条消息")
#         logger.info("程序退出")

# if __name__ == "__main__":
#     main()