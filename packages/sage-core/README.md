# SAGE Framework Meta Package

SAGE Framework是一个统一的AI推理和数据流处理框架，提供完整的端到端解决方案。

## 简介

这是SAGE框架的元包(meta package)，它集成了以下核心组件：

- **sage-kernel**: 统一内核，包含核心运行时、工具和CLI
- **sage-middleware**: 中间件组件，包含LLM中间件服务
- **sage-userspace**: 用户空间组件，提供高级API和应用框架
- **sage-dev-toolkit**: 开发工具包，提供开发和调试工具

## 安装

```bash
pip install intellistream-sage
```

## 快速开始

```python
import sage

# 创建本地环境
env = sage.LocalEnvironment()

# 创建数据流
stream = env.from_collection([1, 2, 3, 4, 5])

# 应用转换
result = stream.map(lambda x: x * 2).collect()
print(result)  # [2, 4, 6, 8, 10]
```

## 文档

更多详细信息请参考：
- [官方文档](https://intellistream.github.io/SAGE-Pub/)
- [GitHub仓库](https://github.com/intellistream/SAGE)

## 许可证

MIT License
