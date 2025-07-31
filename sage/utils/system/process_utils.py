"""
Process Management Utilities

System-level process operations independent of any specific class context.
These utilities provide reusable functions for process discovery, termination,
and management operations.
"""

import psutil
import subprocess
import getpass
import time
from typing import List, Dict, Any, Optional


def find_processes_by_name(process_names: List[str]) -> List[psutil.Process]:
    """
    根据进程名称列表查找进程
    
    Args:
        process_names: 要搜索的进程名称列表
        
    Returns:
        List[psutil.Process]: 匹配的进程对象列表
    """
    matching_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_info = proc.info
            proc_name = proc_info['name']
            cmdline = ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else ''
            
            # 检查进程名称或命令行是否匹配
            for target_name in process_names:
                if (target_name in proc_name or 
                    target_name in cmdline):
                    matching_processes.append(proc)
                    break
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    return matching_processes


def get_process_info(pid: int) -> Dict[str, Any]:
    """
    获取进程详细信息
    
    Args:
        pid: 进程ID
        
    Returns:
        Dict: 进程信息字典
    """
    try:
        proc = psutil.Process(pid)
        return {
            "pid": pid,
            "name": proc.name(),
            "user": proc.username(),
            "cmdline": ' '.join(proc.cmdline()),
            "status": proc.status(),
            "cpu_percent": proc.cpu_percent(),
            "memory_percent": proc.memory_percent(),
            "create_time": proc.create_time()
        }
    except psutil.NoSuchProcess:
        return {
            "pid": pid, 
            "name": "N/A", 
            "user": "N/A", 
            "cmdline": "N/A", 
            "status": "Not Found",
            "error": "Process not found"
        }
    except psutil.AccessDenied:
        return {
            "pid": pid, 
            "name": "N/A", 
            "user": "N/A", 
            "cmdline": "N/A", 
            "status": "Access Denied",
            "error": "Access denied"
        }
    except Exception as e:
        return {
            "pid": pid,
            "error": f"Error getting process info: {e}"
        }


def terminate_process(pid: int, timeout: int = 5) -> Dict[str, Any]:
    """
    优雅地终止进程（先TERM，后KILL）
    
    Args:
        pid: 进程ID
        timeout: 等待终止的超时时间（秒）
        
    Returns:
        Dict: 终止结果
    """
    try:
        proc = psutil.Process(pid)
        proc_info = get_process_info(pid)
        
        # 先尝试优雅终止
        proc.terminate()
        
        try:
            proc.wait(timeout=timeout)
            return {
                "success": True,
                "method": "terminate",
                "pid": pid,
                "process_info": proc_info,
                "message": f"Process {pid} terminated gracefully"
            }
        except psutil.TimeoutExpired:
            # 超时后强制杀死
            proc.kill()
            proc.wait(timeout=2)
            return {
                "success": True,
                "method": "kill",
                "pid": pid,
                "process_info": proc_info,
                "message": f"Process {pid} killed after timeout"
            }
            
    except psutil.NoSuchProcess:
        return {
            "success": True,  # 进程已经不存在，视为成功
            "method": "already_gone",
            "pid": pid,
            "message": f"Process {pid} already terminated"
        }
    except psutil.AccessDenied:
        return {
            "success": False,
            "method": "access_denied",
            "pid": pid,
            "error": f"Access denied to terminate process {pid}"
        }
    except Exception as e:
        return {
            "success": False,
            "method": "error",
            "pid": pid,
            "error": f"Error terminating process {pid}: {e}"
        }


def terminate_processes_by_name(process_names: List[str], 
                              timeout: int = 5) -> Dict[str, Any]:
    """
    根据进程名称终止所有匹配的进程
    
    Args:
        process_names: 要终止的进程名称列表
        timeout: 每个进程的终止超时时间（秒）
        
    Returns:
        Dict: 终止结果汇总
    """
    processes = find_processes_by_name(process_names)
    
    results = {
        "total_found": len(processes),
        "terminated": [],
        "failed": [],
        "already_gone": []
    }
    
    for proc in processes:
        result = terminate_process(proc.pid, timeout)
        
        if result["success"]:
            if result["method"] == "already_gone":
                results["already_gone"].append(result)
            else:
                results["terminated"].append(result)
        else:
            results["failed"].append(result)
    
    results["success"] = len(results["failed"]) == 0
    return results


def kill_process_with_sudo(pid: int, sudo_password: Optional[str] = None) -> Dict[str, Any]:
    """
    使用sudo权限强制杀死进程
    
    Args:
        pid: 进程ID
        sudo_password: sudo密码（如果为None则会提示输入）
        
    Returns:
        Dict: 操作结果
    """
    if sudo_password is None:
        sudo_password = getpass.getpass("Enter sudo password: ")
    
    if not sudo_password.strip():
        return {
            "success": False,
            "pid": pid,
            "error": "No sudo password provided"
        }
    
    try:
        result = subprocess.run(
            ['sudo', '-S', 'kill', '-9', str(pid)],
            input=sudo_password + '\n',
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "pid": pid,
                "method": "sudo_kill",
                "message": f"Successfully killed process {pid} with sudo"
            }
        else:
            return {
                "success": False,
                "pid": pid,
                "error": f"Failed to kill process {pid} with sudo: {result.stderr.strip()}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "pid": pid,
            "error": f"Timeout while trying to kill process {pid} with sudo"
        }
    except Exception as e:
        return {
            "success": False,
            "pid": pid,
            "error": f"Error killing process {pid} with sudo: {e}"
        }


def verify_sudo_password(password: str) -> bool:
    """
    验证sudo密码是否正确
    
    Args:
        password: 要验证的密码
        
    Returns:
        bool: 密码是否正确
    """
    try:
        result = subprocess.run(
            ['sudo', '-S', 'echo', 'password_test'],
            input=password + '\n',
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def get_process_children(pid: int, recursive: bool = True) -> List[int]:
    """
    获取进程的所有子进程ID
    
    Args:
        pid: 父进程ID
        recursive: 是否递归获取子进程的子进程
        
    Returns:
        List[int]: 子进程ID列表
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=recursive)
        return [child.pid for child in children]
    except psutil.NoSuchProcess:
        return []
    except Exception:
        return []


def terminate_process_tree(pid: int, timeout: int = 5) -> Dict[str, Any]:
    """
    终止进程及其所有子进程
    
    Args:
        pid: 根进程ID
        timeout: 每个进程的终止超时时间（秒）
        
    Returns:
        Dict: 终止结果
    """
    # 获取所有子进程
    children_pids = get_process_children(pid, recursive=True)
    all_pids = children_pids + [pid]  # 先杀子进程，最后杀父进程
    
    results = {
        "root_pid": pid,
        "total_processes": len(all_pids),
        "terminated": [],
        "failed": [],
        "already_gone": []
    }
    
    # 终止所有进程
    for current_pid in all_pids:
        result = terminate_process(current_pid, timeout)
        
        if result["success"]:
            if result["method"] == "already_gone":
                results["already_gone"].append(result)
            else:
                results["terminated"].append(result)
        else:
            results["failed"].append(result)
    
    results["success"] = len(results["failed"]) == 0
    return results


def wait_for_process_termination(pid: int, timeout: int = 10) -> bool:
    """
    等待进程终止
    
    Args:
        pid: 进程ID
        timeout: 超时时间（秒）
        
    Returns:
        bool: True表示进程已终止，False表示超时
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            proc = psutil.Process(pid)
            if not proc.is_running():
                return True
        except psutil.NoSuchProcess:
            return True
        
        time.sleep(0.5)
    
    return False


def get_system_process_summary() -> Dict[str, Any]:
    """
    获取系统进程概要信息
    
    Returns:
        Dict: 系统进程统计信息
    """
    try:
        all_processes = list(psutil.process_iter(['pid', 'name', 'status', 'username']))
        
        summary = {
            "total_processes": len(all_processes),
            "by_status": {},
            "by_user": {},
            "memory_usage": psutil.virtual_memory()._asdict(),
            "cpu_usage": psutil.cpu_percent(interval=1)
        }
        
        # 按状态统计
        for proc in all_processes:
            try:
                status = proc.info['status']
                summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
                
                user = proc.info['username']
                summary["by_user"][user] = summary["by_user"].get(user, 0) + 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return summary
        
    except Exception as e:
        return {"error": f"Failed to get process summary: {e}"}


def is_process_running(pid: int) -> bool:
    """
    检查进程是否正在运行
    
    Args:
        pid: 进程ID
        
    Returns:
        bool: True表示进程正在运行
    """
    try:
        proc = psutil.Process(pid)
        return proc.is_running()
    except psutil.NoSuchProcess:
        return False
    except Exception:
        return False
