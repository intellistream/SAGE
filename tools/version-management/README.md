# SAGE 版本管理工具

这个目录包含了管理SAGE项目版本号和项目信息的统一工具。

## 文件说明

### 核心文件
- `sage_version.py` - 统一的版本管理工具（一个脚本解决所有需求）
- `python_config.py` - Python版本配置管理工具
- `sync_python_versions.py` - Python版本同步工具
- `check_project_config.py` - 项目配置一致性检查工具

### 版本源文件  
- `/_version.py` (项目根目录) - 版本信息的单一数据源，包含Python版本配置

## 使用方法

### 1. 查看当前版本信息
```bash
cd tools/version-management
python sage_version.py show
```

这会显示：
- 项目名称和完整名称
- 当前版本号
- 发布日期和状态
- 作者和联系信息
- 项目链接

### 2. 设置新版本号
```bash
cd tools/version-management
python sage_version.py set 0.2.0
```

这会自动：
- 更新根目录的 `_version.py` 文件
- 更新所有 `pyproject.toml` 文件中的版本号
- 更新所有 Python 包的 `__init__.py` 文件
- 保持版本号在整个项目中的一致性

### 3. 更新项目信息
```bash
cd tools/version-management
python sage_version.py update-info
```

这会统一更新：
- 邮箱地址
- 项目名称
- 其他项目元数据

### 4. 显示Python版本配置
```bash
cd tools/version-management
python sage_version.py show-python
```

显示当前的Python版本配置，包括：
- 支持的Python版本
- 默认版本设置
- Ruff和MyPy配置

### 5. 同步Python版本配置
```bash
cd tools/version-management
python sage_version.py sync-python
```

自动同步所有文件中的Python版本设置：
- 所有pyproject.toml文件
- GitHub Actions工作流
- 脚本文件中的Python版本

### 6. 检查项目配置一致性
```bash
cd tools/version-management
python sage_version.py check-config
```

## 注意事项

1. **运行目录**: 建议在 `tools/version-management/` 目录下运行工具
2. **备份**: 大规模更新前建议先备份或提交当前改动
3. **验证**: 更新后建议检查几个关键文件确保更新正确
4. **权限**: 确保对项目文件有写入权限
5. **标准配置**: 项目已迁移到只使用 `pyproject.toml`，符合Python项目最佳实践

### 7. 同步项目配置文件
```bash
cd tools/version-management
python sage_version.py sync-config
```

自动统一两个配置文件，以`_version.py`为准：
- 统一版本号和描述
- 同步联系邮箱
- 修复许可证信息

## 工作原理

### 版本管理架构
1. **单一数据源**: 所有版本信息都定义在根目录的 `_version.py` 文件中
2. **自动同步**: 工具会自动将版本信息同步到项目中的所有相关文件
3. **一致性保证**: 确保整个项目使用相同的版本号和项目信息
4. **统一工具**: 一个脚本 (`sage_version.py`) 解决所有版本管理需求
5. **Python版本统一管理**: 集中管理所有Python版本配置，避免硬编码

### 更新范围
版本更新会影响以下文件：
- `/pyproject.toml` (根项目)
- `/packages/*/pyproject.toml` (所有子包)
- `/packages/*/src/sage/*/__init__.py` (所有Python包)
- 其他包含版本信息的Python文件

### Python版本管理范围
Python版本同步会更新：
- 所有 `pyproject.toml` 文件中的 `requires-python`、`target-version`、`python_version`
- GitHub Actions 工作流中的 `python-version` 设置
- 脚本文件中的 `SAGE_PYTHON_VERSION` 等变量
- Python分类器和版本矩阵配置

### 项目信息更新
- 统一邮箱地址为: `shuhao_zhang@hust.edu.cn`
- 项目完整名称: `Streaming-Augmented Generative Execution`
- 维护项目元数据的一致性

## 开发指南

### 工具架构
`sage_version.py` 是一个完整的版本管理解决方案，包含：
- `SAGEVersionManager` 类：核心版本管理逻辑
- 自动路径发现：智能查找项目根目录
- 统一更新机制：一次性更新所有相关文件

### 添加新的版本文件
如果需要添加新的文件到版本管理中，编辑 `sage_version.py` 中的：
- `_update_pyproject_files()` 方法：添加新的 TOML 文件
- `_update_python_files()` 方法：添加新的 Python 文件

### 修改项目信息
如果需要更新项目信息：
1. 编辑根目录的 `_version.py` 文件
2. 修改 `update_project_info()` 方法中的替换规则
3. 运行 `python sage_version.py update-info`

## 注意事项

1. **运行目录**: 建议在 `tools/version-management/` 目录下运行工具
2. **备份**: 大规模更新前建议先备份或提交当前改动
3. **验证**: 更新后建议检查几个关键文件确保更新正确
4. **权限**: 确保对项目文件有写入权限

## 故障排除

### 常见问题
- **找不到版本文件**: 确保在正确的项目目录结构中运行
- **权限错误**: 检查文件写入权限
- **路径问题**: 工具会自动查找根目录的 `_version.py` 文件

### 调试模式
如果遇到问题，可以查看各个模块的源码了解具体的更新逻辑。

## 版本历史

- v2.0 - 统一版本管理工具：将多个脚本合并为一个 `sage_version.py`
- v1.0 - 初始版本：支持基本的版本管理功能

---

*现在只需要一个脚本就能管理SAGE项目的所有版本信息！*
