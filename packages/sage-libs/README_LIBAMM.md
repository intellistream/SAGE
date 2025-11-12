# SAGE Libs - LibAMM 编译指南

## 🎯 快速开始

### 默认安装（不含 LibAMM）

```bash
# 安装 sage-libs（跳过 LibAMM，适合大多数用户）
pip install -e packages/sage-libs
```

✅ **推荐**：适合所有开发环境，无内存压力

### 带 LibAMM 的完整安装

```bash
# 需要 16GB+ 内存
BUILD_LIBAMM=1 pip install -e packages/sage-libs --no-build-isolation
```

⚠️ **注意**：需要大内存环境，详见下文

---

## 📚 详细说明

### 为什么 LibAMM 是可选的？

LibAMM 是高性能矩阵计算库，依赖 PyTorch C++ API。编译时：

| 资源 | 需求 |
|------|------|
| **内存** | 单文件峰值 500-700MB |
| **总内存** | 建议 16GB+ (物理 + swap) |
| **编译时间** | 10-30 分钟（取决于 CPU） |
| **PyTorch** | >= 2.0.0 |

在内存受限环境（如 WSL、虚拟机）容易触发 OOM killer，导致系统重启。

### 方案对比

| 方案 | 内存需求 | 安装时间 | 适用场景 |
|------|----------|----------|----------|
| **跳过 LibAMM**（默认） | < 1GB | < 1 分钟 | ✅ 推荐：开发、测试 |
| **从源码编译** | 16GB+ | 10-30 分钟 | 需要自定义 LibAMM |
| **预编译包**（未来） | < 1GB | < 1 分钟 | ✅ 推荐：生产环境 |

---

## 🔧 编译 LibAMM

### 前提条件检查

```bash
# 1. 检查可用内存
free -h

# 需要看到：
# Mem:  可用 + Swap >= 16GB

# 2. 安装 PyTorch
pip install torch>=2.0.0
```

### 增加 Swap（如果内存不足）

```bash
# 创建 8GB swap 文件
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 验证
free -h
```

### 编译

```bash
# 方式1：环境变量
BUILD_LIBAMM=1 pip install -e packages/sage-libs --no-build-isolation

# 方式2：卸载后重装
pip uninstall isage-libs -y
BUILD_LIBAMM=1 pip install -e packages/sage-libs --no-build-isolation
```

### 验证

```python
# 检查 LibAMM 是否可用
python3 << 'EOF'
try:
    from sage.libs.libamm.python import PyAMM
    print("✅ LibAMM 编译成功！")
except ImportError as e:
    print(f"❌ LibAMM 不可用: {e}")
EOF
```

---

## 🐛 常见问题

### 1. 编译时系统重启/卡死

**原因**：OOM killer 杀掉编译进程

**解决**：
```bash
# 检查内存
free -h
dmesg | grep -i "killed process"  # 查看是否被 OOM killer 杀掉

# 增加 swap 或使用预编译包
```

### 2. 编译错误：`torch::linalg` 未定义

**原因**：PyTorch 版本过旧或 C++ API 不兼容

**解决**：
```bash
# 更新 PyTorch
pip install --upgrade torch>=2.0.0
```

### 3. 只想使用 SAGE 其他功能，不需要 LibAMM

**解决**：不用做任何特殊处理，默认安装即可
```bash
pip install -e packages/sage-libs  # LibAMM 会自动跳过
```

---

## 📊 内存监控

编译过程中监控内存：

```bash
# 实时查看内存使用
watch -n 1 'free -h; ps aux | grep cc1plus | grep -v grep'
```

---

## 🏗️ 技术细节

### 已实施的内存优化

LibAMM 的 CMakeLists.txt 包含以下优化：

```cmake
# 1. Unity Build：减少头文件重复解析
set(CMAKE_UNITY_BUILD ON)
set(CMAKE_UNITY_BUILD_BATCH_SIZE 2)

# 2. 降低优化级别
set(CMAKE_CXX_FLAGS_RELEASE "-O0 -g0")  # 原来是 -O3

# 3. 单线程编译
set(CMAKE_BUILD_PARALLEL_LEVEL 1)

# 4. 限制模板深度
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ftemplate-depth=128")

# 5. 积极内存回收
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} --param ggc-min-expand=20")
```

即便如此，仍需要大内存环境。

### 为什么 PyTorch C++ API 占用这么多内存？

```cpp
#include <torch/extension.h>  // 展开后 ~30 万行代码

// 编译器需要：
// 1. 解析 9252 个头文件
// 2. 实例化数千个模板
// 3. 生成符号表
// 4. 执行优化
```

这是 PyTorch C++ API 的设计特点，无法绕过。

---

## 📝 相关文档

- [完整安装指南](./LIBAMM_INSTALLATION.md)
- [内存优化笔记](../../docs/dev-notes/l3-libs/libamm-memory-optimization.md)

---

## 🤝 贡献

如果你：
- 成功在特定环境下编译了 LibAMM
- 有更好的内存优化方案
- 发现了编译问题

欢迎提交 Issue 或 PR！
