import csv
import json
import socket
import time
from pathlib import Path

from sage.common.config.ports import SagePorts
from sage.common.core import SourceFunction


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

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        """
        Initializes the FileSource with the provided configuration and sets the data path for the file.

        :param config: Configuration dictionary containing source settings, including `data_path`.
        """
        if config is None:
            raise ValueError("config parameter is required for FileSource")
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

    def execute(self) -> str | None:
        """
        Reads the next line from the file and returns it as a string.

        :return: A Data object containing the next line of the file content.
        """
        try:
            while True:
                with open(self.data_path, encoding="utf-8") as f:
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
            return None
        except Exception as e:
            self.logger.error(f"Error reading file '{self.data_path}': {e}")
            return None


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

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.host = self.config.get("host", "127.0.0.1")
        self.port = self.config.get("port", SagePorts.GATEWAY_DEFAULT)
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
        if self.socket is None:
            self.logger.error("Socket is not initialized")
            return

        try:
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            self.logger.info(f"成功连接到 {self.host}:{self.port} (TCP)")

            # 发送客户端ID用于负载均衡
            if self.load_balancing:
                self._send_client_id()
        except OSError as e:
            self.logger.error(f"连接失败: {e}")
            self.is_connected = False

    def _send_client_id(self):
        """发送客户端ID到服务器用于负载均衡"""
        if self.socket is None:
            self.logger.error("Socket is not initialized")
            return

        try:
            registration = (
                json.dumps({"action": "register", "client_id": self.client_id}).encode(
                    self.encoding
                )
                + self.delimiter
            )
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

    def _receive_data(self) -> bytes | None:
        """从套接字接收数据"""
        if not self.is_connected and self.protocol == "tcp":
            if not self.reconnect or not self._reconnect():
                return None

        if self.socket is None:
            self.logger.error("Socket is not initialized")
            return None

        try:
            if self.protocol == "tcp":
                data = self.socket.recv(self.buffer_size)
                self.logger.debug(f"recv data: {data}")
                return data
            else:  # UDP
                data, _ = self.socket.recvfrom(self.buffer_size)
                return data
        except TimeoutError:
            return None  # 超时是正常情况
        except OSError as e:
            self.logger.error(f"接收数据错误: {e}")
            self.is_connected = False
            return None

    def _process_buffer(self) -> str | None:
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
                # 没有完整消息，等待更多数据
                return None
        return None

    def execute(self) -> str | dict | None:
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
        data = None
        while data is None and message is None:
            data = self._receive_data()
            if data:
                self.buffer += data
                message = self._process_buffer()
                if message:
                    self.logger.info(
                        f"\033[32m[ {self.__class__.__name__}]: 接收到消息: {message}\033[0m"
                    )
                    return message
        # 没有完整消息
        return None

    def close(self):
        """关闭套接字连接"""
        if self.socket:
            try:
                if self.protocol == "tcp" and self.load_balancing:
                    # 发送注销请求
                    deregistration = (
                        json.dumps({"action": "deregister", "client_id": self.client_id}).encode(
                            self.encoding
                        )
                        + self.delimiter
                    )
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


# ============================================================================
# 额外的Source类实现
# ============================================================================


class TextFileSource(SourceFunction):
    """
    文本文件源 - 读取文本文件内容

    配置参数:
    - file_path: 文件路径
    - encoding: 文件编码 (默认utf-8)
    - read_mode: 读取模式 ('all', 'lines') (默认'all')
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        if config is None:
            raise ValueError("config parameter is required for TextFileSource")
        self.config = config
        file_path = self.config.get("file_path")
        if file_path is None:
            raise ValueError("file_path is required in config")
        self.file_path = file_path
        self.encoding = self.config.get("encoding", "utf-8")
        self.read_mode = self.config.get("read_mode", "all")

    def execute(self, data=None) -> str | list[str]:
        """读取文本文件"""
        try:
            with open(self.file_path, encoding=self.encoding) as f:
                if self.read_mode == "lines":
                    return f.readlines()
                else:
                    return f.read()
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            raise


class JSONFileSource(SourceFunction):
    """
    JSON文件源 - 读取JSON文件内容

    配置参数:
    - file_path: 文件路径
    - encoding: 文件编码 (默认utf-8)
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        if config is None:
            raise ValueError("config parameter is required for JSONFileSource")
        self.config = config
        file_path = self.config.get("file_path")
        if file_path is None:
            raise ValueError("file_path is required in config")
        self.file_path = file_path
        self.encoding = self.config.get("encoding", "utf-8")

    def execute(self, data=None) -> dict | list:
        """读取JSON文件"""
        try:
            with open(self.file_path, encoding=self.encoding) as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.file_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading JSON file: {e}")
            raise


class CSVFileSource(SourceFunction):
    """
    CSV文件源 - 读取CSV文件内容

    配置参数:
    - file_path: 文件路径
    - delimiter: 分隔符 (默认',')
    - encoding: 文件编码 (默认utf-8)
    - has_header: 是否有表头 (默认True)
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        if config is None:
            raise ValueError("config parameter is required for CSVFileSource")
        self.config = config
        file_path = self.config.get("file_path")
        if file_path is None:
            raise ValueError("file_path is required in config")
        self.file_path = file_path
        self.delimiter = self.config.get("delimiter", ",")
        self.encoding = self.config.get("encoding", "utf-8")
        self.has_header = self.config.get("has_header", True)

    def execute(self, data=None) -> list[dict] | list[list]:
        """读取CSV文件"""
        try:
            with open(self.file_path, encoding=self.encoding) as f:
                if self.has_header:
                    reader = csv.DictReader(f, delimiter=self.delimiter)
                    return list(reader)
                else:
                    reader = csv.reader(f, delimiter=self.delimiter)
                    return list(reader)
        except FileNotFoundError:
            self.logger.error(f"File not found: {self.file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading CSV file: {e}")
            raise


class KafkaSource(SourceFunction):
    """
    Kafka源 - 从Kafka topic读取消息（占位实现）

    配置参数:
    - bootstrap_servers: Kafka服务器列表
    - topic: Kafka topic名称
    - group_id: 消费者组ID
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.bootstrap_servers = self.config.get("bootstrap_servers", ["localhost:9092"])
        self.topic = self.config.get("topic")
        self.group_id = self.config.get("group_id", "sage_consumer")

    def execute(self, data=None) -> dict | None:
        """读取Kafka消息（占位实现）"""
        self.logger.warning("KafkaSource is a placeholder implementation")
        # 实际实现需要kafka-python库
        # from kafka import KafkaConsumer
        # consumer = KafkaConsumer(self.topic, ...)
        return None


class DatabaseSource(SourceFunction):
    """
    数据库源 - 从数据库查询数据（占位实现）

    配置参数:
    - connection_string: 数据库连接字符串
    - query: SQL查询语句
    - params: 查询参数
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.connection_string = self.config.get("connection_string")
        self.query = self.config.get("query")
        self.params = self.config.get("params", {})

    def execute(self, data=None) -> list[dict] | None:
        """执行数据库查询（占位实现）"""
        self.logger.warning("DatabaseSource is a placeholder implementation")
        # 实际实现需要数据库驱动（如psycopg2, pymysql等）
        return None


class APISource(SourceFunction):
    """
    API源 - 从REST API获取数据（占位实现）

    配置参数:
    - url: API端点URL
    - method: HTTP方法 (GET, POST等)
    - headers: HTTP头部
    - params: 请求参数
    - timeout: 请求超时时间
    """

    def __init__(self, config: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        self.url = self.config.get("url")
        self.method = self.config.get("method", "GET")
        self.headers = self.config.get("headers", {})
        self.params = self.config.get("params", {})
        self.timeout = self.config.get("timeout", 30)

    def execute(self, data=None) -> dict | list | None:
        """调用API获取数据（占位实现）"""
        self.logger.warning("APISource is a placeholder implementation")
        # 实际实现需要requests库
        # import requests
        # response = requests.request(self.method, self.url, ...)
        return None
