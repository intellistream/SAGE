# Dev-CI 缓存策略文档

## 问题背景

### 原始问题
- `dev-ci.yml` 没有缓存机制，导致4个job（build-sage, quick-check, examples-test, deployment-ready）都需要完整安装SAGE
- 每次安装包括编译C++扩展（sage_db, sage_flow），耗时10-15分钟
- 总CI时间：每个job 15-20分钟 × 4 = 60-80分钟

### 之前尝试的方案及问题
曾经实现过缓存机制，但后来移除了，原因：
- **子模块冲突**：缓存恢复的目录与 `git submodule update --init` 冲突
- **路径问题**：C++扩展在缓存机制下连接路径不正确
- 错误信息：`fatal: destination path '...sage_db' already exists and is not an empty directory`

## 新解决方案

### 核心思路
使用**独立缓存目录** + **手动恢复**机制，避免与子模块冲突

### 关键改进

#### 1. 执行顺序调整
```yaml
1. Checkout Repository
2. Setup Python
3. Initialize Submodules  ← 先初始化子模块
4. Generate Cache Key
5. Cache C++ Build Artifacts  ← 使用独立目录
6. Restore Cached Build Artifacts  ← 手动恢复
7. Install SAGE
```

#### 2. 独立缓存目录
不直接缓存子模块目录，而是使用 `.sage-build-cache/`:
```yaml
path: |
  ~/.cache/pip
  .sage-build-cache/  # 独立缓存目录
```

缓存结构：
```
.sage-build-cache/
├── sage_db/
│   ├── build/       # CMake构建产物
│   ├── install/     # 安装文件
│   └── python/      # .so文件
└── sage_flow/
    ├── build/
    ├── install/
    └── python/
```

#### 3. 手动恢复机制
```bash
if [ "${{ steps.cache-extensions.outputs.cache-hit }}" == "true" ]; then
  # 从独立缓存目录复制到子模块目录
  cp -r .sage-build-cache/sage_db/build/* \
    packages/sage-middleware/.../sage_db/build/
  cp -r .sage-build-cache/sage_db/install/* \
    packages/sage-middleware/.../sage_db/install/
  cp .sage-build-cache/sage_db/python/*.so \
    packages/sage-middleware/.../sage_db/python/
fi
```

#### 4. 手动保存机制
```bash
if [ "${{ steps.cache-extensions.outputs.cache-hit }}" != "true" ]; then
  # 从子模块目录复制到缓存目录
  mkdir -p .sage-build-cache/sage_db
  cp -r packages/sage-middleware/.../sage_db/build \
    .sage-build-cache/sage_db/
  # ... 保存其他文件
fi
```

### 缓存键策略

#### 缓存键组成
```bash
sage-v3-Linux-py311-${SAGE_CODE_HASH}-${SUBMODULE_HASH}-${BUILD_CONFIG_HASH}
```

- `sage-v3`: 版本标识（v3表示新策略）
- `Linux`: 操作系统
- `py311`: Python版本
- `SAGE_CODE_HASH`: Python和C++源码的hash
- `SUBMODULE_HASH`: 子模块状态hash
- `BUILD_CONFIG_HASH`: quickstart.sh和CI配置hash

#### 渐进式回退
```yaml
restore-keys: |
  sage-v3-Linux-py311-
```
允许部分匹配的缓存键，提高缓存命中率

### 缓存失效机制

自动失效触发条件：
1. **代码变更**：Python或C++源文件修改
2. **子模块更新**：子模块commit变化
3. **构建配置变更**：quickstart.sh或CI配置修改
4. **依赖变更**：pyproject.toml修改

## 优势

### 1. 避免冲突
- ✅ 子模块先初始化，再恢复缓存
- ✅ 缓存内容与子模块目录完全分离
- ✅ 不会出现"directory already exists"错误

### 2. 节省时间
- ✅ 缓存命中时跳过C++扩展构建（10-15分钟）
- ✅ 每个job独立缓存，并行执行
- ✅ 预期CI时间减少：60-80分钟 → 30-40分钟

### 3. 可靠性
- ✅ 缓存基于内容hash，确保一致性
- ✅ editable install每次重新执行，确保正确链接
- ✅ 支持渐进式回退，提高命中率

### 4. 可维护性
- ✅ 每个job使用相同的缓存策略，易于维护
- ✅ 缓存键自动生成，无需手动管理版本号
- ✅ 清晰的缓存状态报告

## 监控和调试

### 查看缓存状态
每次运行会显示：
```
🔑 生成缓存键（基于代码内容）...
📄 SAGE代码hash: abc123...
📦 子模块hash: def456...
⚙️ 构建配置hash: ghi789...
🔑 最终缓存键: sage-v3-Linux-py311-...
✅ 缓存命中！恢复C++扩展构建产物...
```

### 缓存未命中的原因
如果缓存未命中，检查哪个hash发生了变化：
- SAGE代码hash变化 → Python或C++源文件被修改
- 子模块hash变化 → 子模块commit更新
- 构建配置hash变化 → quickstart.sh或CI配置修改

### 强制重建缓存
如果需要强制重建缓存：
1. 修改 `sage-v3` 为 `sage-v4`（所有4个job）
2. 提交并推送
3. 新的缓存键会导致缓存未命中，触发重建

## 未来改进空间

### 可能的优化
1. **共享缓存**：考虑在jobs间共享artifacts，而不是每个job独立缓存
2. **增量构建**：只重建修改的扩展
3. **缓存清理**：定期清理旧的缓存版本

### 待观察的指标
1. 缓存命中率
2. 实际节省的时间
3. 缓存大小和存储成本
4. C++扩展链接的稳定性

## 相关Issue

- #866: dev-ci.yml安装多次，改回用cache试试
- 相关Commit: 9c1e0d05（移除缓存）、f9926cad（之前的缓存实现）

## 更新日志

- 2025-10-01: 实现v3缓存策略，使用独立缓存目录解决子模块冲突
- 之前: 移除了v2缓存策略，因为子模块冲突问题
