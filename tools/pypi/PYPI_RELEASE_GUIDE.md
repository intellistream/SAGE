# SAGE PyPI 发布指南

本指南包含了将 SAGE 开源包发布到 PyPI 的完整流程和工具。

## 文件概览

### 脚本文件
- `upload_to_pypi.sh` - 主要的PyPI上传脚本
- `setup_pypi_auth.sh` - PyPI认证设置助手
- `manage_versions.sh` - 版本管理工具
- `pypi_config.ini` - 配置文件

### 支持的开源包
- `sage-kernel` - 核心处理引擎
- `sage-middleware` - 中间件层  
- `sage-userspace` - 用户空间库
- `sage` - 主包
- `sage-dev-toolkit` - 开发工具包
- `sage-frontend` - Web前端

## 快速开始

### 1. 首次设置

```bash
# 设置 PyPI 认证
./scripts/setup_pypi_auth.sh --interactive

# 检查当前版本状态
./scripts/manage_versions.sh show

# 检查版本一致性
./scripts/manage_versions.sh check
```

### 2. 上传所有包到 PyPI

```bash
# 预演模式（推荐先运行）
./scripts/upload_to_pypi.sh --dry-run

# 实际上传
./scripts/upload_to_pypi.sh
```

### 3. 上传特定包

```bash
# 上传特定包
./scripts/upload_to_pypi.sh sage-kernel

# 上传多个包
./scripts/upload_to_pypi.sh sage-kernel sage-frontend
```

## 详细使用指南

### PyPI 认证设置

#### 方法一：使用脚本设置（推荐）

```bash
# 交互式设置
./scripts/setup_pypi_auth.sh --interactive

# 检查现有配置
./scripts/setup_pypi_auth.sh --check

# 重置配置
./scripts/setup_pypi_auth.sh --reset
```

#### 方法二：手动设置

1. 获取 API Token:
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

2. 设置环境变量:
   ```bash
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

3. 或创建 `~/.pypirc` 文件:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### 版本管理

#### 显示当前版本

```bash
./scripts/manage_versions.sh show
```

#### 版本递增

```bash
# 递增补丁版本 (1.0.0 -> 1.0.1)
./scripts/manage_versions.sh bump patch sage-kernel

# 递增次要版本 (1.0.0 -> 1.1.0)
./scripts/manage_versions.sh bump minor --all

# 递增主要版本 (1.0.0 -> 2.0.0)
./scripts/manage_versions.sh bump major sage-frontend
```

#### 设置特定版本

```bash
# 设置单个包版本
./scripts/manage_versions.sh set 1.2.0 sage-kernel

# 设置所有包版本
./scripts/manage_versions.sh set 1.2.0 --all
```

#### 同步版本

```bash
# 同步所有包到最常见的版本
./scripts/manage_versions.sh sync
```

#### 创建 Git 标签

```bash
# 设置版本并创建 git 标签
./scripts/manage_versions.sh set 1.2.0 --all --git-tag
```

### PyPI 上传

#### 基本上传

```bash
# 上传所有包
./scripts/upload_to_pypi.sh

# 预演模式
./scripts/upload_to_pypi.sh --dry-run

# 详细输出
./scripts/upload_to_pypi.sh --verbose
```

#### 测试环境

```bash
# 上传到 TestPyPI
./scripts/upload_to_pypi.sh --test

# 指定包上传到 TestPyPI
./scripts/upload_to_pypi.sh --test sage-kernel
```

#### 高级选项

```bash
# 强制重新构建
./scripts/upload_to_pypi.sh --force

# 跳过检查
./scripts/upload_to_pypi.sh --skip-checks

# 跳过构建，直接上传现有包
./scripts/upload_to_pypi.sh --skip-build
```

## 完整发布流程

### 1. 发布前准备

```bash
# 1. 检查当前状态
./scripts/manage_versions.sh show
./scripts/manage_versions.sh check

# 2. 更新版本号（例如递增次要版本）
./scripts/manage_versions.sh bump minor --all

# 3. 预演上传
./scripts/upload_to_pypi.sh --dry-run
```

### 2. 测试发布

```bash
# 上传到 TestPyPI 进行测试
./scripts/upload_to_pypi.sh --test

# 验证安装
pip install --index-url https://test.pypi.org/simple/ sage-kernel
```

### 3. 正式发布

```bash
# 正式上传到 PyPI
./scripts/upload_to_pypi.sh

# 创建 git 标签（如果还没有创建）
git tag v$(./scripts/manage_versions.sh show | grep sage-kernel | awk '{print $2}')
git push origin --tags
```

## 故障排除

### 常见问题

#### 1. 认证失败
```
错误: HTTP Error 403: Invalid or non-existent authentication information
```

解决方案:
- 检查 API token 是否正确
- 确认 token 有上传权限
- 运行 `./scripts/setup_pypi_auth.sh --check`

#### 2. 版本冲突
```
错误: File already exists
```

解决方案:
- 递增版本号: `./scripts/manage_versions.sh bump patch <package>`
- 或使用 `--skip-existing` 选项

#### 3. 构建失败
```
错误: 构建失败，未找到 wheel 文件
```

解决方案:
- 检查 `pyproject.toml` 配置
- 确保包结构正确
- 运行 `./scripts/upload_to_pypi.sh --verbose` 查看详细错误

#### 4. 依赖问题
```
错误: Could not find a version that satisfies the requirement
```

解决方案:
- 检查依赖版本是否存在
- 使用测试环境验证依赖
- 考虑放宽版本限制

### 调试技巧

#### 1. 使用预演模式
```bash
./scripts/upload_to_pypi.sh --dry-run --verbose
```

#### 2. 测试单个包
```bash
./scripts/upload_to_pypi.sh --test sage-kernel --verbose
```

#### 3. 检查包内容
```bash
python -m zipfile -l dist/package-name-version-py3-none-any.whl
```

#### 4. 手动验证
```bash
# 手动构建
cd packages/sage-kernel
python -m build

# 手动检查
python -m twine check dist/*

# 手动上传到测试环境
python -m twine upload --repository testpypi dist/*
```

## 配置文件

### pypi_config.ini

该文件包含上传的各种配置选项：

```ini
[packages]
# 控制哪些包会被上传
sage-kernel = true
sage-dev-toolkit = true
# ...

[validation]
# 控制验证行为
check_package_integrity = true
validate_dependencies = true
# ...
```

## 安全注意事项

1. **保护 API Token**: 
   - 不要将 token 提交到代码库
   - 使用环境变量或 `~/.pypirc` 文件
   - 定期轮换 token

2. **使用 TestPyPI**:
   - 总是先在 TestPyPI 测试
   - 验证包可以正确安装和导入

3. **版本管理**:
   - 遵循语义化版本控制
   - 确保版本号唯一性
   - 使用 git 标签跟踪发布

4. **审查代码**:
   - 发布前审查所有更改
   - 确保没有敏感信息泄露
   - 验证开源许可证

## 维护

定期维护任务：

1. **更新依赖**: 检查和更新包依赖
2. **清理构建**: 定期清理构建文件
3. **监控发布**: 监控 PyPI 上的包状态
4. **文档更新**: 保持文档与实际操作同步

## 支持

如果遇到问题：

1. 查看本文档的故障排除部分
2. 检查脚本的帮助信息: `./scripts/upload_to_pypi.sh --help`
3. 查看 PyPI 官方文档: https://packaging.python.org/
4. 联系维护团队
