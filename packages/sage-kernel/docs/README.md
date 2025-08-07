# SAGE Kernel Documentation

欢迎使用 SAGE Kernel 框架！这是一个强大的流数据处理和分布式计算内核。

## Documentation Structure

### Core Documentation
- [Architecture Overview](architecture.md) - System design and component relationships
- [Quick Start Guide](guides/quickstart.md) - Get up and running quickly
- [CLI Reference](components/cli.md) - Command-line interface documentation
- [Best Practices](best-practices.md) - Performance optimization and development guidelines
- [FAQ](faq.md) - Frequently asked questions and troubleshooting

### API Documentation
- [Environments API](api/environments.md) - Local and remote execution environments
- [DataStreams API](api/datastreams.md) - Stream processing and data flow
- [Functions API](api/functions.md) - Custom function development and registration
- [Connected Streams API](api/connected-streams.md) - Multi-stream processing and complex pipelines

### Component Guides
- [Core Concepts](concepts.md) - Fundamental concepts and terminology

### Examples and Tutorials
- [Examples Collection](examples/README.md) - Practical examples and use cases

### Additional Resources
- [GitHub Repository](https://github.com/intellistream/SAGE)
- [Issue Tracker](https://github.com/intellistream/SAGE/issues)

## 🚀 快速开始

```python
from sage.core.api.local_environment import LocalEnvironment

# 创建本地环境
env = LocalEnvironment("my_app")

# 创建数据流管道
stream = env.from_batch([1, 2, 3, 4, 5])
result = stream.map(lambda x: x * 2).sink(print)

# 提交执行
env.submit()
```

## 📋 主要特性

- **🔄 流式处理**: 支持无限数据流的实时处理
- **🌐 分布式**: 原生支持集群部署和分布式计算
- **🎯 类型安全**: 基于Python泛型的编译时类型检查
- **🔌 可扩展**: 插件化架构，支持自定义算子和服务
- **🛠️ 工具完善**: 完整的CLI工具链和监控体系
- **🏢 企业级**: 提供商业版高级功能

## 📞 获取帮助

- [GitHub Issues](https://github.com/intellistream/SAGE/issues) - 报告问题
- [讨论区](https://github.com/intellistream/SAGE/discussions) - 社区讨论
- [官方文档](https://intellistream.github.io/SAGE-Pub/) - 完整文档

## 📄 许可证

MIT License - 详见 [LICENSE](../../../LICENSE) 文件
