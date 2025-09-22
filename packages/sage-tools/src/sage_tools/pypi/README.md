# SAGE PyPI 发布工具

这个目录包含了用于将 SAGE 包发布到 PyPI 的工具和脚本。

## 文件说明

- `publish_sage.sh` - 统一的 PyPI 发布脚本

## 使用方法

### 发布到 PyPI

```bash
# 正式发布到 PyPI
./tools/pypi/publish_sage.sh

# 预演模式，发布到 TestPyPI
./tools/pypi/publish_sage.sh --dry-run

# 仅清理构建产物
./tools/pypi/publish_sage.sh --clean
```

### 发布顺序

脚本会按照依赖关系自动排序发布：

1. `isage-common` - 基础工具包（utils + cli + dev + frontend）
2. `isage-kernel` - 内核功能
3. `isage-middleware` - 中间件
4. `isage-libs` - 应用示例
5. `isage` - Meta 包（依赖所有其他包）

## 前置要求

1. **安装 twine**
   ```bash
   pip install twine
   ```

2. **配置 PyPI 凭据**
   
   创建 `~/.pypirc` 文件：
   ```ini
   [distutils]
   index-servers = pypi testpypi

   [pypi]
   repository = https://upload.pypi.org/legacy/
   username = __token__
   password = pypi-your-token-here

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-your-testpypi-token-here
   ```

3. **确保包版本正确**
   
   检查每个包的 `pyproject.toml` 中的版本号，确保：
   - 版本号遵循语义化版本控制
   - 如果包已存在，需要递增版本号

## 故障排除

### 包已存在错误
如果遇到 "File already exists" 错误：
1. 更新包的版本号在 `pyproject.toml` 中
2. 重新运行发布脚本

### 认证错误
如果遇到认证错误：
1. 检查 `~/.pypirc` 配置是否正确
2. 确认 PyPI token 有效且有发布权限

### 依赖错误
如果包构建失败：
1. 检查 `pyproject.toml` 中的依赖配置
2. 确保所有依赖包已安装

## 包信息

当前 SAGE 包结构：

- **isage** (0.1.4) - Meta 包
- **isage-common** (0.1.4) - 通用工具合集
- **isage-kernel** (0.1.4) - 内核功能
- **isage-middleware** (0.1.4) - 中间件
- **isage-libs** (0.1.4) - 应用示例

所有包都使用 MIT 许可证。
