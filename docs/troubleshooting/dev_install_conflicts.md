# SAGE 开发环境依赖冲突问题解决方案

## 问题分析

在运行 `make dev-install` 时出现的依赖冲突错误主要由以下几个原因导致：

### 1. 过时的包残留
- `sage-service` 包引用了不存在的老依赖：`sage-core`, `sage-lib`, `sage-utils`
- 这些是旧版本的包名，现在已经被重构合并到其他包中

### 2. 版本冲突
- `cohere` 版本冲突：需要 5.16.2，但安装了 5.16.1
- `sentence-transformers` 版本冲突：需要 5.0.0，但安装了 3.1.1
- `vllm` 版本冲突：需要 >=0.8.0，但安装了 0.1.2

### 3. 循环依赖
- 多个包同时安装时可能产生循环依赖问题

## 解决方案

### 方案1: 安全的分步开发安装（推荐）

```bash
make dev-install-safe
```

这个方案会：
1. 清理所有现有SAGE安装
2. 预安装基础依赖，避免版本冲突
3. 按依赖顺序逐个安装包
4. 避免循环依赖问题

### 方案2: 手动分步安装

```bash
# 1. 清理现有安装
pip uninstall -y sage sage-kernel sage-middleware sage-userspace sage-cli sage-dev-toolkit sage-service

# 2. 安装基础依赖
pip install --constraint ./scripts/constraints.txt torch==2.7.1 torchvision==0.22.1 transformers numpy

# 3. 逐个安装核心包
pip install -e ./packages/sage-kernel
pip install -e ./packages/sage-dev-toolkit

# 4. 选择性安装其他包
pip install -e ./packages/sage-middleware  # 如果需要
pip install -e ./packages/sage-userspace   # 如果需要
```

### 方案3: 使用修复的requirements-dev.txt

新的 `requirements-dev.txt` 文件已经：
- 预先指定了基础依赖版本
- 按正确的依赖顺序排列
- 暂时注释掉了有冲突的包

## 文件更新

### 1. 修复的文件
- `requirements-dev.txt` - 修复依赖顺序和版本冲突
- `scripts/install_dev_stepwise.sh` - 新的安全分步安装脚本
- `Makefile` - 添加了 `dev-install-safe` 目标

### 2. 清理的内容
- 删除了所有 `*egg-info` 目录
- 卸载了有冲突的残留包

## 使用建议

### 开发者
```bash
# 推荐：安全的开发环境安装
make dev-install-safe

# 或者：传统的开发安装（可能有冲突）
make dev-install
```

### 普通用户
```bash
# 推荐：智能混合安装
make install-smart
```

## 故障排除

如果仍然遇到依赖冲突：

1. **完全清理环境**：
   ```bash
   pip freeze | grep -v "^-e" | cut -d"=" -f1 | xargs pip uninstall -y
   ```

2. **重新创建conda环境**：
   ```bash
   conda deactivate
   conda remove -n sage --all
   conda create -n sage python=3.11
   conda activate sage
   ```

3. **使用虚拟环境**：
   ```bash
   python -m venv sage_env
   source sage_env/bin/activate  # Linux/Mac
   # 或 sage_env\Scripts\activate  # Windows
   ```

## 预防措施

1. **使用约束文件**：确保 `scripts/constraints.txt` 和 `scripts/constraints-build.txt` 保持更新
2. **定期清理**：运行 `make clean` 清理构建缓存
3. **版本锁定**：在生产环境使用 `requirements-lock.txt`
