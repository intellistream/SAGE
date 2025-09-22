"""
Network and Port Management Utilities

System-level network operations independent of any specific class context.
These utilities provide reusable functions for port management, network checks,
and TCP communication operations.
"""
import psutil
import socket
import subprocess
import time
import json
from typing import List, Dict, Any, Optional, Tuple


def is_port_occupied(host: str, port: int) -> bool:
    """
    检查端口是否被占用
    
    Args:
        host: 主机地址
        port: 端口号
        
    Returns:
        bool: True表示端口被占用，False表示端口空闲
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def check_port_binding_permission(host: str, port: int) -> Dict[str, Any]:
    """
    检查端口绑定权限
    
    Args:
        host: 主机地址
        port: 端口号
        
    Returns:
        Dict: 包含检查结果的字典
            - success: bool, 是否成功
            - error: str, 错误类型（如果失败）
            - message: str, 详细信息
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return {
                "success": True, 
                "message": f"Port {port} binding permission verified"
            }
    except PermissionError:
        return {
            "success": False, 
            "error": "permission_denied",
            "message": f"Permission denied to bind port {port}"
        }
    except OSError as e:
        if e.errno == 98:  # Address already in use
            return {
                "success": False, 
                "error": "port_in_use",
                "message": f"Port {port} is still in use"
            }
        return {
            "success": False, 
            "error": "os_error", 
            "message": f"Error checking port binding permission: {e}"
        }
    except Exception as e:
        return {
            "success": False, 
            "error": "unknown", 
            "message": f"Unexpected error checking port permission: {e}"
        }


def wait_for_port_release(host: str, port: int, timeout: int = 10, check_interval: float = 1) -> bool:
    """
    等待端口释放
    
    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        bool: True表示端口已释放，False表示超时
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if not is_port_occupied(host, port):
            return True
        time.sleep(check_interval)
    
    return False


def find_port_processes(port: int) -> List[psutil.Process]:
    """
    查找占用指定端口的进程列表
    使用多种方法确保找到所有相关进程
    
    Args:
        port: 要查询的端口号
        
    Returns:
        List[psutil.Process]: 占用该端口的进程列表
    """
    pids = set()
    
    # Method 1: lsof
    pids.update(_find_processes_with_lsof(port))
    
    # Method 2: netstat
    pids.update(_find_processes_with_netstat(port))
    
    # Method 3: fuser
    pids.update(_find_processes_with_fuser(port))
    
    # 将PID转换为psutil.Process对象
    processes = []
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            # 检查进程是否仍然存在
            if proc.is_running():
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # 进程不存在或无访问权限，跳过
            continue
    
    return processes


def _find_processes_with_lsof(port: int) -> List[int]:
    """
    使用lsof查找占用端口的进程
    
    Args:
        port: 端口号
        
    Returns:
        List[int]: 进程ID列表
    """
    try:
        result = subprocess.run(
            ['lsof', '-t', f'-i:{port}'],
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('p'):
                    line = line[1:]  # Remove 'p' prefix
                if line.isdigit():
                    pids.append(int(line))
            return pids
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    return []


def _find_processes_with_netstat(port: int) -> List[int]:
    """
    使用netstat查找占用端口的进程
    
    Args:
        port: 端口号
        
    Returns:
        List[int]: 进程ID列表
    """
    try:
        result = subprocess.run(
            ['netstat', '-tlnp'],
            capture_output=True, 
            text=True, 
            timeout=5
        )
        pids = []
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) > 6 and '/' in parts[6]:
                        pid_str = parts[6].split('/')[0]
                        if pid_str.isdigit():
                            pids.append(int(pid_str))
        return pids
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        # netstat命令不存在或执行失败
        pass
    return []


def _find_processes_with_fuser(port: int) -> List[int]:
    """
    使用fuser查找占用端口的进程
    
    Args:
        port: 端口号
        
    Returns:
        List[int]: 进程ID列表
    """
    try:
        result = subprocess.run(
            ['fuser', f'{port}/tcp'],
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return [
                int(pid.strip()) 
                for pid in result.stdout.strip().split() 
                if pid.strip().isdigit()
            ]
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    return []


def send_tcp_health_check(host: str, port: int, 
                         request: Dict[str, Any],
                         timeout: int = 5) -> Dict[str, Any]:
    """
    发送TCP健康检查请求
    
    Args:
        host: 目标主机
        port: 目标端口
        request: 要发送的请求数据
        timeout: 超时时间（秒）
        
    Returns:
        Dict: 响应数据或错误信息
    """
    try:
        # Validate JSON serialization upfront
        request_data = json.dumps(request).encode('utf-8')
    except (TypeError, ValueError) as e:
        # Re-raise JSON serialization errors
        raise e
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))
            
            # 发送请求
            length_data = len(request_data).to_bytes(4, byteorder='big')
            sock.sendall(length_data + request_data)
            
            # 接收响应
            response_length_data = sock.recv(4)
            if len(response_length_data) != 4:
                return {"status": "error", "message": "Invalid response format"}
            
            response_length = int.from_bytes(response_length_data, byteorder='big')
            response_data = b''
            while len(response_data) < response_length:
                chunk = sock.recv(min(response_length - len(response_data), 8192))
                if not chunk:
                    break
                response_data += chunk
            
            if len(response_data) != response_length:
                return {"status": "error", "message": "Incomplete response received"}
                
            return json.loads(response_data.decode('utf-8'))
            
    except socket.error as e:
        return {"status": "error", "message": f"Connection failed: {e}"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON response: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Health check failed: {e}"}


def allocate_free_port(host: str = "127.0.0.1", 
                      port_range: Tuple[int, int] = (19200, 20000)) -> int:
    """
    分配一个空闲端口
    
    Args:
        host: 绑定的主机地址
        port_range: 端口范围 (start, end)
        
    Returns:
        int: 分配的端口号
        
    Raises:
        RuntimeError: 如果无法分配端口
    """
    start_port, end_port = port_range
    
    # 尝试从指定范围分配端口
    for port in range(start_port, end_port):
        if not is_port_occupied(host, port):
            # 双重检查：尝试绑定端口
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, port))
                    return port
            except OSError:
                continue
    
    # 如果范围内都被占用，使用系统分配
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            return s.getsockname()[1]
    except Exception as e:
        raise RuntimeError(f"Unable to allocate free port: {e}")


def aggressive_port_cleanup(port: int) -> Dict[str, Any]:
    """
    激进的端口清理 - 尝试杀死所有占用指定端口的进程
    
    Args:
        port: 要清理的端口号
        
    Returns:
        Dict: 清理结果
            - success: bool, 是否成功找到并终止进程
            - killed_pids: List[int], 被终止的进程ID列表
            - errors: List[str], 错误信息列表
    """
    import psutil
    
    result = {
        "success": False,
        "killed_pids": [],
        "errors": []
    }
    
    # 使用多种方法查找占用端口的进程
    all_pids = find_port_processes(port)
    
    if not all_pids:
        result["errors"].append("No processes found occupying the port")
        return result
    
    # 尝试杀死所有找到的进程
    for pid in all_pids:
        try:
            proc = psutil.Process(pid)
            
            # 先尝试优雅终止
            try:
                proc.terminate()
                proc.wait(timeout=2)
                result["killed_pids"].append(pid)
            except psutil.TimeoutExpired:
                # 超时后强制杀死
                proc.kill()
                proc.wait(timeout=2)
                result["killed_pids"].append(pid)
                
        except psutil.NoSuchProcess:
            # 进程已经不存在
            continue
        except psutil.AccessDenied:
            result["errors"].append(f"Access denied to kill process {pid}")
        except Exception as e:
            result["errors"].append(f"Error killing process {pid}: {e}")
    
    result["success"] = len(result["killed_pids"]) > 0
    return result


def get_host_ip() -> str:
    """
    自动获取本机可用于外部连接的IP地址
    
    Returns:
        str: IP地址
    """
    try:
        # 尝试连接到外部地址以获取本机IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def check_tcp_connection(host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
    """
    测试TCP连接
    
    Args:
        host: 目标主机
        port: 目标端口
        timeout: 超时时间（秒）
        
    Returns:
        Dict: 连接测试结果
    """
    try:
        start_time = time.time()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            elapsed_time = time.time() - start_time
            
            if result == 0:
                return {
                    "success": True,
                    "message": f"Connection to {host}:{port} successful",
                    "response_time": elapsed_time
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection to {host}:{port} failed (error code: {result})",
                    "response_time": elapsed_time
                }
    except socket.timeout:
        return {
            "success": False,
            "message": f"Connection timeout to {host}:{port}",
            "response_time": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {e}",
            "response_time": 0
        }
