import unittest
import socket
import threading
import time
import json
import logging
from sage.libs.io_utils.source import SocketSource  # 假设上面的 SocketSource 类保存在 socket_source.py 文件中

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SocketSourceTest")

class TestSocketSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 启动测试服务器
        cls.tcp_server = TestTCPServer(port=9000)
        cls.udp_server = TestUDPServer(port=9001)
        cls.tcp_server.start()
        cls.udp_server.start()
        time.sleep(0.5)  # 给服务器启动时间

    @classmethod
    def tearDownClass(cls):
        cls.tcp_server.stop()
        cls.udp_server.stop()

    def test_tcp_basic(self):
        """测试 TCP 基础功能 - 接收单条消息"""
        config = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "delimiter": "|"
        }
        
        source = SocketSource(config=config)
        
        # 发送测试消息
        self.tcp_server.send_message("Msg for client1")
        self.tcp_server.send_message("Msg for client1")
        self.tcp_server.send_message("Msg for client1")
        result = source.execute()
        print(f"result: {result}")
        source.close()

    def test_udp_basic(self):
        """测试 UDP 基础功能 - 接收单条消息"""
        config = {
            "host": "localhost",
            "port": 9001,
            "protocol": "udp",
            "delimiter": "\n"
        }
        
        source = SocketSource(config=config)
        
        # 发送测试消息
        self.udp_server.send_message("Hello UDP\n")
        
        # 接收消息
        result = source.execute()
        self.assertEqual(result, "Hello UDP")
        source.close()

    def test_multiple_messages(self):
        """测试连续接收多条消息"""
        config = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "delimiter": "|"
        }
        
        source = SocketSource(config=config)
        time.sleep(0.5)  # 确保连接建立
        # 发送多条消息
        messages = ["Message 1|", "Message 2|", "Message 3|"]
        for msg in messages:
            self.tcp_server.send_message(msg)
            time.sleep(0.1)
            result = source.execute()
            self.assertEqual(result, msg.strip("|"))
        
        source.close()

    def test_reconnect(self):
        """测试自动重连功能"""
        config = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "reconnect": True,
            "reconnect_interval": 1,
            "delimiter": "|"
        }
        
        source = SocketSource(config=config)
        time.sleep(0.5)  # 确保连接建立
        # 发送第一条消息
        self.tcp_server.send_message("Before disconnect|")
        result = source.execute()
        self.assertEqual(result, "Before disconnect")
        
        # 断开服务器连接
        self.tcp_server.stop()
        time.sleep(1)
        
        # 尝试接收 - 应该失败
        result = source.execute()
        self.assertIsNone(result)
        
        # 重启服务器
        self.tcp_server.start()
        time.sleep(1.5)  # 等待重连
        
        # 发送第二条消息
        self.tcp_server.send_message("After reconnect|")
        result = source.execute()
        self.assertEqual(result, "After reconnect")
        
        source.close()

    def test_load_balancing(self):
        """测试负载均衡功能"""
        # 创建两个客户端
        config1 = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "load_balancing": True,
            "client_id": "client1",
            "delimiter": "|"
        }
        
        config2 = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "load_balancing": True,
            "client_id": "client2",
            "delimiter": "|"
        }
        
        source1 = SocketSource(config=config1)
        source2 = SocketSource(config=config2)
        
        # 发送消息给所有客户端
        messages = ["Msg for client1|", "Msg for client2|", "Msg for client1|", "Msg for client2|"]
        for msg in messages:
            self.tcp_server.send_message(msg)
            time.sleep(0.1)
        
        # 检查客户端1接收的消息
        result1 = source1.execute()
        result2 = source1.execute()
        self.assertEqual(result1, "Msg for client1")
        self.assertEqual(result2, "Msg for client1")
        
        # 检查客户端2接收的消息
        result1 = source2.execute()
        result2 = source2.execute()
        self.assertEqual(result1, "Msg for client2")
        self.assertEqual(result2, "Msg for client2")
        
        source1.close()
        source2.close()

    def test_different_delimiters(self):
        """测试不同分隔符的处理"""
        config = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "delimiter": "END"
        }
        
        source = SocketSource(config=config)
        time.sleep(0.5)  # 确保连接建立
        print(source.is_connected)
        # 发送带分隔符的消息
        self.tcp_server.send_message("Message with custom delimiterEND")
        print("发送完消息")
        # 接收消息
        result = source.execute()
        self.assertEqual(result, "Message with custom delimiter")
        source.close()

    def test_large_message(self):
        """测试大消息处理"""
        config = {
            "host": "localhost",
            "port": 9000,
            "protocol": "tcp",
            "buffer_size": 1024,
            "delimiter": "|"
        }
        
        source = SocketSource(config=config)
        time.sleep(0.5)  # 确保连接建立
        # 创建大消息 (大于缓冲区大小)
        large_message = "A" * 2000 + "|"
        self.tcp_server.send_message(large_message)
        
        # 接收消息
        result = source.execute()
        self.assertEqual(len(result), 2000)
        self.assertEqual(result, "A" * 2000)
        source.close()

 
class TestTCPServer:
    """TCP 测试服务器"""
    def __init__(self, host="localhost", port=9000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = True
        self.thread = None
        self.clients = {}
        self.lock = threading.Lock()
        self.client_socket_id = 0

    def start(self):
        self.server_socket = socket.socket()
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"TCP server started on {self.host}:{self.port}")
        print(f"TCP server started on {self.host}:{self.port}")
    def stop(self):
        if not self.running:
            return
            
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        for client in self.clients.values():
            client.close()
        logger.info("TCP server stopped")

    def _run(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logger.info(f"New TCP connection from {addr}")
                with self.lock:
                    self.client_socket_id += 1
                    client_id = f"{addr[0]}:{addr[1]}_{self.client_socket_id}" 
                    self.clients[client_id] = client_socket
            except OSError:
                break  # Server socket closed


    def _handle_client(self, client_socket, client_id):
        """处理客户端连接"""
        while self.running:
            try:
                # 保持连接，但不做特别处理
                data = client_socket.recv(1024)
                if not data:
                    break
            except:
                break
        
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]
        client_socket.close()
        logger.info(f"Client {client_id} disconnected")

    def send_message(self, message):
        """发送消息给所有客户端"""
        with self.lock:
            for client_id, client_socket in self.clients.items():
                try:
                    client_socket.send(message.encode("UTF-8"))
                except:
                    logger.warning(f"Failed to send message to client {client_id}")

class TestUDPServer:
    """UDP 测试服务器"""
    def __init__(self, host="localhost", port=9001):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.thread = None
        self.clients = {}
        self.lock = threading.Lock()

    def start(self):            
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.host, self.port))
        self.running = True
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"UDP server started on {self.host}:{self.port}")

    def stop(self):
        if not self.running:
            return
            
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("UDP server stopped")

    def _run(self):
        while self.running:
            try:
                data, addr = self.server_socket.recvfrom(1024)
                client_id = self._parse_client_id(data)
                
                with self.lock:
                    self.clients[addr] = client_id
            except OSError:
                break  # Server socket closed

    def _parse_client_id(self, data):
        """解析客户端ID（用于负载均衡）"""
        try:
            message = json.loads(data.decode())
            if message.get("action") == "register":
                return message.get("client_id", "unknown")
        except:
            pass
        return "unknown"

    def send_message(self, message):
        """发送消息给所有已知客户端"""
        with self.lock:
            for addr, client_id in self.clients.items():
                try:
                    self.server_socket.sendto(message.encode(), addr)
                except:
                    logger.warning(f"Failed to send message to client {client_id} at {addr}")

if __name__ == "__main__":
    unittest.main(verbosity=2)

    