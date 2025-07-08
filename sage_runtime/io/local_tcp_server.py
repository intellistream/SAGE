import socket
import threading
import pickle
from typing import Dict, Any, Callable, Optional
from sage_utils.custom_logger import CustomLogger


class LocalTcpServer:
    """
    本地TCP服务器，用于接收Ray Actor发送的数据
    """
    
    def __init__(self, 
                 host: str = None, 
                 port: int = None,
                 message_handler: Optional[Callable[[Dict[str, Any], tuple], None]] = None):
        """
        初始化TCP服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            message_handler: 消息处理回调函数，接收 (message, client_address) 参数
        """
        self.host = host or self._get_host_ip()  # 确定自己的ip地址
        self.port = port or self._allocate_tcp_port()  # 分配一个可用的端口
        self.message_handler = message_handler
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        
        self.logger = CustomLogger(
            filename="LocalTcpServer",
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING"
        )
        self.logger.info(f"Initializing LocalTcpServer on {self.host}:{self.port}")


    def _get_host_ip(self):
        """自动获取本机可用于外部连接的 IP 地址"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 连接到任意公网地址（不必可达，只为取出绑定IP）
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            self.logger.warning("Failed to get external IP, using localhost")
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip
    
    def _allocate_tcp_port(self) -> int:
        """为 DAG 分配可用的 TCP 端口"""
        import socket
        
        # 尝试从预设范围分配端口
        for port in range(19000, 20000):  # DAG 专用端口范围
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("localhost", port))
                    return port
            except OSError:
                continue
        # 如果预设范围都被占用，使用系统分配
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.logger.warning("All predefined ports are occupied, using system-assigned port")
            s.bind(("localhost", 0))
            return s.getsockname()[1]
        

    def set_message_handler(self, handler: Callable[[Dict[str, Any], tuple], None]):
        """设置消息处理器"""
        self.message_handler = handler
    
    def start(self):
        """启动TCP服务器"""
        if self.running:
            self.logger.warning("TCP server is already running")
            return
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            self.server_thread = threading.Thread(
                target=self._server_loop,
                name="LocalTcpServerThread"
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.logger.info(f"TCP server started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start TCP server: {e}")
            self.running = False
            raise
    
    def stop(self):
        """停止TCP服务器"""
        if not self.running:
            return
        
        self.logger.info("Stopping TCP server...")
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
            if self.server_thread.is_alive():
                self.logger.warning("TCP server thread did not stop gracefully")
        
        self.logger.info("TCP server stopped")
    
    def _server_loop(self):
        """TCP服务器主循环"""
        self.logger.debug("TCP server loop started")
        
        while self.running:
            try:
                if not self.server_socket:
                    break
                    
                client_socket, address = self.server_socket.accept()
                self.logger.debug(f"New TCP client connected from {address}")
                
                # 在新线程中处理客户端
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    name=f"TcpClient-{address[0]}:{address[1]}"
                )
                client_thread.daemon = True
                client_thread.start()
                
            except OSError as e:
                # Socket被关闭时会抛出OSError
                if self.running:
                    self.logger.error(f"Error accepting TCP connection: {e}")
                break
            except Exception as e:
                if self.running:
                    self.logger.error(f"Unexpected error in server loop: {e}")
        
        self.logger.debug("TCP server loop stopped")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """处理TCP客户端连接和消息"""
        try:
            while self.running:
                # 读取消息长度
                size_data = client_socket.recv(4)
                if not size_data:
                    break
                
                message_size = int.from_bytes(size_data, byteorder='big')
                if message_size <= 0 or message_size > 10 * 1024 * 1024:  # 10MB limit
                    self.logger.warning(f"Invalid message size {message_size} from {address}")
                    break
                
                # 读取消息内容
                message_data = self._receive_full_message(client_socket, message_size)
                if not message_data:
                    break
                
                # 反序列化并处理消息
                try:
                    message = pickle.loads(message_data)
                    self._process_message(message, address)
                except Exception as e:
                    self.logger.error(f"Error processing message from {address}: {e}")
                
        except Exception as e:
            self.logger.error(f"Error handling TCP client {address}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            self.logger.debug(f"TCP client {address} disconnected")
    
    def _receive_full_message(self, client_socket: socket.socket, message_size: int) -> Optional[bytes]:
        """接收完整的消息数据"""
        message_data = b''
        while len(message_data) < message_size:
            chunk_size = min(message_size - len(message_data), 8192)  # 8KB chunks
            chunk = client_socket.recv(chunk_size)
            if not chunk:
                self.logger.warning("Connection closed while receiving message")
                return None
            message_data += chunk
        
        return message_data
    
    def _process_message(self, message: Dict[str, Any], client_address: tuple):
        """处理接收到的消息"""
        try:
            if self.message_handler:
                self.message_handler(message, client_address)
            else:
                self.logger.warning(f"No message handler set, ignoring message from {client_address}")
                
        except Exception as e:
            self.logger.error(f"Error in message handler: {e}", exc_info=True)
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        return {
            "host": self.host,
            "port": self.port,
            "running": self.running,
            "address": f"{self.host}:{self.port}"
        }
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.stop()
        except:
            pass