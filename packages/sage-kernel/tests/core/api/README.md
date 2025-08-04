# API Test 模块

该目录包含 Sage Core API 层的测试文件，主要测试远程环境相关功能。

## 测试文件说明

### `test_new_remote_env.py`
测试新版本的远程环境实现：
- 远程环境的创建和初始化
- 远程任务的提交和执行
- 错误处理和恢复机制

### `test_remote_env_serialization.py`  
测试远程环境的序列化功能：
- 环境配置的序列化和反序列化
- 跨进程/跨节点的环境状态传输
- 序列化数据的完整性验证

### `test_remote_environment_server.py`
测试远程环境服务器功能：
- 远程环境服务器的启动和停止
- 客户端与服务器的通信协议
- 多客户端并发访问测试

## 运行测试

```bash
# 运行所有API测试
python -m pytest tests/core/api/

# 运行特定测试文件
python -m pytest tests/core/api/test_new_remote_env.py
```

## 测试环境要求

- Python 3.8+
- pytest
- 网络连接（用于远程环境测试）
- Ray 集群（可选，用于分布式测试）
