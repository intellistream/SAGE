#!/usr/bin/env python3
"""
独立的Ray启动器
支持自动探测公网IP并启动Ray集群
"""

import os
import sys
import socket
import subprocess
import argparse
import time
import requests
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RayLauncher:
    """Ray集群启动器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 默认配置
        self.default_config = {
            'head_port': 10001,
            'dashboard_port': 8265,
            'client_port': 10002,
            'temp_dir': '/tmp/ray_shared',
            'object_store_memory': None,  # 自动检测
            'resources': {'jobmanager': 1.0},
            'include_dashboard': True,
            'dashboard_host': '0.0.0.0',
            'verbose': False,
            'auto_detect_ip': True,
            'preferred_interfaces': ['eth0', 'ens3', 'ens4', 'wlan0'],
            'fallback_ip_services': [
                'https://api.ipify.org',
                'https://httpbin.org/ip',
                'https://ifconfig.me/ip',
                'https://ipecho.net/plain'
            ]
        }
        
        # 合并配置
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
    
    def get_public_ip(self) -> Optional[str]:
        """获取机器的公网IP地址"""
        logger.info("Detecting public IP address...")
        
        # 方法1: 尝试从网络接口获取非本地IP
        local_ip = self._get_local_non_loopback_ip()
        if local_ip and not local_ip.startswith('127.') and not local_ip.startswith('169.254.'):
            logger.info(f"Found local non-loopback IP: {local_ip}")
            # 验证这个IP是否可以从外部访问
            if self._is_ip_accessible(local_ip):
                return local_ip
        
        # 方法2: 通过外部服务获取公网IP
        public_ip = self._get_public_ip_from_service()
        if public_ip:
            logger.info(f"Found public IP via external service: {public_ip}")
            return public_ip
        
        # 方法3: 使用UDP连接方式获取本机IP
        local_ip = self._get_ip_via_udp()
        if local_ip and not local_ip.startswith('127.'):
            logger.info(f"Found IP via UDP method: {local_ip}")
            return local_ip
        
        logger.warning("Could not detect public IP, falling back to localhost")
        return '127.0.0.1'
    
    def _get_local_non_loopback_ip(self) -> Optional[str]:
        """从本地网络接口获取非回环IP"""
        try:
            # 优先检查指定的网络接口
            import netifaces
            
            for interface in self.config['preferred_interfaces']:
                try:
                    if interface in netifaces.interfaces():
                        addrs = netifaces.ifaddresses(interface)
                        if netifaces.AF_INET in addrs:
                            for addr in addrs[netifaces.AF_INET]:
                                ip = addr['addr']
                                if not ip.startswith('127.') and not ip.startswith('169.254.'):
                                    return ip
                except Exception as e:
                    logger.debug(f"Error checking interface {interface}: {e}")
                    continue
            
            # 如果指定接口没找到，检查所有接口
            for interface in netifaces.interfaces():
                if interface in self.config['preferred_interfaces']:
                    continue  # 已经检查过了
                try:
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr in addrs[netifaces.AF_INET]:
                            ip = addr['addr']
                            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                                return ip
                except Exception as e:
                    logger.debug(f"Error checking interface {interface}: {e}")
                    continue
                    
        except ImportError:
            logger.debug("netifaces not available, using alternative method")
            
        # 备用方法：使用hostname解析
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if not ip.startswith('127.'):
                return ip
        except Exception as e:
            logger.debug(f"Error getting IP via hostname: {e}")
        
        return None
    
    def _get_public_ip_from_service(self) -> Optional[str]:
        """通过外部服务获取公网IP"""
        for service_url in self.config['fallback_ip_services']:
            try:
                logger.debug(f"Trying IP service: {service_url}")
                response = requests.get(service_url, timeout=5)
                
                if response.status_code == 200:
                    # 不同服务返回格式不同
                    if 'httpbin.org' in service_url:
                        data = response.json()
                        ip = data.get('origin', '').split(',')[0].strip()
                    else:
                        ip = response.text.strip()
                    
                    # 验证IP格式
                    if self._is_valid_ip(ip):
                        return ip
                        
            except Exception as e:
                logger.debug(f"Failed to get IP from {service_url}: {e}")
                continue
        
        return None
    
    def _get_ip_via_udp(self) -> Optional[str]:
        """通过UDP连接方式获取本机IP"""
        try:
            # 连接到Google DNS，不会实际发送数据，但可以获取本机IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                return ip
        except Exception as e:
            logger.debug(f"Error getting IP via UDP: {e}")
            return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def _is_ip_accessible(self, ip: str) -> bool:
        """检查IP是否可以被外部访问（简单检查）"""
        try:
            # 尝试绑定到这个IP地址
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((ip, 0))  # 绑定到任意可用端口
                return True
        except Exception as e:
            logger.debug(f"IP {ip} not accessible: {e}")
            return False
    
    def get_system_resources(self) -> Dict[str, Any]:
        """获取系统资源信息"""
        import psutil
        
        # 获取CPU核心数
        cpu_count = psutil.cpu_count(logical=True)
        
        # 获取内存信息
        memory = psutil.virtual_memory()
        total_memory_gb = memory.total / (1024**3)
        
        # 计算Ray对象存储内存（默认使用30%的系统内存）
        if not self.config['object_store_memory']:
            object_store_memory = int(memory.total * 0.3)
        else:
            object_store_memory = self.config['object_store_memory']
        
        return {
            'cpu_count': cpu_count,
            'total_memory_gb': total_memory_gb,
            'object_store_memory': object_store_memory,
            'available_memory_gb': memory.available / (1024**3)
        }
    
    def check_ports_available(self, ports: List[int]) -> Dict[int, bool]:
        """检查端口是否可用"""
        result = {}
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    result[port] = True
            except OSError:
                result[port] = False
        return result
    
    def find_available_port(self, start_port: int, max_attempts: int = 100) -> int:
        """查找可用端口"""
        for i in range(max_attempts):
            port = start_port + i
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        raise RuntimeError(f"Could not find available port starting from {start_port}")
    
    def is_ray_running(self) -> bool:
        """检查Ray是否已经在运行"""
        try:
            # 方法1: 使用ray status命令
            result = subprocess.run(['ray', 'status'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # 方法2: 检查Ray进程
        try:
            result = subprocess.run(['pgrep', '-f', 'ray.*raylet'], 
                                  capture_output=True, text=True)
            return result.returncode == 0 and result.stdout.strip()
        except FileNotFoundError:
            pass
        
        # 方法3: 检查端口占用
        head_port = self.config['head_port']
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', head_port))
                return result == 0
        except Exception:
            pass
        
        return False
    
    def stop_ray(self) -> bool:
        """停止Ray集群"""
        logger.info("Stopping Ray cluster...")
        
        try:
            # 尝试优雅停止
            result = subprocess.run(['ray', 'stop'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.info("Ray cluster stopped gracefully")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Failed to stop Ray gracefully, trying force stop...")
        
        # 强制停止Ray进程
        try:
            subprocess.run(['pkill', '-f', 'ray'], timeout=10)
            time.sleep(2)
            subprocess.run(['pkill', '-9', '-f', 'ray'], timeout=10)
            logger.info("Ray cluster force stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to force stop Ray: {e}")
            return False
    
    def start_ray_head(self) -> bool:
        """启动Ray头节点"""
        logger.info("Starting Ray head node...")
        
        # 检查是否已经在运行
        if self.is_ray_running():
            logger.info("Ray cluster is already running")
            return True
        
        # 获取系统资源
        resources = self.get_system_resources()
        logger.info(f"System resources: {resources}")
        
        # 获取IP地址
        if self.config['auto_detect_ip']:
            node_ip = self.get_public_ip()
        else:
            node_ip = '127.0.0.1'
        
        logger.info(f"Using node IP: {node_ip}")
        
        # 检查端口可用性
        required_ports = [
            self.config['head_port'],
            self.config['dashboard_port'],
            self.config['client_port']
        ]
        
        port_status = self.check_ports_available(required_ports)
        unavailable_ports = [port for port, available in port_status.items() if not available]
        
        if unavailable_ports:
            logger.warning(f"Ports {unavailable_ports} are not available, trying to find alternatives...")
            
            # 尝试找到可用端口
            if not port_status[self.config['head_port']]:
                self.config['head_port'] = self.find_available_port(self.config['head_port'])
                logger.info(f"Using alternative head port: {self.config['head_port']}")
            
            if not port_status[self.config['dashboard_port']]:
                self.config['dashboard_port'] = self.find_available_port(self.config['dashboard_port'])
                logger.info(f"Using alternative dashboard port: {self.config['dashboard_port']}")
        
        # 创建临时目录
        temp_dir = Path(self.config['temp_dir'])
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建Ray启动命令
        cmd = [
            'ray', 'start', '--head',
            f'--port={self.config["head_port"]}',
            f'--node-ip-address={node_ip}',
            f'--temp-dir={self.config["temp_dir"]}',
            f'--object-store-memory={resources["object_store_memory"]}'
        ]
        
        # 添加dashboard配置
        if self.config['include_dashboard']:
            cmd.extend([
                f'--dashboard-host={self.config["dashboard_host"]}',
                f'--dashboard-port={self.config["dashboard_port"]}'
            ])
        else:
            cmd.append('--disable-usage-stats')
        
        # 添加资源配置
        if self.config['resources']:
            resources_str = json.dumps(self.config['resources'])
            cmd.extend(['--resources', resources_str])
        
        # 添加详细输出
        if self.config['verbose']:
            cmd.append('--verbose')
        
        # 启动Ray
        logger.info(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Ray head node started successfully")
                logger.info(f"Ray output: {result.stdout}")
                
                # 等待Ray完全启动
                self._wait_for_ray_ready()
                
                # 显示连接信息
                self._show_connection_info(node_ip)
                
                return True
            else:
                logger.error(f"Failed to start Ray head node: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Ray startup timed out")
            return False
        except Exception as e:
            logger.error(f"Error starting Ray: {e}")
            return False
    
    def _wait_for_ray_ready(self, timeout: int = 30):
        """等待Ray集群完全启动"""
        logger.info("Waiting for Ray cluster to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(['ray', 'status'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and 'cluster_resources' in result.stdout.lower():
                    logger.info("Ray cluster is ready")
                    return
            except subprocess.TimeoutExpired:
                pass
            except FileNotFoundError:
                # Ray CLI不可用，尝试其他方法
                break
            
            time.sleep(2)
        
        logger.warning("Ray cluster readiness check timed out, but startup appears successful")
    
    def _show_connection_info(self, node_ip: str):
        """显示连接信息"""
        logger.info("=== Ray Cluster Connection Info ===")
        logger.info(f"Node IP: {node_ip}")
        logger.info(f"Head Port: {self.config['head_port']}")
        logger.info(f"Dashboard: http://{node_ip}:{self.config['dashboard_port']}")
        logger.info(f"Ray Address: ray://{node_ip}:{self.config['head_port']}")
        
        # 生成环境变量设置
        logger.info("\n=== Environment Variables ===")
        logger.info(f"export RAY_ADDRESS=ray://{node_ip}:{self.config['head_port']}")
        logger.info(f"export RAY_DASHBOARD_HOST={node_ip}")
        logger.info(f"export RAY_DASHBOARD_PORT={self.config['dashboard_port']}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取Ray集群状态"""
        status = {
            'running': False,
            'node_ip': None,
            'head_port': self.config['head_port'],
            'dashboard_port': self.config['dashboard_port'],
            'dashboard_url': None,
            'ray_address': None,
            'nodes': [],
            'resources': {}
        }
        
        if not self.is_ray_running():
            return status
        
        status['running'] = True
        
        # 获取节点IP
        if self.config['auto_detect_ip']:
            node_ip = self.get_public_ip()
        else:
            node_ip = '127.0.0.1'
        
        status['node_ip'] = node_ip
        status['dashboard_url'] = f"http://{node_ip}:{self.config['dashboard_port']}"
        status['ray_address'] = f"ray://{node_ip}:{self.config['head_port']}"
        
        # 尝试获取详细状态
        try:
            result = subprocess.run(['ray', 'status'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                status['raw_status'] = result.stdout
                # 解析状态信息（简单版本）
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'node(s)' in line.lower():
                        # 提取节点数量
                        import re
                        match = re.search(r'(\d+)\s+node', line)
                        if match:
                            status['node_count'] = int(match.group(1))
        except Exception as e:
            logger.debug(f"Error getting detailed status: {e}")
        
        return status


def install_dependencies():
    """安装必要的依赖"""
    logger.info("Checking and installing dependencies...")
    
    required_packages = ['psutil', 'requests']
    optional_packages = ['netifaces']
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
        except ImportError:
            logger.info(f"Optional package {package} not found, some features may be limited")
    
    if missing_packages:
        logger.info(f"Installing missing packages: {missing_packages}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            logger.info("Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    return True


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Ray集群启动器")
    
    parser.add_argument('command', nargs='?', default='start',
                       choices=['start', 'stop', 'restart', 'status', 'ip'],
                       help='操作命令')
    
    parser.add_argument('--head-port', type=int, default=10001,
                       help='Ray头节点端口')
    parser.add_argument('--dashboard-port', type=int, default=8265,
                       help='Ray Dashboard端口')
    parser.add_argument('--client-port', type=int, default=10002,
                       help='Ray客户端端口')
    parser.add_argument('--temp-dir', default='/tmp/ray_shared',
                       help='Ray临时目录')
    parser.add_argument('--no-dashboard', action='store_true',
                       help='禁用Ray Dashboard')
    parser.add_argument('--dashboard-host', default='0.0.0.0',
                       help='Dashboard监听地址')
    parser.add_argument('--no-auto-ip', action='store_true',
                       help='不自动检测IP，使用127.0.0.1')
    parser.add_argument('--verbose', action='store_true',
                       help='详细输出')
    parser.add_argument('--install-deps', action='store_true',
                       help='安装依赖包')
    
    args = parser.parse_args()
    
    # 安装依赖
    if args.install_deps:
        if not install_dependencies():
            sys.exit(1)
    
    # 配置
    config = {
        'head_port': args.head_port,
        'dashboard_port': args.dashboard_port,
        'client_port': args.client_port,
        'temp_dir': args.temp_dir,
        'include_dashboard': not args.no_dashboard,
        'dashboard_host': args.dashboard_host,
        'auto_detect_ip': not args.no_auto_ip,
        'verbose': args.verbose
    }
    
    launcher = RayLauncher(config)
    
    if args.command == 'start':
        success = launcher.start_ray_head()
        sys.exit(0 if success else 1)
    
    elif args.command == 'stop':
        success = launcher.stop_ray()
        sys.exit(0 if success else 1)
    
    elif args.command == 'restart':
        logger.info("Restarting Ray cluster...")
        launcher.stop_ray()
        time.sleep(3)
        success = launcher.start_ray_head()
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        status = launcher.get_status()
        print(json.dumps(status, indent=2))
    
    elif args.command == 'ip':
        ip = launcher.get_public_ip()
        print(f"Detected IP: {ip}")
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
