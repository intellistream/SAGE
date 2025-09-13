#!/usr/bin/env python3
"""
SAGE README 模板生成工具
从配置文件动态生成 README 内容
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict

import tomli


def load_project_config(config_path: str = "project_config.toml") -> Dict[str, Any]:
    """加载项目配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "rb") as f:
        return tomli.load(f)


def generate_main_package_readme(package_key: str, config: Dict[str, Any]) -> str:
    """为主包生成 README 内容"""
    project_info = config["project"]
    urls = config["urls"]
    package_descriptions = config["package_descriptions"]

    template = f"""# SAGE Framework Meta Package

SAGE Framework是一个统一的AI推理和数据流处理框架，提供完整的端到端解决方案。

## 简介

这是SAGE框架的元包(meta package)，它集成了以下核心组件：

- **sage-kernel**: 统一内核，包含核心运行时、工具和CLI
- **sage-middleware**: 中间件组件，包含LLM中间件服务
- **sage-userspace**: 用户空间组件，提供高级API和应用框架
- **sage-dev-toolkit**: 开发工具包，提供开发和调试工具

## 安装

```bash
pip install {package_key}
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
- [官方文档]({urls['documentation']})
- [GitHub仓库]({urls['repository']})

## 许可证

{config['project']['license']} License
"""
    return template


def generate_installation_guide(config: Dict[str, Any]) -> str:
    """生成安装指南"""
    project_info = config["project"]
    urls = config["urls"]
    packages = config["packages"]

    # 生成包名列表
    package_list = ""
    for new_name, path in packages.items():
        if new_name == "intellistream":  # 跳过抢注包
            continue
        package_list += (
            f"| `{new_name}` | {config['package_descriptions'][new_name]} |\\n"
        )

    template = f"""# SAGE 安装指南

## 📦 快速安装

### 一键安装（推荐）

```bash
pip install {project_info['package_prefix']}
```

SAGE 框架采用模块化设计，您可以根据需要安装不同的组件：

| 包名 | 说明 |
|------|------|
{package_list}

**便捷导入**: 安装后直接使用 `import sage` 即可开始使用

## 🚀 快速安装

### 完整安装（推荐）

```bash
# 安装主包
pip install {project_info['package_prefix']}
```

### 按需安装

```bash
# 只安装核心组件
pip install {project_info['package_prefix']}-kernel

# 安装中间件（包含 LLM 功能）
pip install {project_info['package_prefix']}-middleware

# 安装用户空间库（包含高级 API）
pip install {project_info['package_prefix']}-userspace

# 安装开发工具
pip install {project_info['package_prefix']}-dev-toolkit

# 安装 Web 前端
pip install {project_info['package_prefix']}-frontend
```

### 开发环境安装

```bash
# 安装带开发依赖的完整环境
pip install {project_info['package_prefix']}[dev]

# 或者从源码安装（推荐开发者使用）
git clone {urls['repository']}
cd SAGE
pip install -e ".[dev]"
```

## � 探索示例

安装后可以直接使用内置示例：

```python
# 访问示例代码
from sage.examples.tutorials import hello_world
from sage.examples.rag import qa_simple
from sage.examples.streaming import kafka_query

# 示例包含：
# - sage.examples.tutorials.*  # 基础教程
# - sage.examples.rag.*        # RAG 应用示例  
# - sage.examples.agents.*     # 多智能体示例
# - sage.examples.streaming.*  # 流处理示例
# - sage.examples.memory.*     # 记忆管理示例
# - sage.examples.evaluation.* # 评估工具示例
```

## �📝 使用示例

安装后的 Python 导入保持不变：

```python
# 导入路径没有变化
import sage
from sage.kernels import DataStream
from sage.middleware import LLMService
from sage.userspace import RAGPipeline

# 使用示例
env = sage.LocalEnvironment()
stream = env.from_collection([1, 2, 3, 4, 5])
result = stream.map(lambda x: x * 2).collect()
print(result)  # [2, 4, 6, 8, 10]
```

## 🔄 版本管理

SAGE 框架定期更新，建议保持最新版本：

```bash
# 升级到最新版本
pip install --upgrade {project_info['package_prefix']}

# 查看当前版本
python -c "import sage; print(sage.__version__)"
```

## 🆘 故障排除

### 依赖问题

```bash
# 强制重新安装
pip install --force-reinstall {project_info['package_prefix']}

# 或者创建新的虚拟环境
python -m venv venv_sage
source venv_sage/bin/activate  # Linux/Mac
# venv_sage\\Scripts\\activate  # Windows
pip install {project_info['package_prefix']}
```

## 📞 获取帮助

- 📖 [官方文档]({urls['documentation']})
- 🐛 [问题反馈]({urls['issues']})
- 📧 [联系我们](mailto:{project_info['contact_email']})

---

**现在 SAGE 安装更简单了！** 🎉
"""
    return template


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python generate_readme.py <command> [args]")
        print("命令:")
        print("  main-package <package-name>  为主包生成README")
        print("  installation                 生成安装指南")
        sys.exit(1)

    command = sys.argv[1]

    # 加载项目配置
    try:
        config = load_project_config()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    if command == "main-package":
        if len(sys.argv) < 3:
            print("错误: 请指定包名")
            sys.exit(1)

        package_key = sys.argv[2]
        if package_key not in config["packages"]:
            print(f"错误: 未知包名 {package_key}")
            print(f"可用包: {', '.join(config['packages'].keys())}")
            sys.exit(1)

        readme_content = generate_main_package_readme(package_key, config)
        print(readme_content)

    elif command == "installation":
        installation_content = generate_installation_guide(config)
        print(installation_content)

    else:
        print(f"错误: 未知命令 {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
