# 多租户环境不一致问题的解决方案

## 问题描述

目前的 JobManager 实例是全局唯一的，当多租户环境不一致时（如不同的Python版本、依赖版本、虚拟环境等），会导致 environment 无法提交，主要表现为：

1. **序列化/反序列化失败**: 不同Python版本或dill版本间的对象序列化不兼容
2. **依赖版本冲突**: 本地和远程环境的关键依赖版本不一致
3. **路径和环境变量差异**: 不同虚拟环境间的路径配置差异

## 解决方案

### 1. 环境检查机制

在 `RemoteEnvironment` 中添加了环境检查功能：

- **本地环境信息收集**: 获取Python版本、依赖版本、虚拟环境等信息
- **远程环境信息查询**: 通过JobManager获取远程环境的相同信息
- **兼容性验证**: 对比本地和远程环境，识别不兼容的配置

### 2. 环境对齐机制

当检测到环境不一致时，提供多种对齐策略：

- **Python版本对齐**: 自动查找兼容的Python可执行文件并重启
- **虚拟环境对齐**: 切换到远程环境匹配的conda环境或venv
- **依赖版本提示**: 提供详细的版本差异信息和建议

### 3. 智能提交流程

增强了 `submit()` 方法：

1. **预检查**: 在序列化前进行环境兼容性检查
2. **自动对齐**: 发现问题时尝试自动环境对齐
3. **失败恢复**: 序列化失败时的二次尝试和错误诊断

## 新增的API

### RemoteEnvironment 新方法

```python
# 检查环境兼容性
compatibility = env.check_environment_compatibility(detailed=True)

# 尝试环境对齐
result = env.align_environment(force=False)

# 获取详细的远程信息（包含环境信息）
info = env.get_remote_info()
```

### JobManagerClient 新方法

```python
# 获取远程环境信息
client = JobManagerClient()
env_info = client.get_environment_info()
```

### RemoteJobManager 新方法

```python
# 在远程Actor中获取环境信息
@ray.remote
class RemoteJobManager:
    def get_environment_info(self) -> Dict[str, Any]:
        # 返回Python版本、依赖版本、环境配置等信息
```

## 使用示例

### 基本用法

```python
from sage_core.api.remote_environment import RemoteEnvironment

# 创建远程环境
env = RemoteEnvironment("my_env")

# 执行提交（自动包含环境检查）
try:
    env.submit()
    print("提交成功！")
except Exception as e:
    print(f"提交失败: {e}")
```

### 显式环境检查

```python
# 手动检查环境兼容性
compatibility = env.check_environment_compatibility(detailed=True)

if not compatibility["compatible"]:
    print("环境不兼容，错误:")
    for error in compatibility["errors"]:
        print(f"  - {error}")
    
    # 尝试自动对齐
    result = env.align_environment()
    if result["alignment_performed"]:
        print("环境对齐已启动，进程将重启")
```

### 环境信息查看

```python
# 查看详细的环境对比
compatibility = env.check_environment_compatibility(detailed=True)
local_env = compatibility["local_env"] 
remote_env = compatibility["remote_env"]

print(f"本地Python: {local_env['python_version']}")
print(f"远程Python: {remote_env['python_version']}")
print(f"本地Ray: {local_env['ray_version']}")
print(f"远程Ray: {remote_env['ray_version']}")
```

## 对齐策略

### 1. Python版本对齐

- 自动检测远程Python版本
- 在本地查找匹配的Python可执行文件
- 使用匹配的Python重新启动当前脚本

### 2. 虚拟环境对齐

- **Conda环境**: 检测并切换到匹配的conda环境
- **Python venv**: 切换到匹配的虚拟环境
- **环境创建**: 未来可扩展为自动创建匹配的环境

### 3. 依赖对齐

- 版本差异检测和报告
- 关键依赖（ray, dill等）的特别检查
- 提供升级/降级建议

## 配置选项

### 环境检查配置

```python
env = RemoteEnvironment(
    name="my_env",
    config={
        "environment_check": {
            "enabled": True,  # 是否启用环境检查
            "strict_mode": False,  # 严格模式：不兼容时拒绝提交
            "auto_align": True,  # 自动尝试环境对齐
            "critical_packages": ["ray", "dill", "torch"]  # 关键依赖列表
        }
    }
)
```

## 错误处理和日志

系统提供详细的日志记录：

- 环境检查过程和结果
- 对齐尝试的详细步骤
- 失败原因的具体分析
- 建议的手动修复方案

## 部署和运维建议

### 1. 监控和告警

- 定期检查不同租户间的环境一致性
- 设置环境不兼容的告警机制

### 2. 标准化环境

- 建议为不同租户提供标准化的环境配置
- 使用容器化部署减少环境差异

### 3. 版本管理

- 定期同步更新所有环境的依赖版本
- 维护环境兼容性矩阵

## 未来扩展

1. **环境隔离**: 为不同租户创建隔离的JobManager实例
2. **动态环境管理**: 根据需要动态创建匹配的执行环境
3. **智能依赖管理**: 自动安装缺失或升级不兼容的依赖
4. **环境模板**: 预定义的环境配置模板供用户选择

## 测试

运行示例脚本测试新功能：

```bash
python example_environment_check.py
```

这将演示完整的环境检查、对齐和提交流程。
