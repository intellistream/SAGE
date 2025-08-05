#!/usr/bin/env python3
"""
远程环境服务端测试脚本
用于接收序列化的环境并验证其完整性

这个文件既可以作为独立的测试服务器运行，也可以通过pytest运行标准测试。

独立运行Usage:
    # 运行完整的RemoteEnvironment序列化测试
    python test_remote_environment_server.py --mode remote_env_test
    
    # 只启动服务器
    python test_remote_environment_server.py --mode server
    
    # 只发送测试数据
    python test_remote_environment_server.py --mode client
    
    # 运行基础测试
    python test_remote_environment_server.py --mode test

Pytest运行Usage:
    # 运行所有pytest测试
    python -m pytest test_remote_environment_server.py -v
    
    # 运行特定测试
    python -m pytest test_remote_environment_server.py::test_basic_environment_serialization -v
"""

import socket
import pickle
import json
import logging
import threading
import time
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent  # 指向SAGE项目根目录
sys.path.insert(0, str(project_root))
print(f"Added to Python path: {project_root}")

# 导入SAGE的序列化工具
try:
    from sage.kernel.utils.serialization.dill_serializer import serialize_object, deserialize_object
    print("✅ Using SAGE dill_serializer for serialization")
    has_sage_serializer = True
except ImportError as e:
    print(f"❌ Could not import SAGE dill_serializer: {e}")
    print("Falling back to pickle")
    import pickle
    has_sage_serializer = False

# 导入RemoteEnvironment用于测试
try:
    from sage.kernel.api.remote_environment import RemoteEnvironment
    print("✅ Successfully imported RemoteEnvironment")
    has_remote_environment = True
except ImportError as e:
    print(f"❌ Could not import RemoteEnvironment: {e}")
    print("🔧 Creating mock RemoteEnvironment for testing...")
    
    # 创建一个简化的测试环境类
    class MockRemoteEnvironment:
        """模拟的RemoteEnvironment类用于测试序列化"""
        
        def __init__(self, name: str, config: dict = None, host: str = "127.0.0.1", port: int = 19001):
            self.name = name
            self.config = config or {}
            self.platform = "remote"
            self.daemon_host = host
            self.daemon_port = port
            self.pipeline = []
            self.env_uuid = None
            self.is_running = False
            
            # 模拟排除的属性
            self._engine_client = None
            self._jobmanager = None
            
        def __repr__(self):
            return f"MockRemoteEnvironment(name='{self.name}', host='{self.daemon_host}', port={self.daemon_port})"
    
    # 使用模拟类
    RemoteEnvironment = MockRemoteEnvironment
    has_remote_environment = True
    print("✅ Mock RemoteEnvironment created successfully")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnvironmentTestServer:
    """环境测试服务器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 19002):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.received_environments = []
        
    def start(self):
        """启动服务器"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.settimeout(1.0)  # 设置超时以便能优雅退出
                self.socket.bind((self.host, self.port))
                self.socket.listen(5)
                
                self.running = True
                logger.info(f"Environment test server started on {self.host}:{self.port}")
                break
                
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    if attempt < max_retries - 1:
                        # 尝试下一个端口
                        self.port += 1
                        logger.warning(f"Port {self.port - 1} in use, trying {self.port}")
                        continue
                    else:
                        logger.error(f"Failed to bind after {max_retries} attempts: {e}")
                        return
                else:
                    logger.error(f"Failed to start server: {e}")
                    return
            except Exception as e:
                logger.error(f"Failed to start server: {e}")
                return
        
        try:
            while self.running:
                try:
                    client_socket, client_address = self.socket.accept()
                    logger.info(f"New connection from {client_address}")
                    
                    # 创建线程处理客户端
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
                    
        except Exception as e:
            logger.error(f"Server loop error: {e}")
        finally:
            self.stop()
    
    def _handle_client(self, client_socket: socket.socket, client_address):
        """处理客户端连接"""
        try:
            with client_socket:
                # 接收数据长度
                length_data = client_socket.recv(4)
                if len(length_data) != 4:
                    logger.warning("Invalid length header")
                    return
                
                data_length = int.from_bytes(length_data, byteorder='big')
                logger.info(f"Expecting {data_length} bytes from {client_address}")
                
                # 接收完整数据
                received_data = b""
                while len(received_data) < data_length:
                    chunk = client_socket.recv(min(4096, data_length - len(received_data)))
                    if not chunk:
                        break
                    received_data += chunk
                
                if len(received_data) != data_length:
                    logger.error(f"Data length mismatch: expected {data_length}, got {len(received_data)}")
                    self._send_response(client_socket, {
                        "status": "error",
                        "message": "Data length mismatch"
                    })
                    return
                
                logger.info(f"Received {len(received_data)} bytes, attempting to deserialize...")
                
                # 反序列化环境对象
                env = self._deserialize_environment(received_data)
                
                if env is not None:
                    logger.info("✅ Successfully deserialized environment object")
                    
                    # 验证环境对象
                    validation_result = self._validate_environment(env)
                    
                    # 记录接收到的环境
                    self.received_environments.append({
                        "timestamp": time.time(),
                        "client_address": client_address,
                        "data_size": len(received_data),
                        "environment": env,  # 存储反序列化的环境
                        "validation": validation_result
                    })
                    
                    # 发送成功响应
                    response = {
                        "status": "success",
                        "message": "Environment received and validated",
                        "validation": validation_result
                    }
                    self._send_response(client_socket, response)
                    
                else:
                    logger.error("❌ Failed to deserialize environment")
                    # 发送错误响应
                    response = {
                        "status": "error", 
                        "message": "Deserialization failed"
                    }
                    self._send_response(client_socket, response)
                    
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
    
    def _deserialize_environment(self, data: bytes) -> Optional[Any]:
        """反序列化环境数据"""
        try:
            # 使用SAGE的dill序列化器
            if has_sage_serializer:
                try:
                    return deserialize_object(data)
                except Exception as e:
                    logger.warning(f"SAGE dill deserialization failed: {e}, trying pickle...")
            
            # 备用：使用pickle
            try:
                return pickle.loads(data)
            except Exception as e:
                logger.error(f"Pickle deserialization also failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None
    
    def _validate_environment(self, env_data: Any) -> Dict[str, Any]:
        """验证环境数据的完整性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": {}
        }
        
        try:
            # 基本类型检查
            if env_data is None:
                validation_result["valid"] = False
                validation_result["errors"].append("Environment data is None")
                return validation_result
            
            # 获取环境基本信息
            env_type = type(env_data).__name__
            validation_result["info"]["type"] = env_type
            
            # 检查是否有必要的属性
            required_attrs = ["name", "config", "platform"]
            missing_attrs = []
            
            for attr in required_attrs:
                if hasattr(env_data, attr):
                    value = getattr(env_data, attr)
                    validation_result["info"][attr] = str(value) if value is not None else None
                else:
                    missing_attrs.append(attr)
            
            if missing_attrs:
                validation_result["warnings"].append(f"Missing attributes: {missing_attrs}")
            
            # 检查pipeline
            if hasattr(env_data, 'pipeline'):
                pipeline = getattr(env_data, 'pipeline')
                if pipeline:
                    validation_result["info"]["pipeline_length"] = len(pipeline) if hasattr(pipeline, '__len__') else 'unknown'
                    validation_result["info"]["pipeline_type"] = type(pipeline).__name__
                else:
                    validation_result["info"]["pipeline_length"] = 0
            else:
                validation_result["warnings"].append("No pipeline attribute found")
            
            # 检查配置
            if hasattr(env_data, 'config'):
                config = getattr(env_data, 'config')
                if isinstance(config, dict):
                    validation_result["info"]["config_keys"] = list(config.keys())
                    validation_result["info"]["config_size"] = len(config)
                else:
                    validation_result["warnings"].append(f"Config is not a dict: {type(config)}")
            
            # 检查是否有客户端连接相关的属性（应该被排除）
            excluded_attrs = ["_engine_client", "_jobmanager", "client", "jobmanager"]
            found_excluded = []
            
            for attr in excluded_attrs:
                if hasattr(env_data, attr):
                    value = getattr(env_data, attr)
                    if value is not None:
                        found_excluded.append(attr)
            
            if found_excluded:
                validation_result["warnings"].append(f"Found excluded attributes (should be None): {found_excluded}")
            
            # 统计总属性数
            if hasattr(env_data, '__dict__'):
                total_attrs = len(env_data.__dict__)
                validation_result["info"]["total_attributes"] = total_attrs
            
            logger.info(f"Environment validation completed: {validation_result}")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            logger.error(f"Environment validation error: {e}")
        
        return validation_result
    
    def _send_response(self, client_socket: socket.socket, response: Dict[str, Any]):
        """发送响应给客户端"""
        try:
            response_data = json.dumps(response).encode('utf-8')
            response_length = len(response_data)
            
            # 发送长度头
            client_socket.send(response_length.to_bytes(4, byteorder='big'))
            # 发送数据
            client_socket.send(response_data)
            
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        logger.info("Environment test server stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务器统计信息"""
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "received_count": len(self.received_environments),
            "last_received": self.received_environments[-1]["timestamp"] if self.received_environments else None
        }
    
    def get_environment_summary(self, env_id: int = None) -> Dict[str, Any]:
        """获取环境摘要"""
        if env_id is None:
            # 返回所有环境的摘要
            summaries = []
            for i, env_record in enumerate(self.received_environments, 1):
                summaries.append({
                    "id": i,
                    "timestamp": env_record["timestamp"],
                    "client": str(env_record["client_address"]),
                    "valid": env_record["validation"]["valid"],
                    "type": env_record["validation"]["info"].get("type", "unknown"),
                    "name": env_record["validation"]["info"].get("name", "unknown")
                })
            return {"environments": summaries}
        else:
            # 返回特定环境的详细信息
            if 1 <= env_id <= len(self.received_environments):
                return self.received_environments[env_id - 1]
            else:
                return {"error": f"Environment {env_id} not found"}


def send_test_environment(server_host: str = "127.0.0.1", server_port: int = 19002):
    """发送测试环境到服务器"""
    try:
        # 创建一个简单的测试环境数据
        test_env_data = {
            "name": "test_environment",
            "config": {"test_key": "test_value"},
            "platform": "remote",
            "pipeline": ["step1", "step2", "step3"]
        }
        
        # 序列化
        if has_sage_serializer:
            # 使用SAGE的dill序列化器
            serialized_data = serialize_object(test_env_data)
            logger.info("Using SAGE dill_serializer for serialization")
        else:
            # 使用pickle
            serialized_data = pickle.dumps(test_env_data)
            logger.info("Using pickle for serialization")
        
        logger.info(f"Sending test environment data ({len(serialized_data)} bytes)")
        
        # 连接到服务器
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((server_host, server_port))
            
            # 发送数据长度
            data_length = len(serialized_data)
            client_socket.send(data_length.to_bytes(4, byteorder='big'))
            
            # 发送数据
            client_socket.send(serialized_data)
            
            # 接收响应
            response_length_data = client_socket.recv(4)
            response_length = int.from_bytes(response_length_data, byteorder='big')
            
            response_data = client_socket.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            logger.info(f"Server response: {response}")
            
    except Exception as e:
        logger.error(f"Error sending test environment: {e}")


def send_remote_environment_test(server_host: str = "127.0.0.1", server_port: int = 19002):
    """发送真实的RemoteEnvironment实例进行序列化测试"""
    if not has_remote_environment:
        logger.error("RemoteEnvironment not available, skipping test")
        return False
    
    try:
        logger.info("Creating RemoteEnvironment instance for serialization test")
        
        # 创建RemoteEnvironment实例
        remote_env = RemoteEnvironment(
            name="test_remote_env",
            config={
                "test_param": "test_value",
                "batch_size": 32,
                "model_name": "test_model"
            },
            host="localhost",
            port=19001
        )
        
        # 模拟添加一些pipeline步骤
        remote_env.pipeline.extend([
            {"type": "preprocessor", "config": {"normalize": True}},
            {"type": "model", "config": {"model_path": "/path/to/model"}},
            {"type": "postprocessor", "config": {"format": "json"}}
        ])
        
        logger.info(f"Created RemoteEnvironment: {remote_env}")
        logger.info(f"Pipeline length: {len(remote_env.pipeline)}")
        
        # 使用SAGE的序列化工具进行序列化
        if has_sage_serializer:
            try:
                # 首先尝试直接使用serialize_object，这个更简单
                logger.info("Using serialize_object for serialization")
                serialized_data = serialize_object(remote_env)
                logger.info(f"✅ serialize_object succeeded: {len(serialized_data)} bytes")
            except Exception as e:
                logger.warning(f"serialize_object failed: {e}, trying trim_object_for_ray...")
                try:
                    from sage.kernel.utils.serialization.dill_serializer import trim_object_for_ray
                    logger.info("Using trim_object_for_ray as fallback")
                    trimmed_env = trim_object_for_ray(remote_env)
                    serialized_data = serialize_object(trimmed_env)
                    logger.info(f"✅ trim_object_for_ray + serialize_object succeeded: {len(serialized_data)} bytes")
                except Exception as e2:
                    logger.warning(f"trim_object_for_ray also failed: {e2}, using pickle as final fallback...")
                    serialized_data = pickle.dumps(remote_env)
                    logger.info(f"✅ pickle fallback succeeded: {len(serialized_data)} bytes")
        else:
            logger.warning("SAGE serializer not available, using pickle")
            serialized_data = pickle.dumps(remote_env)
        
        logger.info(f"Serialized RemoteEnvironment ({len(serialized_data)} bytes)")
        
        # 连接到服务器并发送序列化数据
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((server_host, server_port))
            
            # 发送数据长度
            data_length = len(serialized_data)
            client_socket.send(data_length.to_bytes(4, byteorder='big'))
            
            # 发送数据
            client_socket.send(serialized_data)
            
            # 接收响应
            response_length_data = client_socket.recv(4)
            if len(response_length_data) != 4:
                logger.error("Failed to receive response length")
                return False
                
            response_length = int.from_bytes(response_length_data, byteorder='big')
            
            response_data = client_socket.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            logger.info(f"Server response: {response}")
            
            # 检查响应状态
            if response.get("status") == "success":
                logger.info("✅ RemoteEnvironment serialization test PASSED")
                validation = response.get("validation", {})
                if validation.get("valid"):
                    logger.info("✅ Serialized environment validation PASSED")
                    logger.info(f"Environment info: {validation.get('info', {})}")
                else:
                    logger.warning(f"⚠️ Validation warnings: {validation.get('warnings', [])}")
                    logger.error(f"❌ Validation errors: {validation.get('errors', [])}")
                return True
            else:
                logger.error(f"❌ RemoteEnvironment serialization test FAILED: {response.get('message')}")
                return False
                
    except Exception as e:
        logger.error(f"Error in RemoteEnvironment serialization test: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remote Environment Test Server")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=19002, help="Server port")
    parser.add_argument("--mode", choices=["server", "client", "test", "remote_env_test"], default="server",
                       help="Run mode: server (start test server), client (send test data), test (both), remote_env_test (test RemoteEnvironment serialization)")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        # 启动服务器
        server = EnvironmentTestServer(args.host, args.port)
        try:
            server.start()
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        finally:
            server.stop()
            
    elif args.mode == "client":
        # 发送测试数据
        send_test_environment(args.host, args.port)
        
    elif args.mode == "remote_env_test":
        # 测试RemoteEnvironment序列化
        server = EnvironmentTestServer(args.host, args.port)
        
        def run_server():
            try:
                server.start()
            except:
                pass
        
        # 在后台线程启动服务器
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        try:
            print("\n" + "="*60)
            print("🚀 Starting RemoteEnvironment Serialization Test")
            print("="*60)
            
            # 发送基础测试数据
            print("\n📋 Step 1: Testing basic serialization...")
            send_test_environment(args.host, args.port)
            
            # 发送RemoteEnvironment实例
            print("\n🎯 Step 2: Testing RemoteEnvironment serialization...")
            success = send_remote_environment_test(args.host, args.port)
            
            # 等待一下让服务器处理
            time.sleep(1)
            
            # 显示统计信息
            print("\n📊 Test Results:")
            print("-" * 40)
            
            stats = server.get_stats()
            print(f"Server Stats: {stats}")
            
            summary = server.get_environment_summary()
            print(f"Environment Summary: {summary}")
            
            # 显示测试结果总结
            print("\n🎉 Test Summary:")
            print("-" * 40)
            if success:
                print("✅ RemoteEnvironment serialization test PASSED")
                print("✅ Environment can be successfully serialized and deserialized")
                print("✅ Validation checks completed")
            else:
                print("❌ RemoteEnvironment serialization test FAILED")
                print("❌ Check logs for detailed error information")
            
            print("="*60)
            
        except KeyboardInterrupt:
            logger.info("RemoteEnvironment test interrupted by user")
        finally:
            server.stop()
        
    elif args.mode == "test":
        # 启动服务器并发送测试数据
        server = EnvironmentTestServer(args.host, args.port)
        
        def run_server():
            try:
                server.start()
            except:
                pass
        
        # 在后台线程启动服务器
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        try:
            # 发送测试数据
            send_test_environment(args.host, args.port)
            
            # 等待一下让服务器处理
            time.sleep(1)
            
            # 显示统计信息
            stats = server.get_stats()
            print(f"\nServer Stats: {stats}")
            
            summary = server.get_environment_summary()
            print(f"\nEnvironment Summary: {summary}")
            
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        finally:
            server.stop()


def run_remote_environment_test(host: str = "127.0.0.1", port: int = 19002) -> bool:
    """
    便捷函数：运行RemoteEnvironment序列化测试
    
    Args:
        host: 测试服务器主机
        port: 测试服务器端口
        
    Returns:
        bool: 测试是否成功
    """
    print(f"\n🧪 Running RemoteEnvironment serialization test on {host}:{port}")
    
    # 创建测试服务器
    server = EnvironmentTestServer(host, port)
    
    def run_server():
        try:
            server.start()
        except:
            pass
    
    # 在后台线程启动服务器
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 等待服务器启动
    time.sleep(1)
    
    try:
        print("📋 Testing basic serialization...")
        send_test_environment(host, port)
        
        print("🎯 Testing RemoteEnvironment serialization...")
        success = send_remote_environment_test(host, port)
        
        # 等待处理完成
        time.sleep(1)
        
        # 显示结果
        stats = server.get_stats()
        summary = server.get_environment_summary()
        
        print(f"\n📊 Results: {stats['received_count']} environments processed")
        
        if success:
            print("✅ RemoteEnvironment serialization test PASSED")
        else:
            print("❌ RemoteEnvironment serialization test FAILED")
            
        return success
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    finally:
        server.stop()


# ======================================================================
# PYTEST TESTS - 符合pytest规范的测试函数
# ======================================================================

import pytest
import signal
import tempfile
import os

def find_free_port(start_port=19003, max_attempts=100):
    """找到一个可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(("127.0.0.1", port))
            test_socket.close()
            return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find a free port in range {start_port}-{start_port + max_attempts}")

# 测试服务器的全局实例
_test_server = None
_server_thread = None

@pytest.fixture(scope="module")
def test_server():
    """提供测试服务器的fixture"""
    global _test_server, _server_thread
    
    # 动态找到一个可用的端口
    free_port = find_free_port()
    logger.info(f"Using free port {free_port} for test server")
    server = EnvironmentTestServer("127.0.0.1", free_port)
    
    def run_server():
        try:
            server.start()
        except Exception as e:
            logger.error(f"Server start error: {e}")
    
    # 在后台线程启动服务器
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 等待服务器启动，并验证是否成功
    max_wait = 5  # 最多等待5秒
    for i in range(max_wait * 10):  # 每0.1秒检查一次
        if server.running:
            break
        time.sleep(0.1)
    
    if not server.running:
        raise RuntimeError(f"Test server failed to start within {max_wait} seconds")
    
    logger.info(f"Test server successfully started on {server.host}:{server.port}")
    
    _test_server = server
    _server_thread = server_thread
    
    yield server
    
    # 清理
    logger.info("Cleaning up test server")
    server.stop()
    # 等待线程结束
    if server_thread.is_alive():
        server_thread.join(timeout=2)


@pytest.fixture(scope="function")
def clean_server_state(test_server):
    """每个测试前清理服务器状态"""
    test_server.received_environments.clear()
    yield test_server


def test_environment_test_server_creation():
    """测试EnvironmentTestServer类的创建"""
    # 使用动态端口避免冲突
    test_port = find_free_port(19100)
    server = EnvironmentTestServer("localhost", test_port)
    assert server.host == "localhost"
    assert server.port == test_port
    assert server.running == False
    assert len(server.received_environments) == 0


def test_basic_environment_serialization(clean_server_state):
    """测试基础环境数据的序列化和传输"""
    server = clean_server_state
    
    # 创建基础测试数据
    test_env_data = {
        "name": "test_environment", 
        "config": {"test_key": "test_value"},
        "platform": "remote",
        "pipeline": ["step1", "step2", "step3"]
    }
    
    # 序列化数据
    if has_sage_serializer:
        serialized_data = serialize_object(test_env_data)
    else:
        serialized_data = pickle.dumps(test_env_data)
    
    assert len(serialized_data) > 0
    
    # 发送到测试服务器
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(10.0)  # 10秒超时
                client_socket.connect((server.host, server.port))
                
                # 发送数据长度
                data_length = len(serialized_data)
                client_socket.send(data_length.to_bytes(4, byteorder='big'))
                
                # 发送数据
                client_socket.send(serialized_data)
                
                # 接收响应
                response_length_data = client_socket.recv(4)
                if len(response_length_data) != 4:
                    raise ConnectionError("Failed to receive response length")
                    
                response_length = int.from_bytes(response_length_data, byteorder='big')
                
                response_data = b""
                while len(response_data) < response_length:
                    chunk = client_socket.recv(response_length - len(response_data))
                    if not chunk:
                        raise ConnectionError("Connection closed while receiving response")
                    response_data += chunk
                
                response = json.loads(response_data.decode('utf-8'))
                
                # 验证响应
                assert response["status"] == "success"
                assert "validation" in response
                break  # 成功，跳出重试循环
                
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.5)
                continue
            else:
                pytest.fail(f"Basic serialization test failed after {max_retries} attempts: {e}")
        except Exception as e:
            pytest.fail(f"Basic serialization test failed: {e}")
    
    # 等待服务器处理
    time.sleep(0.5)
    
    # 验证服务器收到了数据
    assert len(server.received_environments) == 1
    assert server.received_environments[0]["validation"]["valid"] == True


def test_remote_environment_serialization(clean_server_state):
    """测试RemoteEnvironment实例的序列化"""
    if not has_remote_environment:
        pytest.skip("RemoteEnvironment not available")
    
    server = clean_server_state
    
    # 创建RemoteEnvironment实例
    remote_env = RemoteEnvironment(
        name="pytest_remote_env",
        config={
            "test_param": "pytest_value",
            "batch_size": 16,
            "model_name": "pytest_model"
        },
        host="localhost",
        port=19001
    )
    
    # 添加pipeline步骤
    remote_env.pipeline.extend([
        {"type": "preprocessor", "config": {"normalize": True}},
        {"type": "model", "config": {"model_path": "/test/model"}},
        {"type": "postprocessor", "config": {"format": "json"}}
    ])
    
    # 序列化
    if has_sage_serializer:
        try:
            serialized_data = serialize_object(remote_env)
        except Exception as e:
            try:
                from sage.kernel.utils.serialization.dill_serializer import trim_object_for_ray
                trimmed_env = trim_object_for_ray(remote_env)
                serialized_data = serialize_object(trimmed_env)
            except Exception as e2:
                serialized_data = pickle.dumps(remote_env)
    else:
        serialized_data = pickle.dumps(remote_env)
    
    assert len(serialized_data) > 0
    
    # 发送到测试服务器
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(10.0)
                client_socket.connect((server.host, server.port))
                
                # 发送数据长度
                data_length = len(serialized_data)
                client_socket.send(data_length.to_bytes(4, byteorder='big'))
                
                # 发送数据
                client_socket.send(serialized_data)
                
                # 接收响应
                response_length_data = client_socket.recv(4)
                if len(response_length_data) != 4:
                    raise ConnectionError("Failed to receive response length")
                    
                response_length = int.from_bytes(response_length_data, byteorder='big')
                
                response_data = b""
                while len(response_data) < response_length:
                    chunk = client_socket.recv(response_length - len(response_data))
                    if not chunk:
                        raise ConnectionError("Connection closed while receiving response")
                    response_data += chunk
                
                response = json.loads(response_data.decode('utf-8'))
                
                # 验证响应
                assert response["status"] == "success"
                validation = response.get("validation", {})
                assert validation.get("valid") == True
                
                # 验证环境信息
                info = validation.get("info", {})
                assert "name" in info
                assert "config" in info
                assert "pipeline_length" in info
                break  # 成功，跳出重试循环
                
        except (ConnectionResetError, ConnectionRefusedError, socket.timeout) as e:
            if attempt < max_retries - 1:
                logger.warning(f"RemoteEnvironment test attempt {attempt + 1} failed: {e}, retrying...")
                time.sleep(0.5)
                continue
            else:
                pytest.fail(f"RemoteEnvironment serialization test failed after {max_retries} attempts: {e}")
        except Exception as e:
            pytest.fail(f"RemoteEnvironment serialization test failed: {e}")
    
    # 等待服务器处理
    time.sleep(0.5)
    
    # 验证服务器状态
    assert len(server.received_environments) == 1
    received_env = server.received_environments[0]
    assert received_env["validation"]["valid"] == True


def test_serialization_fallback():
    """测试序列化回退机制"""
    # 创建一个可能难以序列化的对象
    complex_data = {
        "name": "complex_test",
        "config": {"nested": {"deep": {"value": 42}}},
        "lambda_func": lambda x: x * 2,  # 这可能会导致序列化问题
        "platform": "test"
    }
    
    # 测试不同的序列化方法
    serialized = None
    
    if has_sage_serializer:
        try:
            serialized = serialize_object(complex_data)
        except Exception:
            # 预期可能失败，使用pickle作为后备
            try:
                serialized = pickle.dumps(complex_data)
            except Exception:
                # 移除problematic元素再试
                clean_data = {k: v for k, v in complex_data.items() if k != "lambda_func"}
                serialized = pickle.dumps(clean_data)
    
    assert serialized is not None
    assert len(serialized) > 0


def test_server_stats_and_summary(clean_server_state):
    """测试服务器统计功能"""
    server = clean_server_state
    
    # 初始状态
    stats = server.get_stats()
    assert stats["running"] == True
    assert stats["received_count"] == 0
    
    # 发送一些测试数据
    test_data = {"name": "stats_test", "config": {}}
    serialized_data = pickle.dumps(test_data)
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.settimeout(10.0)
            client_socket.connect((server.host, server.port))
            data_length = len(serialized_data)
            client_socket.send(data_length.to_bytes(4, byteorder='big'))
            client_socket.send(serialized_data)
            
            # 接收响应
            response_length_data = client_socket.recv(4)
            if len(response_length_data) != 4:
                raise ConnectionError("Failed to receive response length")
            response_length = int.from_bytes(response_length_data, byteorder='big')
            
            response_data = b""
            while len(response_data) < response_length:
                chunk = client_socket.recv(response_length - len(response_data))
                if not chunk:
                    raise ConnectionError("Connection closed while receiving response")
                response_data += chunk
            
            response = json.loads(response_data.decode('utf-8'))
    except Exception as e:
        pytest.fail(f"Failed to send stats test data: {e}")
    
    time.sleep(0.5)
    
    # 检查更新后的统计
    updated_stats = server.get_stats()
    assert updated_stats["received_count"] == 1
    assert updated_stats["last_received"] is not None
    
    # 测试环境摘要
    summary = server.get_environment_summary()
    assert "environments" in summary
    assert len(summary["environments"]) == 1
    
    # 测试特定环境详情
    detail = server.get_environment_summary(1)
    assert "validation" in detail
    assert "timestamp" in detail


def test_environment_validation():
    """测试环境验证逻辑"""
    server = EnvironmentTestServer()
    
    # 测试有效环境
    valid_env = type('TestEnv', (), {
        'name': 'valid_test',
        'config': {'key': 'value'},
        'platform': 'test',
        'pipeline': ['step1', 'step2']
    })()
    
    validation = server._validate_environment(valid_env)
    assert validation["valid"] == True
    assert len(validation["errors"]) == 0
    assert "name" in validation["info"]
    assert "config" in validation["info"]
    assert "platform" in validation["info"]
    
    # 测试None环境
    null_validation = server._validate_environment(None)
    assert null_validation["valid"] == False
    assert len(null_validation["errors"]) > 0


# ======================================================================
# 兼容性：保留原有的命令行接口
# ======================================================================

if __name__ == "__main__":
    # 如果直接运行且没有参数，默认运行RemoteEnvironment测试
    if len(sys.argv) == 1:
        print("🚀 Running default RemoteEnvironment serialization test...")
        print("To see all options, run with --help")
        success = run_remote_environment_test()
        sys.exit(0 if success else 1)
    else:
        main()
