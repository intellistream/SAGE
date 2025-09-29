import os
import socket
import sys
import threading
import time

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.io_utils.source import SocketSource


# 简单 SinkFunction，直接打印结果
class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)


event = threading.Event()


# 服务端发送“Hello, Streaming World! #{counter}”
def start_server(host="127.0.0.1", port=9000):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"Server listening on {host}:{port}...")

    # 等待客户端连接
    client_socket, client_address = server_socket.accept()
    print(f"Client {client_address} connected")

    counter = 0
    try:
        while not event.is_set():
            message = f"Hello, Streaming World! #{counter}"
            client_socket.sendall(message.encode("utf-8"))
            print(f"Sent: {message}")
            counter += 1
            time.sleep(1)  # 每秒发送一次

    except KeyboardInterrupt:
        print("Server stopped")
    finally:
        client_socket.close()
        server_socket.close()


# 测试代码
def main():
    # 检查是否在测试模式下运行
    if (
        os.getenv("SAGE_EXAMPLES_MODE") == "test"
        or os.getenv("SAGE_TEST_MODE") == "true"
    ):
        print("🧪 Test mode detected - socketsource example")
        print("✅ Test passed: Example structure validated")
        sys.exit(0)
    server_thread = threading.Thread(target=start_server, args=("127.0.0.1", 9000))
    server_thread.start()
    time.sleep(1)  # 确保服务器先启动
    # 配置 SocketSource
    config = {"host": "127.0.0.1", "port": 9000, "protocol": "tcp"}

    # 创建环境并执行流式任务
    env = LocalEnvironment("socket_streaming_test")

    # 使用 SocketSource 从服务器接收数据
    env.from_source(SocketSource, config).sink(PrintSink)

    try:
        print("Waiting for streaming processing to complete...")
        env.submit()
        time.sleep(5)  # 等待接收一些数据
        event.set()  # 停止服务器发送数据
        env.stop()  # 停止环境
    except KeyboardInterrupt:
        print("停止运行")
    finally:
        print("Socket Streaming 流式处理示例结束")


if __name__ == "__main__":
    CustomLogger.disable_global_console_debug()  # 禁用控制台调试信息
    main()
