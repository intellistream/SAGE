# SAGE Framework 发布脚本

本目录包含用于自动化发布 SAGE Framework 包的脚本。

## 脚本列表

### 1. `publish_all_proprietary.sh` - 完整版闭源发布脚本

功能丰富的闭源包发布脚本，支持多种选项和详细日志。

**功能特性:**
- ✅ 支持所有包或指定包发布
- ✅ 预演模式和实际发布模式
- ✅ 详细的日志记录和错误处理
- ✅ 版本检查和依赖验证
- ✅ 并行发布支持（实验性）
- ✅ 发布摘要和统计信息

**基本用法:**
```bash
# 显示帮助
./scripts/publish_all_proprietary.sh --help

# 预演模式发布所有包
./scripts/publish_all_proprietary.sh --dry-run

# 强制发布所有包（跳过确认）
./scripts/publish_all_proprietary.sh --force

# 只发布指定包
./scripts/publish_all_proprietary.sh --packages sage-cli,sage-core

# 详细输出模式
./scripts/publish_all_proprietary.sh --verbose --dry-run
```

**高级用法:**
```bash
# 指定输出目录
./scripts/publish_all_proprietary.sh --output /tmp/builds

# 跳过版本检查
./scripts/publish_all_proprietary.sh --skip-version-check

# 并行发布（实验性）
./scripts/publish_all_proprietary.sh --parallel --force
```

### 2. `quick_publish_all.sh` - 快速发布脚本

简化版发布脚本，用于日常快速发布。

**特点:**
- 🚀 简单易用，最少的选项
- ⚡ 快速发布所有包
- 📊 简洁的发布摘要

**用法:**
```bash
# 预演模式
./scripts/quick_publish_all.sh --dry-run

# 实际发布
./scripts/quick_publish_all.sh --force

# 交互式发布
./scripts/quick_publish_all.sh
```

## 使用场景

### 日常开发发布
使用快速发布脚本进行日常的包发布：
```bash
./scripts/quick_publish_all.sh --dry-run  # 先预演
./scripts/quick_publish_all.sh            # 实际发布
```

### 生产环境发布
使用完整版脚本进行生产环境的正式发布：
```bash
# 1. 详细预演
./scripts/publish_all_proprietary.sh --dry-run --verbose

# 2. 实际发布
./scripts/publish_all_proprietary.sh --force
```

### 部分包发布
只发布特定的包：
```bash
./scripts/publish_all_proprietary.sh --packages sage-cli,sage-core --verbose
```

## 前置要求

1. **安装 sage-dev-toolkit:**
   ```bash
   pip install -e packages/sage-dev-toolkit
   ```

2. **配置 PyPI 认证:**
   确保 `~/.pypirc` 文件配置正确：
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-AgE...  # 你的 PyPI token

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-AgE...  # 你的 TestPyPI token
   ```

3. **安装依赖工具:**
   ```bash
   pip install twine build tomli
   ```

## 工作流程

两个脚本都遵循相同的基本工作流程：

1. **依赖检查** - 验证必要的工具和环境
2. **包发现** - 自动发现或使用指定的包列表
3. **版本检查** - 检查包版本信息（可选）
4. **用户确认** - 显示将要发布的包并确认（除非使用 --force）
5. **逐包发布** - 使用 `sage-dev proprietary` 发布每个包
6. **结果汇总** - 显示发布结果和统计信息

## 日志和调试

### 完整版脚本日志
完整版脚本会在项目根目录生成详细的日志文件：
```
publish_all_YYYYMMDD_HHMMSS.log
```

### 常见问题排查

**1. 包路径验证失败**
- 确保包目录存在且包含 `pyproject.toml`
- 检查包目录结构是否正确

**2. sage-dev 命令未找到**
```bash
pip install -e packages/sage-dev-toolkit
```

**3. PyPI 认证失败**
- 检查 `~/.pypirc` 文件格式
- 验证 PyPI token 是否有效

**4. 包版本冲突**
- 检查 PyPI 上是否已存在相同版本
- 更新包的版本号

## 安全注意事项

1. **私有 token 保护**: 确保 PyPI token 安全，不要提交到版本控制
2. **预演模式**: 在正式发布前务必使用预演模式测试
3. **版本控制**: 发布前确保代码已提交到版本控制系统
4. **备份**: 重要版本发布前建议创建备份

## 脚本维护

如需修改脚本，请注意：
- 保持向后兼容性
- 添加适当的错误处理
- 更新文档和帮助信息
- 测试所有功能选项

## 支持

如有问题，请：
1. 检查日志文件中的详细错误信息
2. 确认环境和依赖配置
3. 使用 `--verbose` 选项获取更多信息
4. 联系开发团队获取支持
