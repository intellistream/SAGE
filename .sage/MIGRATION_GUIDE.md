# 构建目录迁移指南

## 📋 变更摘要

从 **分散的构建目录** 迁移到 **统一的 `.sage/build/` 目录**。

### 变更前 (旧结构)

```
SAGE/
├── build/                          # middleware 主构建
├── packages/sage-middleware/
│   ├── sage_db_build/              # sage_db 构建
│   ├── sage_flow_build/            # sage_flow 构建
│   └── sage_tsdb_build/            # sage_tsdb 构建
└── packages/.../sageDB/build/      # 子模块内部构建
    packages/.../sageFlow/build/
    packages/.../sageTSDB/build/
```

### 变更后 (新结构) ✨

```
SAGE/
├── .sage/
│   └── build/                      # 🎯 统一构建目录
│       ├── middleware/             # middleware 主构建
│       ├── sage_db/                # sage_db 构建
│       ├── sage_flow/              # sage_flow 构建
│       └── sage_tsdb/              # sage_tsdb 构建
└── packages/                       # 只有源码，无构建产物
```

## ✅ 优势

1. **清晰分离**: 源码和构建产物完全分离
1. **易于管理**: 所有构建产物集中在一个位置
1. **简化清理**: `rm -rf .sage/build/` 清理所有构建
1. **符合 SOTA**: 参考 Rust (target/), CMake 最佳实践
1. **Git 友好**: `.sage/` 已在 gitignore 中

## 🔄 迁移步骤

### 1. 清理旧的构建目录

```bash
# 进入项目根目录
cd /path/to/SAGE

# 清理所有旧的构建产物
make clean

# 或手动删除
rm -rf build/
rm -rf packages/sage-middleware/sage_*_build/
rm -rf packages/sage-middleware/src/sage/middleware/components/*/build/
```

### 2. 重新构建

```bash
# 使用快速安装脚本（推荐）
./quickstart.sh --dev --yes

# 或手动安装
pip install -e packages/sage-middleware --force-reinstall --no-deps
```

### 3. 验证新的构建位置

```bash
# 检查新的构建目录
ls -la .sage/build/

# 应该看到：
# .sage/build/middleware/
# .sage/build/sage_db/
# .sage/build/sage_flow/
# .sage/build/sage_tsdb/
```

## 🔍 详细变更

### 文件修改列表

1. **CMakeLists.txt**

   - 文件: `packages/sage-middleware/CMakeLists.txt`
   - 变更: 使用 `${SAGE_BUILD_ROOT}` 指向 `.sage/build/`

1. **构建脚本**

   - `sage_flow/sageFlow/build.sh`
   - `sage_db/sageDB/build.sh`
   - `sage_tsdb/sageTSDB/build.sh`
   - 变更: 自动检测并使用统一构建目录

1. **Python 构建配置**

   - 文件: `packages/sage-middleware/pyproject.toml`
   - 变更: `build-dir = "../../.sage/build/middleware/{wheel_tag}"`

1. **Git 配置**

   - 文件: `.gitignore`
   - 变更: 添加 `.sage/build/` 忽略规则

1. **清理命令**

   - 文件: `Makefile`
   - 变更: 更新 `make clean` 清理新位置

## 🛠️ 开发者工作流

### 常见任务

#### 完整重新构建

```bash
make clean
pip install -e packages/sage-middleware
```

#### 只清理 C++ 扩展

```bash
rm -rf .sage/build/
pip install -e packages/sage-middleware --no-build-isolation
```

#### 清理特定模块

```bash
# 只重建 sage_flow
rm -rf .sage/build/sage_flow/
cd packages/sage-middleware/src/sage/middleware/components/sage_flow/sageFlow
./build.sh
```

#### 调试构建问题

```bash
# 查看 CMake 配置
cat .sage/build/sage_flow/CMakeCache.txt

# 查看编译日志
tail -f .sage/logs/install.log

# 检查构建产物
find .sage/build -name "*.so"
```

### CI/CD 影响

✅ **无影响** - CI/CD 工作流不需要修改，因为：

- 构建命令保持不变
- 清理仍然通过 `make clean`
- `.sage/` 已在 gitignore 中

## 🐛 故障排除

### 问题 1: 找不到编译的 .so 文件

**症状**: ImportError: cannot import name '\_sage_flow'

**解决方案**:

```bash
# 确保构建目录存在
ls .sage/build/

# 重新安装
pip install -e packages/sage-middleware --force-reinstall
```

### 问题 2: 构建失败

**症状**: CMake 配置错误

**解决方案**:

```bash
# 完全清理后重试
make clean
rm -rf .sage/build/
pip install -e packages/sage-middleware
```

### 问题 3: 磁盘空间不足

**症状**: No space left on device

**解决方案**:

```bash
# 清理构建产物（可释放数 GB 空间）
rm -rf .sage/build/

# 清理缓存
rm -rf .sage/cache/
```

### 问题 4: 旧构建目录仍然存在

**症状**: 构建产物在多个位置

**解决方案**:

```bash
# 删除所有旧位置
rm -rf build/
rm -rf packages/sage-middleware/sage_*_build/
find packages -type d -name "build" -exec rm -rf {} +
```

## 📚 相关资源

- [构建系统最佳实践](../docs/dev-notes/build-system.md)
- [CMake Out-of-Source Builds](https://cmake.org/cmake/help/latest/guide/user-interaction/index.html#out-of-source-builds)
- [Rust Cargo Book - Target Directory](https://doc.rust-lang.org/cargo/guide/build-cache.html)

## 🤝 反馈

如有问题或建议，请：

1. 提交 Issue: https://github.com/intellistream/SAGE/issues
1. 参与讨论: https://github.com/intellistream/SAGE/discussions

______________________________________________________________________

**迁移日期**: 2025-11-05\
**版本**: v1.0\
**状态**: ✅ 已完成
