# SAGE 项目构建系统文档

本目录包含 SAGE 项目构建系统的完整文档，详细介绍了现代 Python 项目的构建规范和最佳实践。

## 文档目录

- [pyproject.toml 详解](./pyproject_toml_guide.md) - 现代 Python 项目配置文件的完整指南
- [setup.py 与 pyproject.toml 联合构建](./setup_py_integration.md) - 传统与现代构建系统的协作机制
- [Python C++ 项目规范](./python_cpp_project_standards.md) - 混合语言项目的标准化开发指南
- [构建系统最佳实践](./build_system_best_practices.md) - 企业级项目构建的推荐做法

## 快速导航

### 开发者必读
- 如果你是新手开发者，建议按顺序阅读所有文档
- 如果你要添加 C++ 扩展，重点阅读 [Python C++ 项目规范](./python_cpp_project_standards.md)
- 如果你要修改项目配置，重点阅读 [pyproject.toml 详解](./pyproject_toml_guide.md)

### 运维人员必读
- 部署相关配置请查看 [构建系统最佳实践](./build_system_best_practices.md)
- CI/CD 配置请参考各文档中的自动化部署章节

## SAGE 项目特色

SAGE 项目采用了现代化的 Python 项目构建标准：

- **标准化模块化**：使用 monorepo 结构管理多个相关包
- **现代构建工具**：基于 pyproject.toml 的标准化配置
- **混合语言支持**：Python 与 C++ 的无缝集成
- **开发工具集成**：完整的代码质量和测试工具链
- **性能优化**：高性能 C++ 扩展与 Python 的灵活性结合

## 技术栈概览

```
┌─────────────────────────────────────────┐
│              Python 生态系统              │
├─────────────────────────────────────────┤
│ pyproject.toml (PEP 518, 621)          │
│ setuptools (build backend)             │
│ pip (package installer)                 │
│ wheel (distribution format)             │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│               C++ 生态系统               │
├─────────────────────────────────────────┤
│ CMake (build system)                    │
│ pybind11 (Python bindings)             │
│ GCC/Clang (compilers)                   │
│ pkg-config (dependency management)      │
└─────────────────────────────────────────┘
```

开始阅读：[pyproject.toml 详解](./pyproject_toml_guide.md) →
