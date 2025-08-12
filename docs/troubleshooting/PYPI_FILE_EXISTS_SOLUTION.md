# PyPI 文件已存在错误 - 解决方案指南

## 问题描述
发布包到 PyPI 时遇到 "File already exists" 错误，这是因为 PyPI 不允许覆盖已存在的文件。

## 解决方案

### 方案1: 使用改进的发布脚本（推荐）

#### 1.1 自动递增版本发布
```bash
# 自动递增版本并发布（推荐）
./scripts/quick_publish_all.sh --auto-increment --no-dry-run

# 预演模式查看会做什么
./scripts/quick_publish_all.sh --auto-increment --dry-run --force
```

#### 1.2 手动管理版本
```bash
# 查看所有包的当前版本
./scripts/version_manager.sh list

# 递增所有包的patch版本 (0.1.2 -> 0.1.3)
./scripts/version_manager.sh increment

# 递增指定包的版本
./scripts/version_manager.sh increment --packages sage-cli,sage-core

# 递增minor版本 (0.1.2 -> 0.2.0)  
./scripts/version_manager.sh increment --type minor

# 然后正常发布
./scripts/quick_publish_all.sh --no-dry-run
```

### 方案2: 单包处理

#### 2.1 单独递增特定包版本
```bash
# 手动编辑 packages/sage-cli/pyproject.toml
# 将 version = "0.1.2" 改为 version = "0.1.3"

# 或使用脚本
./scripts/version_manager.sh increment --packages sage-cli

# 然后发布单个包
sage-dev proprietary packages/sage-cli --no-dry-run --force
```

#### 2.2 查看包的详细信息
```bash
# 查看包信息
sage-dev publish info packages/sage-cli

# 检查PyPI上的现有版本
pip index versions intellistream-sage-cli
```

### 方案3: 紧急情况处理

如果确实需要重新发布相同版本（不推荐），可以：

1. **联系PyPI管理员删除现有版本** (很少批准)
2. **使用不同的包名** (如添加时间戳后缀)
3. **发布到TestPyPI进行测试**:
   ```bash
   # 发布到TestPyPI
   sage-dev proprietary packages/sage-cli --no-dry-run --force --repository testpypi
   ```

## 工作流程建议

### 日常开发发布
1. **开发完成后检查版本**:
   ```bash
   ./scripts/version_manager.sh list
   ```

2. **预演发布查看效果**:
   ```bash
   ./scripts/quick_publish_all.sh --dry-run --force
   ```

3. **自动处理版本冲突并发布**:
   ```bash
   ./scripts/quick_publish_all.sh --auto-increment --no-dry-run
   ```

### 生产环境发布
1. **手动递增版本号**:
   ```bash
   ./scripts/version_manager.sh increment --type minor
   ```

2. **详细预演**:
   ```bash
   ./scripts/publish_all_proprietary.sh --dry-run --verbose
   ```

3. **正式发布**:
   ```bash
   ./scripts/publish_all_proprietary.sh --no-dry-run --force
   ```

## 脚本新增功能

### quick_publish_all.sh 新增选项
- `--auto-increment`: 遇到文件已存在错误时自动递增patch版本号
- 改进的错误处理：明确区分文件已存在错误和其他错误

### 新增 version_manager.sh 脚本
- `list`: 显示所有包的版本信息
- `increment`: 批量递增版本号
- `--packages`: 指定特定包
- `--type`: 指定递增类型 (major/minor/patch)

## 版本号规则

遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范:
- **MAJOR**: 不兼容的API修改 (1.0.0 -> 2.0.0)
- **MINOR**: 向后兼容的功能性新增 (1.0.0 -> 1.1.0)  
- **PATCH**: 向后兼容的bug修复 (1.0.0 -> 1.0.1)

## 常见错误处理

### 错误1: File already exists
```
HTTPError: 400 Bad Request from https://upload.pypi.org/legacy/
File already exists ('intellistream_sage_cli-0.1.2-py3-none-any.whl'...)
```
**解决**: 使用 `--auto-increment` 或手动递增版本号

### 错误2: Invalid authentication credentials  
**解决**: 检查 `~/.pypirc` 配置文件

### 错误3: Package name already taken
**解决**: 修改包名或联系PyPI管理员

### 错误4: File too large
**解决**: 优化包大小或分拆包

## 预防措施

1. **发布前检查**: 总是先用 `--dry-run` 预演
2. **版本管理**: 建立版本递增的工作流程
3. **测试发布**: 先发布到TestPyPI测试
4. **自动化**: 使用改进的脚本处理常见错误

## 相关文档
- [PyPI Help - File Name Reuse](https://pypi.org/help/#file-name-reuse)
- [Semantic Versioning](https://semver.org/)
- [Python Packaging User Guide](https://packaging.python.org/)
