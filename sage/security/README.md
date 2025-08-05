# SAGE 安全模块

SAGE安全模块提供框架运行时的安全保障，包括容器化执行、文件访问控制等安全机制。

## 模块概述

安全模块确保SAGE框架在处理用户代码和数据时的安全性，通过多层安全机制防止恶意代码执行、未授权访问等安全威胁。

## 核心组件

### `containerized_execution.py`
容器化执行服务：
- 在隔离的容器环境中执行用户代码
- 提供资源限制和访问控制
- 支持Docker和其他容器化技术
- 包含执行超时和资源监控
- 防止恶意代码对主机系统的影响

### `file_access_service.py`
文件访问控制服务：
- 实现细粒度的文件访问权限控制
- 支持基于路径的访问策略
- 提供安全的文件操作API
- 包含文件类型检查和内容扫描
- 防止路径遍历攻击和未授权访问

## 主要特性

- **隔离执行**: 通过容器化技术隔离用户代码执行
- **权限控制**: 细粒度的文件和资源访问控制
- **安全审计**: 完整的安全操作日志记录
- **威胁防护**: 多种安全威胁的检测和防护
- **资源限制**: 防止资源耗尽攻击

## 安全策略

### 执行安全
- 代码在沙箱环境中运行
- 严格的资源使用限制
- 网络访问控制
- 执行时间限制

### 数据安全
- 敏感数据加密存储
- 访问权限验证
- 数据传输加密
- 审计日志记录

### 系统安全
- 最小权限原则
- 安全配置验证
- 定期安全扫描
- 漏洞监控和修复

## 使用场景

- **用户代码执行**: 安全执行用户提交的处理函数
- **数据处理**: 保护敏感数据的处理过程
- **多租户环境**: 不同用户间的资源隔离
- **生产部署**: 生产环境的安全加固

## 快速开始

```python
# 容器化执行
from sage.security.containerized_execution import ContainerizedExecutor

executor = ContainerizedExecutor(
    image="sage-runtime:latest",
    resource_limits={"memory": "1GB", "cpu": "1"}
)

result = executor.execute_function(user_function, input_data)

# 文件访问控制
from sage.security.file_access_service import FileAccessService

file_service = FileAccessService(
    allowed_paths=["/data", "/tmp"],
    blocked_extensions=[".exe", ".bat", ".sh"]
)

# 安全读取文件
content = file_service.read_file("/data/input.txt")

# 安全写入文件
file_service.write_file("/tmp/output.txt", processed_data)
```

## 配置选项

### 容器化配置
- `container_runtime`: 容器运行时（docker, podman等）
- `base_image`: 基础执行镜像
- `resource_limits`: 资源限制配置
- `network_policy`: 网络访问策略
- `timeout_settings`: 执行超时配置

### 文件访问配置
- `allowed_paths`: 允许访问的路径列表
- `blocked_paths`: 禁止访问的路径列表
- `file_size_limits`: 文件大小限制
- `allowed_extensions`: 允许的文件扩展名
- `scan_enabled`: 是否启用内容扫描

## 安全最佳实践

1. **最小权限**: 仅授予必要的最小权限
2. **定期更新**: 及时更新安全补丁和配置
3. **监控审计**: 启用完整的安全日志记录
4. **定期扫描**: 定期进行安全漏洞扫描
5. **隔离环境**: 使用容器和虚拟环境隔离

## 合规性支持

- 支持数据保护法规合规（GDPR等）
- 提供安全审计报告
- 支持行业安全标准（SOC2等）
- 包含隐私保护机制

## 性能考虑

安全机制在保证安全的同时，注重性能优化：
- 容器启动优化
- 权限检查缓存
- 批量操作支持
- 异步安全检查
