#!/usr/bin/env python3
"""
安全的文件访问服务
只处理文件读取，不执行用户代码
"""

import os
import json
import socket
import threading
from pathlib import Path
from typing import Dict, Any, List
import stat
import pwd
import grp
from sage.utils.custom_logger import CustomLogger

class SecureFileAccessService:
    """
    安全的文件访问服务
    - 运行在sudo权限下
    - 只允许安全的文件操作
    - 严格的路径验证
    - 禁止执行用户代码
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19002):
        self.host = host
        self.port = port
        self.logger = CustomLogger([("console", "INFO")], name="FileAccessService")
        
        # 安全配置
        self.allowed_extensions = {'.txt', '.json', '.csv', '.yaml', '.yml', '.xml', '.md'}
        self.forbidden_paths = {'/etc', '/usr', '/bin', '/sbin', '/var/log', '/root'}
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        
    def start(self):
        """启动文件访问服务"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)
            
            self.logger.info(f"SecureFileAccessService started on {self.host}:{self.port}")
            
            while True:
                client_socket, client_address = server_socket.accept()
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                thread.daemon = True
                thread.start()
    
    def _handle_client(self, client_socket: socket.socket, client_address):
        """处理客户端请求"""
        try:
            # 接收请求
            data = client_socket.recv(4096)
            request = json.loads(data.decode('utf-8'))
            
            # 处理请求
            response = self._process_request(request)
            
            # 发送响应
            response_data = json.dumps(response).encode('utf-8')
            client_socket.send(response_data)
            
        except Exception as e:
            error_response = {
                "status": "error",
                "message": f"Request processing failed: {str(e)}"
            }
            client_socket.send(json.dumps(error_response).encode('utf-8'))
            
        finally:
            client_socket.close()
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理安全的文件访问请求"""
        action = request.get("action")
        
        if action == "read_file":
            return self._read_file(request)
        elif action == "list_directory":
            return self._list_directory(request)
        elif action == "check_file_access":
            return self._check_file_access(request)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def _validate_path(self, file_path: str) -> Dict[str, Any]:
        """严格的路径验证"""
        try:
            # 规范化路径
            normalized_path = os.path.normpath(os.path.abspath(file_path))
            
            # 检查是否在禁止目录中
            for forbidden in self.forbidden_paths:
                if normalized_path.startswith(forbidden):
                    return {
                        "valid": False,
                        "reason": f"Access to {forbidden} is forbidden"
                    }
            
            # 检查文件扩展名
            file_extension = Path(normalized_path).suffix.lower()
            if file_extension not in self.allowed_extensions:
                return {
                    "valid": False,
                    "reason": f"File extension {file_extension} not allowed"
                }
            
            # 检查文件是否存在
            if not os.path.exists(normalized_path):
                return {
                    "valid": False,
                    "reason": "File does not exist"
                }
            
            # 检查是否为常规文件
            if not os.path.isfile(normalized_path):
                return {
                    "valid": False,
                    "reason": "Path is not a regular file"
                }
            
            # 检查文件大小
            file_size = os.path.getsize(normalized_path)
            if file_size > self.max_file_size:
                return {
                    "valid": False,
                    "reason": f"File too large: {file_size} bytes"
                }
            
            return {
                "valid": True,
                "normalized_path": normalized_path,
                "file_size": file_size
            }
            
        except Exception as e:
            return {
                "valid": False,
                "reason": f"Path validation error: {str(e)}"
            }
    
    def _read_file(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """安全地读取文件"""
        file_path = request.get("file_path")
        if not file_path:
            return {"status": "error", "message": "Missing file_path"}
        
        # 验证路径
        validation = self._validate_path(file_path)
        if not validation["valid"]:
            return {"status": "error", "message": validation["reason"]}
        
        try:
            # 读取文件内容
            with open(validation["normalized_path"], 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "status": "success",
                "content": content,
                "file_path": validation["normalized_path"],
                "file_size": validation["file_size"]
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to read file: {str(e)}"}
    
    def _list_directory(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """安全地列出目录内容"""
        dir_path = request.get("dir_path")
        if not dir_path:
            return {"status": "error", "message": "Missing dir_path"}
        
        try:
            normalized_path = os.path.normpath(os.path.abspath(dir_path))
            
            # 检查禁止目录
            for forbidden in self.forbidden_paths:
                if normalized_path.startswith(forbidden):
                    return {"status": "error", "message": f"Access to {forbidden} is forbidden"}
            
            if not os.path.isdir(normalized_path):
                return {"status": "error", "message": "Path is not a directory"}
            
            # 列出文件
            files = []
            for item in os.listdir(normalized_path):
                item_path = os.path.join(normalized_path, item)
                if os.path.isfile(item_path):
                    file_extension = Path(item).suffix.lower()
                    if file_extension in self.allowed_extensions:
                        files.append({
                            "name": item,
                            "path": item_path,
                            "size": os.path.getsize(item_path)
                        })
            
            return {
                "status": "success",
                "directory": normalized_path,
                "files": files
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to list directory: {str(e)}"}
    
    def _check_file_access(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """检查文件访问权限"""
        file_path = request.get("file_path")
        if not file_path:
            return {"status": "error", "message": "Missing file_path"}
        
        validation = self._validate_path(file_path)
        
        return {
            "status": "success",
            "accessible": validation["valid"],
            "reason": validation.get("reason"),
            "details": validation if validation["valid"] else None
        }


class SecureFileClient:
    """安全文件访问客户端"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19002):
        self.host = host
        self.port = port
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求到文件访问服务"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                
                # 发送请求
                request_data = json.dumps(request).encode('utf-8')
                sock.send(request_data)
                
                # 接收响应
                response_data = sock.recv(1024 * 1024)  # 1MB buffer
                return json.loads(response_data.decode('utf-8'))
                
        except Exception as e:
            return {"status": "error", "message": f"Communication failed: {str(e)}"}
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """安全地读取文件"""
        return self._send_request({
            "action": "read_file",
            "file_path": file_path
        })
    
    def list_directory(self, dir_path: str) -> Dict[str, Any]:
        """安全地列出目录"""
        return self._send_request({
            "action": "list_directory",
            "dir_path": dir_path
        })
    
    def check_file_access(self, file_path: str) -> Dict[str, Any]:
        """检查文件访问权限"""
        return self._send_request({
            "action": "check_file_access", 
            "file_path": file_path
        })


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure File Access Service")
    parser.add_argument("--host", default="127.0.0.1", help="Service host")
    parser.add_argument("--port", type=int, default=19002, help="Service port")
    
    args = parser.parse_args()
    
    service = SecureFileAccessService(args.host, args.port)
    service.start()
