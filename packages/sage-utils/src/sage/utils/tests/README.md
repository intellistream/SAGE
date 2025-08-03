# SAGE 工具模块测试

本目录包含SAGE工具模块的单元测试和集成测试。

## 测试概述

测试覆盖了工具模块的主要功能，确保代码质量和功能正确性。

## 测试文件

### `test_embedding.py`
嵌入模型测试：
- 各种嵌入服务的功能测试
- API接口兼容性测试
- 性能基准测试
- 错误处理测试

### `test_name_server.py`
名称服务器测试：
- 服务注册和发现测试
- 名称解析功能测试
- 并发访问测试
- 故障恢复测试

### `test_refactored_servers.py`
重构服务器测试：
- 服务器启动和关闭测试
- 请求处理测试
- 负载测试
- 配置管理测试

## 运行测试

```bash
# 运行所有测试
python -m pytest sage/utils/tests/

# 运行特定测试文件
python -m pytest sage/utils/tests/test_embedding.py

# 运行特定测试用例
python -m pytest sage/utils/tests/test_embedding.py::TestEmbeddingAPI::test_openai_embedding
```

## 测试配置

测试使用以下配置：
- 模拟环境和服务
- 测试数据文件
- 临时文件清理
- 并发测试控制

## 测试覆盖率

目标测试覆盖率：
- 单元测试覆盖率 > 80%
- 集成测试覆盖关键路径
- 异常处理测试完整

## 持续集成

测试集成到CI/CD流程：
- 自动化测试执行
- 测试报告生成
- 性能回归检测
- 代码质量检查
