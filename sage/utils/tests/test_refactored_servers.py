#!/usr/bin/env python3
"""
测试重构后的服务器类
"""

import sys
import os
import time
import threading
import json
import socket
from typing import Dict, Any

# 添加sage到路径
sys.path.insert(0, '/home/tjy/SAGE')

from sage.utils.network.local_tcp_server import LocalTcpServer, BaseTcpServer

class TestTcpServer(BaseTcpServer):
    """测试用的TCP服务器，继承自BaseTcpServer"""
    
    def __init__(self, host: str = None, port: int = None):
        super().__init__(host, port, server_name="TestTcpServer")
        self.received_messages = []
    
    def _handle_message_data(self, message_data: bytes, client_address: tuple) -> Dict[str, Any]:
        """处理接收到的消息数据"""
        try:
            # 假设接收到的是JSON数据
            message_str = message_data.decode('utf-8')
            message = json.loads(message_str)
            
            self.received_messages.append(message)
            self.logger.info(f"Received message: {message}")
            
            # 返回响应
            return {
                "status": "success",
                "message": "Message received",
                "received_data": message,
                "timestamp": int(time.time())
            }
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return {
                "status": "error",
                "message": f"Error processing message: {str(e)}"
            }
    
    def _serialize_response(self, response: Any) -> bytes:
        """序列化响应为JSON格式"""
        return json.dumps(response).encode('utf-8')

def test_base_tcp_server():
    """测试BaseTcpServer"""
    print("=== 测试BaseTcpServer ===")
    
    server = TestTcpServer()
    print(f"Server created: {server.get_server_info()}")
    
    # 启动服务器
    server.start()
    time.sleep(0.5)  # 等待服务器启动
    
    try:
        # 创建客户端连接并发送消息
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server.host, server.port))
        
        # 发送测试消息
        test_message = {"type": "test", "data": "Hello Server!"}
        message_data = json.dumps(test_message).encode('utf-8')
        
        # 发送消息长度
        client_socket.send(len(message_data).to_bytes(4, byteorder='big'))
        # 发送消息内容
        client_socket.send(message_data)
        
        # 接收响应
        response_length_data = client_socket.recv(4)
        response_length = int.from_bytes(response_length_data, byteorder='big')
        response_data = client_socket.recv(response_length)
        response = json.loads(response_data.decode('utf-8'))
        
        print(f"收到响应: {response}")
        
        client_socket.close()
        
        # 检查服务器是否收到消息
        time.sleep(0.1)
        print(f"服务器收到的消息: {server.received_messages}")
        
    finally:
        server.stop()
    
    print("BaseTcpServer测试完成\n")

def test_local_tcp_server():
    """测试LocalTcpServer"""
    print("=== 测试LocalTcpServer ===")
    
    def handle_test_message(message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        print(f"处理测试消息 from {client_address}: {message}")
        return {
            "type": "test_response",
            "status": "success", 
            "message": "Test message processed",
            "original": message
        }
    
    def handle_default_message(message: Dict[str, Any], client_address: tuple) -> Dict[str, Any]:
        print(f"处理默认消息 from {client_address}: {message}")
        return {
            "type": "default_response",
            "status": "success",
            "message": "Default handler processed message"
        }
    
    # 创建LocalTcpServer
    server = LocalTcpServer(default_handler=handle_default_message)
    server.register_handler("test", handle_test_message)
    
    print(f"Server created: {server.get_server_info()}")
    
    # 启动服务器
    server.start()
    time.sleep(0.5)
    
    try:
        # 测试特定类型的消息处理
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((server.host, server.port))
        
        # 发送测试消息（有注册的处理器）
        test_message = {"type": "test", "data": "Hello from LocalTcpServer test!"}
        import pickle
        message_data = pickle.dumps(test_message)
        
        # 发送消息
        client_socket.send(len(message_data).to_bytes(4, byteorder='big'))
        client_socket.send(message_data)
        
        # 接收响应
        response_length_data = client_socket.recv(4)
        response_length = int.from_bytes(response_length_data, byteorder='big')
        response_data = client_socket.recv(response_length)
        response = pickle.loads(response_data)
        
        print(f"收到响应: {response}")
        
        client_socket.close()
        
    finally:
        server.stop()
    
    print("LocalTcpServer测试完成\n")

def main():
    """主测试函数"""
    print("开始测试重构后的服务器类\n")
    
    try:
        test_base_tcp_server()
        test_local_tcp_server()
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
