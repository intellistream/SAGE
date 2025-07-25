#!/usr/bin/env python3
"""
简化RemoteEnvironment测试脚本
演示序列化环境并发送给服务端的基本功能
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 导入SAGE的序列化工具和RemoteEnvironment
try:
    from sage.utils.serialization.dill_serializer import serialize_object, deserialize_object
    from simple_remote_environment import SimpleRemoteEnvironment
    print("✅ Successfully imported SAGE components")
    has_sage_imports = True
except ImportError as e:
    print(f"❌ Could not import SAGE components: {e}")
    has_sage_imports = False
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockBaseEnvironment:
    """模拟BaseEnvironment基类"""
    
    def __init__(self, name: str, config: dict = None, platform: str = "local"):
        self.name = name
        self.config = config or {}
        self.platform = platform
        self.pipeline = []
        self.is_running = False
        self.env_uuid = None
        
        logger.info(f"MockBaseEnvironment '{name}' initialized with platform '{platform}'")

class MockJobManagerClient:
    """模拟JobManager客户端"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        logger.info(f"MockJobManagerClient connecting to {host}:{port}")
    
    def health_check(self):
        return {"status": "success", "message": "Mock client is healthy"}
    
    def get_actor_info(self):
        return {
            "status": "success", 
            "actor_name": "mock_jobmanager",
            "host": self.host,
            "port": self.port
        }
    
    def get_actor_handle(self):
        return MockJobManager(self.host, self.port)

class MockJobManager:
    """模拟JobManager"""
    
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.submitted_jobs = {}
        
    def submit_job(self, serialized_env):
        """模拟提交作业"""
        import uuid
        import pickle
        
        job_uuid = str(uuid.uuid4())
        
        logger.info(f"MockJobManager received job submission")
        logger.info(f"Serialized data size: {len(pickle.dumps(serialized_env)) if serialized_env else 0} bytes")
        
        # 验证序列化环境的基本结构
        if hasattr(serialized_env, 'name'):
            logger.info(f"Environment name: {serialized_env.name}")
        if hasattr(serialized_env, 'config'):
            logger.info(f"Environment config keys: {list(serialized_env.config.keys()) if serialized_env.config else []}")
        if hasattr(serialized_env, 'platform'):
            logger.info(f"Environment platform: {serialized_env.platform}")
        
        # 检查是否排除了客户端连接
        excluded_attrs = ['_engine_client', '_jobmanager', 'client', 'jobmanager']
        found_excluded = []
        for attr in excluded_attrs:
            if hasattr(serialized_env, attr):
                value = getattr(serialized_env, attr)
                if value is not None:
                    found_excluded.append(attr)
        
        if found_excluded:
            logger.warning(f"Found non-None excluded attributes: {found_excluded}")
        else:
            logger.info("✅ All client connection attributes properly excluded")
        
        self.submitted_jobs[job_uuid] = {
            "uuid": job_uuid,
            "environment": serialized_env,
            "status": "running",
            "timestamp": __import__('time').time()
        }
        
        logger.info(f"✅ Job submitted successfully with UUID: {job_uuid}")
        return job_uuid
    
    def pause_job(self, job_uuid: str):
        """模拟暂停作业"""
        if job_uuid in self.submitted_jobs:
            self.submitted_jobs[job_uuid]["status"] = "stopped"
            logger.info(f"Job {job_uuid} paused")
            return {"status": "stopped", "uuid": job_uuid}
        else:
            logger.error(f"Job {job_uuid} not found")
            return {"status": "error", "message": "Job not found"}
    
    def get_job_status(self, job_uuid: str):
        """模拟获取作业状态"""
        if job_uuid in self.submitted_jobs:
            return self.submitted_jobs[job_uuid]
        else:
            return {"status": "error", "message": "Job not found"}

def mock_trim_object_for_ray(obj):
    """模拟trim_object_for_ray函数"""
    logger.info("Mocking trim_object_for_ray - creating cleaned copy")
    
    if not hasattr(obj, '__dict__'):
        return obj
    
    # 创建对象副本
    obj_class = type(obj)
    cleaned_obj = obj_class.__new__(obj_class)
    
    # 复制属性，排除指定的属性
    exclude_attrs = getattr(obj_class, '__state_exclude__', [])
    
    for attr_name, attr_value in obj.__dict__.items():
        if attr_name not in exclude_attrs:
            setattr(cleaned_obj, attr_name, attr_value)
        else:
            # 设置为None而不是完全移除
            setattr(cleaned_obj, attr_name, None)
            logger.debug(f"Excluded attribute '{attr_name}' set to None")
    
    # 特殊处理：对于@property属性，我们不能简单设置，需要确保底层私有属性被清理
    property_mappings = {
        'client': '_engine_client',
        'jobmanager': '_jobmanager'
    }
    
    for prop_name, private_attr in property_mappings.items():
        if hasattr(cleaned_obj, private_attr):
            setattr(cleaned_obj, private_attr, None)
            logger.debug(f"Cleared private attribute '{private_attr}' for property '{prop_name}'")
    
    logger.info(f"Cleaned object created, excluded {len(exclude_attrs)} attributes")
    return cleaned_obj

# 简化版RemoteEnvironment类
class SimpleRemoteEnvironment(MockBaseEnvironment):
    """
    简化的远程环境实现
    专注于序列化环境并发送给远程JobManager
    """
    
    # 序列化时排除的属性
    __state_exclude__ = [
        'logger', '_logger', 
        '_engine_client', '_jobmanager',
        'client', 'jobmanager'  # 避免序列化客户端连接
    ]

    def __init__(self, name: str, config: dict = None, host: str = "127.0.0.1", port: int = 19001):
        """初始化远程环境"""
        super().__init__(name, config, platform="remote")
        
        # 远程连接配置
        self.daemon_host = host
        self.daemon_port = port
        
        # 客户端连接（延迟初始化）
        self._engine_client = None
        self._jobmanager = None
        
        # 更新配置
        self.config.update({
            "engine_host": self.daemon_host,
            "engine_port": self.daemon_port
        })
        
        logger.info(f"SimpleRemoteEnvironment '{name}' initialized for {host}:{port}")

    @property
    def client(self):
        """获取JobManager客户端（延迟创建）"""
        if self._engine_client is None:
            logger.debug(f"Creating JobManager client for {self.daemon_host}:{self.daemon_port}")
            self._engine_client = MockJobManagerClient(
                host=self.daemon_host, 
                port=self.daemon_port
            )
        return self._engine_client

    @property
    def jobmanager(self):
        """获取远程JobManager句柄（延迟创建）"""
        if self._jobmanager is None:
            logger.debug("Getting JobManager actor handle")
            self._jobmanager = self.client.get_actor_handle()
        return self._jobmanager

    def submit(self) -> str:
        """提交环境到远程JobManager"""
        try:
            logger.info(f"Submitting environment '{self.name}' to remote JobManager")
            
            # 序列化环境，排除不可序列化的内容
            logger.debug("Serializing environment for remote submission")
            serialized_env = mock_trim_object_for_ray(self)
            
            # 通过JobManager提交作业
            logger.debug("Calling jobmanager.submit_job()")
            env_uuid = self.jobmanager.submit_job(serialized_env)
            
            if env_uuid:
                self.env_uuid = env_uuid
                logger.info(f"Environment submitted successfully with UUID: {self.env_uuid}")
                return env_uuid
            else:
                raise RuntimeError("Failed to submit environment: no UUID returned")
                
        except Exception as e:
            logger.error(f"Failed to submit environment: {e}")
            raise

    def stop(self):
        """停止远程环境"""
        if not self.env_uuid:
            logger.warning("Remote environment not submitted, nothing to stop")
            return {"status": "warning", "message": "Environment not submitted"}
        
        try:
            logger.info(f"Stopping remote environment {self.env_uuid}")
            response = self.jobmanager.pause_job(self.env_uuid)
            
            if response.get("status") == "stopped":
                logger.info(f"Environment {self.env_uuid} stopped successfully")
            else:
                logger.warning(f"Stop operation returned: {response}")
                
            return response
            
        except Exception as e:
            logger.error(f"Error stopping remote environment: {e}")
            return {"status": "error", "message": str(e)}

    def close(self):
        """关闭远程环境"""
        if not self.env_uuid:
            logger.warning("Remote environment not submitted, nothing to close")
            return {"status": "warning", "message": "Environment not submitted"}
        
        try:
            logger.info(f"Closing remote environment {self.env_uuid}")
            response = self.jobmanager.pause_job(self.env_uuid)
            
            # 清理本地资源
            self.is_running = False
            self.env_uuid = None
            self.pipeline.clear()
            
            logger.info("Remote environment closed and local resources cleaned")
            return response
            
        except Exception as e:
            logger.error(f"Error closing remote environment: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # 确保本地状态被清理
            self.is_running = False
            self.env_uuid = None

    def health_check(self):
        """检查远程JobManager健康状态"""
        try:
            logger.debug("Performing health check")
            response = self.client.health_check()
            logger.debug(f"Health check result: {response}")
            return response
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_remote_info(self):
        """获取远程JobManager信息"""
        try:
            logger.debug("Getting remote JobManager info")
            response = self.client.get_actor_info()
            return response
        except Exception as e:
            logger.error(f"Failed to get remote info: {e}")
            return {"status": "error", "message": str(e)}

    def get_job_status(self):
        """获取当前环境作业状态"""
        if not self.env_uuid:
            return {"status": "not_submitted", "message": "Environment not submitted"}
        
        try:
            logger.debug(f"Getting job status for {self.env_uuid}")
            response = self.jobmanager.get_job_status(self.env_uuid)
            return response
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"status": "error", "message": str(e)}

    def __repr__(self) -> str:
        return f"SimpleRemoteEnvironment(name='{self.name}', host='{self.daemon_host}', port={self.daemon_port})"


def test_remote_environment():
    """测试简化的RemoteEnvironment"""
    logger.info("=== Testing Simplified RemoteEnvironment ===")
    
    # 创建远程环境
    config = {
        "batch_size": 100,
        "timeout": 30,
        "retry_count": 3
    }
    
    env = SimpleRemoteEnvironment(
        name="test_remote_env",
        config=config,
        host="127.0.0.1",
        port=19001
    )
    
    # 添加一些管道步骤（模拟实际使用）
    env.pipeline.extend(["data_source", "transformation", "sink"])
    
    logger.info(f"Created environment: {env}")
    
    # 测试健康检查
    logger.info("\n--- Testing Health Check ---")
    health = env.health_check()
    logger.info(f"Health check result: {health}")
    
    # 测试获取远程信息
    logger.info("\n--- Testing Remote Info ---")
    remote_info = env.get_remote_info()
    logger.info(f"Remote info: {remote_info}")
    
    # 测试提交环境
    logger.info("\n--- Testing Environment Submission ---")
    try:
        env_uuid = env.submit()
        logger.info(f"✅ Environment submitted with UUID: {env_uuid}")
        
        # 测试获取作业状态
        logger.info("\n--- Testing Job Status ---")
        status = env.get_job_status()
        logger.info(f"Job status: {status}")
        
        # 测试停止环境
        logger.info("\n--- Testing Environment Stop ---")
        stop_result = env.stop()
        logger.info(f"Stop result: {stop_result}")
        
        # 测试关闭环境
        logger.info("\n--- Testing Environment Close ---")
        close_result = env.close()
        logger.info(f"Close result: {close_result}")
        
    except Exception as e:
        logger.error(f"❌ Environment submission failed: {e}")
    
    logger.info("\n=== Test Completed ===")


def test_serialization_exclusion():
    """测试序列化排除功能"""
    logger.info("\n=== Testing Serialization Exclusion ===")
    
    env = SimpleRemoteEnvironment("serialization_test")
    
    # 触发客户端创建
    _ = env.client
    _ = env.jobmanager
    
    logger.info("Before serialization:")
    logger.info(f"  _engine_client: {env._engine_client}")
    logger.info(f"  _jobmanager: {env._jobmanager}")
    
    # 测试序列化清理
    cleaned_env = mock_trim_object_for_ray(env)
    
    logger.info("After serialization cleaning:")
    logger.info(f"  _engine_client: {cleaned_env._engine_client}")
    logger.info(f"  _jobmanager: {cleaned_env._jobmanager}")
    logger.info(f"  name: {cleaned_env.name}")
    logger.info(f"  config: {cleaned_env.config}")
    
    # 验证清理效果 - 只检查底层私有属性
    critical_attrs = ['_engine_client', '_jobmanager']
    all_clean = True
    
    for attr in critical_attrs:
        if hasattr(cleaned_env, attr):
            value = getattr(cleaned_env, attr)
            if value is not None:
                logger.warning(f"❌ Attribute '{attr}' should be None but is: {value}")
                all_clean = False
            else:
                logger.info(f"✅ Attribute '{attr}' properly excluded (None)")
    
    # 测试@property是否正常工作（会创建新的客户端实例）
    logger.info("Testing @property behavior after cleaning:")
    try:
        client_after_clean = cleaned_env.client
        logger.info(f"✅ client property works: {type(client_after_clean).__name__}")
        jobmanager_after_clean = cleaned_env.jobmanager  
        logger.info(f"✅ jobmanager property works: {type(jobmanager_after_clean).__name__}")
    except Exception as e:
        logger.error(f"❌ Property access failed: {e}")
        all_clean = False
    
    if all_clean:
        logger.info("✅ All critical attributes properly excluded and properties work correctly")
    else:
        logger.error("❌ Some attributes were not properly excluded")
    
    logger.info("=== Serialization Exclusion Test Completed ===")


def main():
    """主函数"""
    logger.info("Starting SimpleRemoteEnvironment Tests")
    
    # 测试序列化排除
    test_serialization_exclusion()
    
    # 测试远程环境基本功能
    test_remote_environment()
    
    logger.info("All tests completed")


if __name__ == "__main__":
    main()
