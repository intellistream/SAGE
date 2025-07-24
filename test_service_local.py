import sys
import os
sys.path.append('/home/tjy/SAGE')

from sage_core.api.local_environment import LocalEnvironment
from sage_runtime.dispatcher import Dispatcher
from sage_runtime.runtime_context import RuntimeContext

# 创建一个简单的测试服务
class TestService:
    def __init__(self, name: str, value: int = 42):
        self.name = name
        self.value = value
        self.ctx = None
    
    def start_running(self):
        print(f"TestService {self.name} started with value {self.value}")
    
    def get_info(self):
        return f"Service {self.name}: value={self.value}"
    
    def terminate(self):
        print(f"TestService {self.name} terminated")

# 创建local环境并注册服务
env = LocalEnvironment(
    name="test_env",
    num_cpus=1,
    memory=1024
)

# 注册服务
env.register_service(
    service_name="test_service",
    service_class=TestService,
    service_args=("my_service",),
    service_kwargs={"value": 100}
)

print("Service factories:", list(env.service_factories.keys()))
print("Service task factories:", list(env.service_task_factories.keys()))

# 创建dispatcher并提交环境
dispatcher = Dispatcher()
ctx = RuntimeContext()

try:
    dispatcher.submit(env, ctx)
    print("Environment submitted successfully")
    
    # 启动服务
    dispatcher.start()
    print("Services started")
    
    # 检查服务状态
    service_status = dispatcher.get_service_status()
    print("Service status:", service_status)
    
    # 获取服务实例进行测试
    if "test_service" in dispatcher.services:
        service_task = dispatcher.services["test_service"]
        # 如果是本地服务任务，可以直接访问服务实例
        if hasattr(service_task, 'service'):
            service = service_task.service
            print("Service info:", service.get_info())
    
finally:
    # 清理
    dispatcher.cleanup()
    print("Cleanup completed")
