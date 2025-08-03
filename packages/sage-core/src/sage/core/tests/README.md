# Tests 模块

该目录包含 Sage Core 模块的集成测试和服务测试。

## 测试文件说明

### `test_comap_service_integration.py`
协同映射服务集成测试：
- 测试协同映射功能与服务系统的集成
- 验证多流协同处理的服务调用机制
- 测试服务间的状态同步和协调

### `test_comap_service_simple.py`  
协同映射服务简单测试：
- 基础协同映射服务功能测试
- 简化场景下的服务行为验证
- 快速回归测试用例

### `README_comap_service_integration.md`
协同映射服务集成的详细文档：
- 集成测试的设计说明
- 测试环境配置要求
- 问题排查指南

## 测试范围

### 集成测试
- Core 模块与其他模块的交互测试
- 端到端数据流处理测试
- 服务集成和协调测试

### 服务测试
- 服务发现和注册测试
- 服务调用和响应测试  
- 服务故障恢复测试

## 运行测试

```bash
# 运行所有 Core 测试
python -m pytest sage/core/tests/

# 运行服务集成测试
python -m pytest sage/core/tests/test_comap_service_integration.py

# 运行简单服务测试
python -m pytest sage/core/tests/test_comap_service_simple.py
```

## 测试环境要求

- Python 3.8+
- pytest 测试框架
- 相关服务运行环境
- 网络连接（用于分布式测试）

## 测试数据和配置

测试使用预定义的测试数据集和配置文件，确保测试结果的一致性和可重现性。详细配置请参考各测试文件中的设置。
