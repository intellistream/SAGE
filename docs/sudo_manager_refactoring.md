# Sudo管理器重构示例

## 重构前后对比

### 重构前 (JobManagerController类中的方法)
```python
class JobManagerController:
    def __init__(self):
        self._sudo_password = None
    
    def _get_sudo_password(self) -> str:
        """获取sudo密码"""
        if self._sudo_password is None:
            # 30多行的密码获取和验证逻辑
            # 直接在类中处理UI交互
            # 密码验证逻辑耦合在业务类中
        return self._sudo_password
    
    def _ensure_sudo_access(self) -> bool:
        """确保有sudo访问权限"""
        # 5行逻辑耦合在业务类中
        password = self._get_sudo_password()
        # ...
    
    # 在多个方法中重复使用：
    def force_kill(self):
        if not self._ensure_sudo_access():
            # 处理逻辑
```

### 重构后 (使用独立的工具类)
```python
from sage.utils.system import create_sudo_manager

class JobManagerController:
    def __init__(self):
        self.sudo_manager = create_sudo_manager()
    
    # 简化的方法调用：
    def force_kill(self):
        if not self.sudo_manager.ensure_sudo_access():
            # 处理逻辑
```

## 新的Sudo管理器功能

### 1. 基本使用
```python
from sage.utils.system import create_sudo_manager

# 创建sudo管理器
sudo_mgr = create_sudo_manager()

# 获取sudo权限
if sudo_mgr.ensure_sudo_access():
    # 执行需要sudo权限的操作
    password = sudo_mgr.get_cached_password()
    result = kill_process_with_sudo(pid, password)
```

### 2. 进程所有权检查
```python
from sage.utils.system import check_process_ownership

# 检查进程是否需要sudo权限
ownership = check_process_ownership(1234)
if ownership["needs_sudo"]:
    print(f"Process {ownership['pid']} is owned by {ownership['process_user']}")
    print("Need sudo to manage this process")
```

### 3. 安全的sudo命令执行
```python
sudo_mgr = create_sudo_manager()
if sudo_mgr.ensure_sudo_access():
    # 执行sudo命令
    result = sudo_mgr.execute_with_sudo(['kill', '-9', '1234'])
    if result["success"]:
        print("Command executed successfully")
    else:
        print(f"Command failed: {result['error']}")
```

## 重构收益

### 1. **代码复用性**
- sudo功能可以在整个SAGE框架中复用
- 统一的sudo管理接口和错误处理
- 避免了在多个类中重复实现相同功能

### 2. **安全性提升**
- 密码只在内存中缓存，并提供清除功能
- 统一的密码验证逻辑
- 安全的sudo命令执行封装

### 3. **可测试性**
- 独立的工具类更容易编写单元测试
- Mock sudo操作进行测试
- 独立验证密码验证逻辑

### 4. **可维护性**
- 系统级逻辑集中管理
- 清晰的职责分离
- 统一的错误处理和用户体验

### 5. **扩展性**
- 可以轻松添加新的sudo功能
- 支持不同类型的sudo操作
- 为未来的权限管理功能奠定基础

## 使用场景

### 1. JobManager进程管理
```python
# 重构后的JobManager
controller = JobManagerController()

# 自动处理sudo权限
if controller.sudo_manager.ensure_sudo_access():
    success = controller.force_kill()
```

### 2. 系统服务管理
```python
sudo_mgr = create_sudo_manager()

# 重启系统服务
if sudo_mgr.ensure_sudo_access():
    result = sudo_mgr.execute_with_sudo(['systemctl', 'restart', 'nginx'])
```

### 3. 文件权限管理
```python
sudo_mgr = create_sudo_manager()

# 修改文件权限
if sudo_mgr.ensure_sudo_access():
    result = sudo_mgr.execute_with_sudo(['chmod', '755', '/path/to/file'])
```

## 最佳实践

### 1. **权限检查优化**
```python
# 批量检查多个进程的权限需求
processes = find_processes_by_name(["nginx", "apache"])
needs_sudo = False

for proc in processes:
    ownership = check_process_ownership(proc.pid)
    if ownership.get("needs_sudo", False):
        needs_sudo = True
        break

# 只在需要时获取sudo权限
if needs_sudo:
    sudo_mgr.ensure_sudo_access()
```

### 2. **错误处理**
```python
try:
    if sudo_mgr.ensure_sudo_access():
        result = sudo_mgr.execute_with_sudo(['kill', str(pid)])
        if not result["success"]:
            print(f"Failed to kill process: {result['error']}")
    else:
        print("Unable to obtain sudo privileges")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### 3. **资源清理**
```python
# 在敏感操作完成后清理缓存
try:
    sudo_mgr.ensure_sudo_access()
    # 执行sudo操作
    result = terminate_processes_by_name(["sensitive_process"])
finally:
    # 清理密码缓存
    sudo_mgr.clear_cache()
```

这次重构成功将sudo管理逻辑从JobManagerController类中解耦出来，提供了一个通用、安全、可重用的sudo管理解决方案。
