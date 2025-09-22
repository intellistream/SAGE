# SAGE - Streaming-Augmented Generative Execution

SAGE (Streaming-Augmented Generative Execution) 是一个强大的分布式流数据处理平台的 Meta 包。

## 简介

这是 SAGE 的主要元包，它会自动安装所有核心 SAGE 组件，为用户提供完整的 SAGE 开发和运行环境。

## 包含的组件

### 核心组件 (默认安装)
- **isage-common**: 基础工具和CLI命令
- **isage-kernel**: 核心运行时和任务执行引擎  
- **isage-middleware**: 中间件服务 (存储、队列、缓存等)
- **isage-libs**: 应用示例和工具库

### 可选组件
- **开发工具**: 开发测试工具 (`pip install isage[dev]`)
- **CLI工具**: 命令行增强 (`pip install isage[cli]`)
- **前端界面**: Web 前端界面 (`pip install isage[frontend]`)
- **完整功能**: 所有功能组件 (`pip install isage[full]`)

## 快速开始

### 基础安装
```bash
pip install isage
```

### 开发环境安装
```bash
pip install isage[dev]
```

### 完整安装 (包含所有组件)
```bash
pip install isage[full]
```

### 企业版安装
```bash
pip install isage[enterprise]
```

## 使用示例

```python
import sage

# 创建 SAGE 应用
app = sage.create_app()

# 定义数据流处理
@app.stream("user_events")
def process_events(event):
    return {
        "user_id": event["user_id"],
        "processed_at": sage.now(),
        "result": "processed"
    }

# 启动应用
if __name__ == "__main__":
    app.run()
```

## 命令行工具

安装后，你可以使用以下命令：

```bash
# 查看版本
sage --version

# 创建新项目
sage create my-project

# 启动服务
sage run

# 查看帮助
sage --help
```

## 文档

- [用户指南](https://intellistream.github.io/SAGE-Pub/)
- [API 文档](https://intellistream.github.io/SAGE-Pub/api/)
- [开发者指南](https://intellistream.github.io/SAGE-Pub/dev/)

## 许可证

MIT License

## 贡献

欢迎贡献代码！请查看我们的[贡献指南](CONTRIBUTING.md)。

## 支持

如果你遇到问题或有疑问，请：

1. 查看[文档](https://intellistream.github.io/SAGE-Pub/)
2. 搜索[已知问题](https://github.com/intellistream/SAGE/issues)
3. 创建[新问题](https://github.com/intellistream/SAGE/issues/new)
