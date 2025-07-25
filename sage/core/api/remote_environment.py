from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Dict, Any
from pathlib import Path
import os
import sys
import subprocess
import json
from core.environment.base_environment import BaseEnvironment
from core.jobmanager_client import JobManagerClient
from utils.actor_wrapper import ActorWrapper
if TYPE_CHECKING:
    from jobmanager.job_manager import JobManager

class RemoteEnvironment(BaseEnvironment):
    """远程环境，通过客户端连接远程JobManager"""

    def __init__(self, name: str, config: dict | None = None, host: str = "127.0.0.1", port: int = 19001):
        super().__init__(name, config, platform="remote")
        
        # 设置远程连接配置
        self.daemon_host = host
        self.daemon_port = port
        
        # 更新配置
        self.config.update({
            "engine_host": self.daemon_host,
            "engine_port": self.daemon_port
        })
        
        # 初始化时尝试创建日志软链接
        self._log_symlink_created = False
        self._setup_log_symlink()

    @property
    def client(self) -> JobManagerClient:
        """获取远程JobManager客户端"""
        if self._engine_client is None:
            self._engine_client = JobManagerClient(
                host=self.daemon_host, 
                port=self.daemon_port
            )
        return self._engine_client

    @property
    def jobmanager(self) -> 'JobManager': # 是actorwrapper无感包着的
        """通过客户端获取远程JobManager句柄"""
        if self._jobmanager is None:
            self._jobmanager = self.client.get_actor_handle()
        return self._jobmanager

    def _setup_log_symlink(self):
        """创建远程JobManager日志目录到本地codebase的软链接"""
        try:
            # 获取项目根目录（SAGE目录）
            current_file = Path(__file__)
            project_root = None
            
            # 向上查找包含setup.py或pyproject.toml的目录
            for parent in current_file.parents:
                if (parent / "setup.py").exists() or (parent / "pyproject.toml").exists():
                    project_root = parent
                    break
            
            if not project_root:
                # 如果找不到，使用当前文件向上三级目录（sage_core/api -> sage_core -> SAGE）
                project_root = current_file.parent.parent.parent
            
            # 在项目根目录下的logs目录中创建软链接
            local_logs_dir = project_root / "logs"
            local_logs_dir.mkdir(exist_ok=True)
            
            # 远程日志软链接目标
            remote_log_symlink = local_logs_dir / "remote_jobmanager_latest"
            
            # 检查是否能连接到远程JobManager
            try:
                log_info = self.client.get_log_directory()
                
                if log_info.get("status") == "success":
                    remote_latest_link = log_info.get("latest_link", "/tmp/sage-jm/session_latest")
                    
                    # 如果软链接已存在，先删除
                    if remote_log_symlink.is_symlink() or remote_log_symlink.exists():
                        remote_log_symlink.unlink()
                    
                    # 创建软链接
                    remote_log_symlink.symlink_to(remote_latest_link)
                    self._log_symlink_created = True
                    
                    self.logger.info(f"Created symlink: {remote_log_symlink} -> {remote_latest_link}")
                    
                else:
                    self.logger.warning(f"Failed to get remote log directory: {log_info.get('message')}")
                    
            except Exception as e:
                self.logger.warning(f"Could not connect to remote JobManager for log symlink: {e}")
                
        except Exception as e:
            self.logger.warning(f"Failed to setup log symlink: {e}")

    def _get_local_environment_info(self) -> Dict[str, Any]:
        """获取本地环境信息"""
        try:
            env_info = {
                "python_version": sys.version,
                "python_executable": sys.executable,
                "platform": sys.platform,
                "python_path": sys.path,
                "virtual_env": os.environ.get("VIRTUAL_ENV"),
                "conda_env": os.environ.get("CONDA_DEFAULT_ENV"),
                "working_directory": os.getcwd(),
            }
            
            # 获取关键依赖版本
            try:
                import ray
                env_info["ray_version"] = ray.__version__
            except ImportError:
                env_info["ray_version"] = None
            
            try:
                import dill
                env_info["dill_version"] = dill.__version__
            except ImportError:
                env_info["dill_version"] = None
                
            # 获取 pip 环境信息
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    packages = json.loads(result.stdout)
                    env_info["installed_packages"] = {pkg["name"]: pkg["version"] for pkg in packages}
                else:
                    env_info["installed_packages"] = {}
            except Exception:
                env_info["installed_packages"] = {}
                
            return env_info
            
        except Exception as e:
            self.logger.warning(f"Failed to get local environment info: {e}")
            return {"error": str(e)}

    def _get_remote_environment_info(self) -> Dict[str, Any]:
        """获取远程 JobManager 环境信息"""
        try:
            # 通过客户端获取远程环境信息
            remote_info = self.client.get_actor_info()
            
            # 如果远程 JobManager 支持环境信息查询，获取详细信息
            if hasattr(self.jobmanager, 'get_environment_info'):
                remote_env = self.jobmanager.get_environment_info()
                remote_info.update(remote_env)
            
            return remote_info
            
        except Exception as e:
            self.logger.warning(f"Failed to get remote environment info: {e}")
            return {"error": str(e)}

    def _validate_environment_compatibility(self) -> Dict[str, Any]:
        """验证本地和远程环境的兼容性"""
        local_env = self._get_local_environment_info()
        remote_env = self._get_remote_environment_info()
        
        compatibility_result = {
            "compatible": True,
            "warnings": [],
            "errors": [],
            "local_env": local_env,
            "remote_env": remote_env
        }
        
        # 检查 Python 版本兼容性
        if "python_version" in local_env and "python_version" in remote_env:
            local_py_version = local_env["python_version"].split()[0]
            remote_py_version = remote_env.get("python_version", "").split()[0] if remote_env.get("python_version") else None
            
            if remote_py_version and local_py_version != remote_py_version:
                compatibility_result["warnings"].append(
                    f"Python version mismatch: local={local_py_version}, remote={remote_py_version}"
                )
        
        # 检查关键依赖版本
        critical_deps = ["ray_version", "dill_version"]
        for dep in critical_deps:
            local_version = local_env.get(dep)
            remote_version = remote_env.get(dep)
            
            if local_version and remote_version and local_version != remote_version:
                compatibility_result["warnings"].append(
                    f"{dep} mismatch: local={local_version}, remote={remote_version}"
                )
        
        # 检查虚拟环境
        local_venv = local_env.get("virtual_env") or local_env.get("conda_env")
        remote_venv = remote_env.get("virtual_env") or remote_env.get("conda_env")
        
        if local_venv != remote_venv:
            compatibility_result["warnings"].append(
                f"Virtual environment mismatch: local={local_venv}, remote={remote_venv}"
            )
        
        # 如果有错误，标记为不兼容
        if compatibility_result["errors"]:
            compatibility_result["compatible"] = False
        
        return compatibility_result

    def _attempt_environment_alignment(self, compatibility_result: Dict[str, Any]) -> bool:
        """尝试环境对齐"""
        if compatibility_result["compatible"] and not compatibility_result["warnings"]:
            return True
        
        self.logger.info("Attempting environment alignment...")
        
        try:
            local_env = compatibility_result["local_env"]
            remote_env = compatibility_result["remote_env"]
            
            # 方案1: 尝试使用相同的 Python 可执行文件路径
            if local_env.get("python_executable") and remote_env.get("python_executable"):
                local_python = local_env["python_executable"]
                remote_python = remote_env.get("python_executable")
                
                if local_python != remote_python:
                    self.logger.info(f"Python executable mismatch detected: local={local_python}, remote={remote_python}")
                    
                    # 检查是否可以通过修改环境变量来对齐
                    suggested_python = self._suggest_compatible_python(local_env, remote_env)
                    if suggested_python:
                        self.logger.info(f"Suggested compatible Python: {suggested_python}")
                        return self._try_restart_with_python(suggested_python)
            
            # 方案2: 虚拟环境对齐
            if local_env.get("virtual_env") != remote_env.get("virtual_env"):
                return self._try_virtual_env_alignment(local_env, remote_env)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Environment alignment failed: {e}")
            return False

    def _suggest_compatible_python(self, local_env: Dict[str, Any], remote_env: Dict[str, Any]) -> Optional[str]:
        """建议兼容的 Python 可执行文件"""
        try:
            # 从远程环境信息中提取 Python 版本
            remote_python_version = remote_env.get("python_version", "").split()[0]
            if not remote_python_version:
                return None
            
            # 提取主版本号 (例如 "3.11" from "3.11.5")
            version_parts = remote_python_version.split(".")
            if len(version_parts) >= 2:
                major_minor = f"{version_parts[0]}.{version_parts[1]}"
                
                # 常见的 Python 可执行文件路径
                potential_pythons = [
                    f"python{major_minor}",
                    f"/usr/bin/python{major_minor}",
                    f"/usr/local/bin/python{major_minor}",
                    f"python{version_parts[0]}",
                ]
                
                # 检查哪个可执行文件可用
                for python_cmd in potential_pythons:
                    try:
                        result = subprocess.run([python_cmd, "--version"], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and major_minor in result.stdout:
                            return python_cmd
                    except Exception:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to suggest compatible Python: {e}")
            return None

    def _try_restart_with_python(self, python_executable: str) -> bool:
        """尝试使用指定的 Python 可执行文件重新启动当前任务"""
        try:
            self.logger.info(f"Attempting to restart with Python: {python_executable}")
            
            # 构建重启命令
            current_script = sys.argv[0]
            restart_args = [python_executable, current_script] + sys.argv[1:]
            
            self.logger.info(f"Restart command: {' '.join(restart_args)}")
            
            # 执行重启 (这会终止当前进程)
            os.execv(python_executable, restart_args)
            
        except Exception as e:
            self.logger.error(f"Failed to restart with compatible Python: {e}")
            return False

    def _try_virtual_env_alignment(self, local_env: Dict[str, Any], remote_env: Dict[str, Any]) -> bool:
        """尝试虚拟环境对齐"""
        try:
            remote_venv = remote_env.get("virtual_env") or remote_env.get("conda_env")
            
            if remote_venv:
                self.logger.info(f"Attempting to align with remote virtual environment: {remote_venv}")
                
                # 检查远程虚拟环境是否在本地可用
                if remote_env.get("conda_env"):
                    # Conda 环境
                    return self._try_conda_env_switch(remote_env["conda_env"])
                elif remote_env.get("virtual_env"):
                    # Python venv
                    return self._try_venv_switch(remote_env["virtual_env"])
            
            return False
            
        except Exception as e:
            self.logger.error(f"Virtual environment alignment failed: {e}")
            return False

    def _try_conda_env_switch(self, conda_env_name: str) -> bool:
        """尝试切换到指定的 Conda 环境"""
        try:
            # 检查 conda 是否可用
            result = subprocess.run(["conda", "info", "--envs"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and conda_env_name in result.stdout:
                self.logger.info(f"Found conda environment: {conda_env_name}")
                
                # 获取 conda 环境的 Python 路径
                conda_python = f"conda run -n {conda_env_name} python"
                
                # 重启脚本使用指定的 conda 环境
                current_script = sys.argv[0]
                restart_cmd = ["conda", "run", "-n", conda_env_name, "python", current_script] + sys.argv[1:]
                
                self.logger.info(f"Restarting with conda environment: {' '.join(restart_cmd)}")
                os.execv("/usr/bin/conda", restart_cmd)
                
            return False
            
        except Exception as e:
            self.logger.error(f"Conda environment switch failed: {e}")
            return False

    def _try_venv_switch(self, venv_path: str) -> bool:
        """尝试切换到指定的虚拟环境"""
        try:
            venv_python = os.path.join(venv_path, "bin", "python")
            
            if os.path.exists(venv_python):
                self.logger.info(f"Found virtual environment Python: {venv_python}")
                return self._try_restart_with_python(venv_python)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Virtual environment switch failed: {e}")
            return False

    def _update_log_symlink(self):
        """更新日志软链接（在连接建立后调用）"""
        if not self._log_symlink_created:
            self._setup_log_symlink()
        
    def get_log_symlink_status(self) -> dict:
        """获取日志软链接状态"""
        try:
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            remote_log_symlink = project_root / "logs" / "remote_jobmanager_latest"
            
            if remote_log_symlink.exists():
                target = remote_log_symlink.resolve()
                return {
                    "status": "active",
                    "symlink_path": str(remote_log_symlink),
                    "target_path": str(target),
                    "exists": target.exists()
                }
            else:
                return {
                    "status": "not_created",
                    "symlink_path": str(remote_log_symlink),
                    "target_path": None,
                    "exists": False
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def submit(self):
        # 先进行环境兼容性检查
        self.logger.info("Performing environment compatibility check...")
        
        try:
            compatibility_result = self._validate_environment_compatibility()
            
            if not compatibility_result["compatible"]:
                self.logger.error("Environment compatibility check failed:")
                for error in compatibility_result["errors"]:
                    self.logger.error(f"  - {error}")
                
                # 尝试环境对齐
                if self._attempt_environment_alignment(compatibility_result):
                    self.logger.info("Environment alignment successful, retrying submission...")
                    # 如果对齐成功，这里的代码不会执行，因为进程会重启
                else:
                    self.logger.warning("Environment alignment failed, proceeding with submission anyway...")
            
            elif compatibility_result["warnings"]:
                self.logger.warning("Environment compatibility warnings detected:")
                for warning in compatibility_result["warnings"]:
                    self.logger.warning(f"  - {warning}")
                
                # 对于警告，尝试对齐但不强制
                self.logger.info("Attempting environment alignment for better compatibility...")
                self._attempt_environment_alignment(compatibility_result)
            
            else:
                self.logger.info("Environment compatibility check passed")
                
        except Exception as e:
            self.logger.warning(f"Environment compatibility check failed: {e}, proceeding anyway...")
        
        # 序列化环境
        from utils.serialization.dill_serializer import trim_object_for_ray
        
        try:
            serialized_env = trim_object_for_ray(self)
        except Exception as e:
            self.logger.error(f"Environment serialization failed: {e}")
            
            # 如果序列化失败，尝试环境对齐后重试
            self.logger.info("Attempting environment alignment due to serialization failure...")
            
            try:
                compatibility_result = self._validate_environment_compatibility()
                if self._attempt_environment_alignment(compatibility_result):
                    # 如果对齐成功，进程会重启，这里不会执行
                    pass
                else:
                    # 对齐失败，抛出原始错误
                    raise e
            except Exception as alignment_error:
                self.logger.error(f"Environment alignment also failed: {alignment_error}")
                raise e
        
        # 通过jobmanager属性提交job
        env_uuid = self.jobmanager.submit_job(serialized_env)
        
        if env_uuid:
            self.env_uuid = env_uuid
            self.logger.info(f"Environment submitted with UUID: {self.env_uuid}")
            
            # 提交成功后更新日志软链接
            self._update_log_symlink()
        else:
            raise RuntimeError("Failed to submit environment: no UUID returned")

    def stop(self):
        """停止远程环境"""
        if not self.env_uuid:
            self.logger.warning("Remote environment not submitted, nothing to stop")
            return
        
        self.logger.info("Stopping remote pipeline...")
        
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "stopped":
                self.is_running = False
                self.logger.info("Remote pipeline stopped successfully")
            else:
                self.logger.warning(f"Failed to stop remote pipeline: {response.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error stopping remote pipeline: {e}")

    def close(self):
        """关闭远程环境"""
        if not self.env_uuid:
            self.logger.warning("Remote environment not submitted, nothing to close")
            return
        
        self.logger.info("Closing remote environment...")
        
        try:
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "stopped":
                self.logger.info("Remote environment closed successfully")
            else:
                self.logger.warning(f"Failed to close remote environment: {response.get('message')}")
                
        except Exception as e:
            self.logger.error(f"Error closing remote environment: {e}")
        finally:
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            
            # 清理管道
            self.pipeline.clear()
            
            # 清理日志软链接（可选，也可以保留用于查看历史日志）
            self._cleanup_log_symlink_if_needed()

    def _cleanup_log_symlink_if_needed(self):
        """根据需要清理日志软链接"""
        # 这里可以根据具体需求决定是否清理软链接
        # 通常建议保留软链接，便于查看历史日志
        pass

    def health_check(self):
        """检查远程JobManager健康状态"""
        try:
            response = self.client.health_check()
            return response
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_remote_info(self):
        """获取远程JobManager信息"""
        try:
            response = self.client.get_actor_info()
            
            # 添加日志软链接信息
            symlink_status = self.get_log_symlink_status()
            response["log_symlink"] = symlink_status
            
            return response
        except Exception as e:
            self.logger.error(f"Failed to get remote info: {e}")
            return {"status": "error", "message": str(e)}

    def check_environment_compatibility(self, detailed: bool = False) -> Dict[str, Any]:
        """
        检查本地和远程环境的兼容性
        
        Args:
            detailed: 是否返回详细的环境信息
        
        Returns:
            兼容性检查结果
        """
        try:
            compatibility_result = self._validate_environment_compatibility()
            
            if not detailed:
                # 简化版本，只返回兼容性状态和警告/错误
                return {
                    "compatible": compatibility_result["compatible"],
                    "warnings": compatibility_result["warnings"],
                    "errors": compatibility_result["errors"]
                }
            
            return compatibility_result
            
        except Exception as e:
            self.logger.error(f"Environment compatibility check failed: {e}")
            return {
                "compatible": False,
                "errors": [str(e)],
                "warnings": []
            }

    def align_environment(self, force: bool = False) -> Dict[str, Any]:
        """
        尝试对齐本地和远程环境
        
        Args:
            force: 是否强制尝试对齐（即使兼容性检查通过）
        
        Returns:
            对齐结果
        """
        try:
            compatibility_result = self._validate_environment_compatibility()
            
            if compatibility_result["compatible"] and not compatibility_result["warnings"] and not force:
                return {
                    "status": "success",
                    "message": "Environment already compatible, no alignment needed",
                    "alignment_performed": False
                }
            
            self.logger.info("Starting environment alignment...")
            alignment_success = self._attempt_environment_alignment(compatibility_result)
            
            if alignment_success:
                return {
                    "status": "success", 
                    "message": "Environment alignment initiated (process will restart)",
                    "alignment_performed": True
                }
            else:
                return {
                    "status": "failed",
                    "message": "Environment alignment failed",
                    "alignment_performed": False,
                    "compatibility_issues": {
                        "warnings": compatibility_result["warnings"],
                        "errors": compatibility_result["errors"]
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Environment alignment failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "alignment_performed": False
            }