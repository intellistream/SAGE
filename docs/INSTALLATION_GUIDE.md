# SAGE 安装指南

> 根据您的使用场景选择合适的安装方式

## 📋 快速选择

| 我想... | 安装命令 | 大小 | 包含内容 |
|--------|---------|------|---------|
| **开发 SAGE 应用** ✅ | `pip install isage` | ~200MB | 核心 + CLI + Web UI |
| 部署到生产环境 | `pip install isage[core]` | ~100MB | 仅运行时 |
| 学习示例应用 | `pip install isage[full]` | ~300MB | + 医疗/视频应用 |
| 修改 SAGE 框架 | `pip install isage[dev]` | ~400MB | + 开发工具 |

## 🎯 详细说明

### 1. 标准安装（推荐）

**场景**：日常应用开发，最常用的安装方式

```bash
pip install isage
```

**包含**：
- ✅ **L1-L4**: 完整核心功能
  - 流式数据处理引擎
  - 算法库和 Agent 框架
  - RAG/LLM operators
- ✅ **L6**: 用户接口
  - `sage` CLI 命令
  - Studio Web UI
- ✅ 数据科学库（numpy, pandas, matplotlib, scipy, jupyter）

**适合**：
- 👨‍💻 应用开发者
- 📊 数据科学家
- 🎓 学生和教师

**你可以**：
```bash
# 使用 CLI
sage --help
sage pipeline build
sage studio start

# 开发 Python 应用
from sage.kernel.api import LocalEnvironment
env = LocalEnvironment()
# ... 你的代码
```

---

### 2. 核心运行时

**场景**：生产环境部署，最小化依赖

```bash
pip install isage[core]
```

**包含**：
- ✅ **L1**: 基础设施（common）
- ✅ **L2**: 平台服务（platform）
- ✅ **L3**: 核心引擎（kernel）
- ❌ 不包含：CLI、Web UI、示例应用

**适合**：
- 🐳 Docker 容器化部署
- ☁️ 云服务器运行
- 📦 最小化镜像

**限制**：
- 无 `sage` CLI 命令
- 无 Studio Web UI
- 仅能运行已有的 pipeline 代码

---

### 3. 完整功能

**场景**：学习 SAGE，运行示例应用

```bash
pip install isage[full]
```

**额外包含**：
- ✅ **sage-apps**: 示例应用
  - 医疗诊断（腰椎 MRI 分析）
  - 视频智能分析
- ✅ **sage-benchmark**: 性能测试
  - RAG 基准测试
  - 内存性能评估

**适合**：
- 🎓 学习 SAGE 的新用户
- 📚 查看示例代码
- 🔬 性能评估和研究

**你可以**：
```bash
# 运行医疗诊断示例
cd examples/medical_diagnosis
python run_diagnosis.py

# 运行 RAG benchmark
python -m sage.benchmark.benchmark_rag.evaluation.pipeline_experiment
```

---

### 4. 框架开发

**场景**：修改 SAGE 框架源代码

```bash
pip install isage[dev]
```

**额外包含**：
- ✅ 开发工具套件
  - pytest, black, ruff, mypy
  - pre-commit hooks
  - 代码质量工具
- ✅ 完整的测试环境

**适合**：
- 🛠️ SAGE 框架贡献者
- 🔬 研究新功能
- 📝 提交 Pull Request

**你可以**：
```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 安装开发环境
pip install -e packages/sage[dev]

# 运行测试
sage dev test

# 代码质量检查
sage dev lint
```

---

## 🏗️ 架构对应关系

```
pip install isage          →  L1 + L2 + L3 + L4 + L6
pip install isage[core]    →  L1 + L2 + L3
pip install isage[full]    →  L1 + L2 + L3 + L4 + L5 + L6
pip install isage[dev]     →  L1 + L2 + L3 + L4 + L5 + L6 + dev tools
```

**层级说明**：
- **L1**: sage-common（基础设施）
- **L2**: sage-platform（平台服务）
- **L3**: sage-kernel + sage-libs（核心引擎 + 算法库）
- **L4**: sage-middleware（领域算子）
- **L5**: sage-apps + sage-benchmark（应用 + 测试）
- **L6**: sage-studio + sage-tools（Web UI + CLI）

---

## 💡 常见问题

### Q: 我应该选择哪个安装方式？

**A**: 大多数用户选择默认的 `pip install isage` 即可。

- 如果你想**开发应用**：`pip install isage`
- 如果你是**生产部署**：`pip install isage[core]`
- 如果你想**学习示例**：`pip install isage[full]`
- 如果你要**贡献代码**：`pip install isage[dev]`

### Q: 为什么默认不包含 sage-apps 和 sage-benchmark？

**A**: 
- `sage-apps` 包含特定领域应用（医疗、视频），不是每个用户都需要
- `sage-benchmark` 是性能测试工具，主要给研究者使用
- 保持默认安装轻量化，用户可按需安装

### Q: 如何升级已安装的 SAGE？

```bash
# 升级到最新版本
pip install --upgrade isage

# 升级到特定版本
pip install isage==1.2.3

# 升级所有子包
pip install --upgrade isage[full]
```

### Q: 如何单独安装某个子包？

```bash
# 只安装 kernel
pip install isage-kernel

# 只安装 tools（会自动安装依赖）
pip install isage-tools

# 只安装 studio
pip install isage-studio
```

### Q: 安装后如何验证？

```bash
# 查看版本
sage --version

# 查看已安装的包
pip list | grep isage

# 运行测试
python -c "from sage.kernel.api import LocalEnvironment; print('SAGE installed successfully!')"
```

---

## 🔧 高级选项

### 从源码安装

```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 安装标准版本
pip install -e packages/sage

# 安装开发版本
pip install -e packages/sage[dev]
```

### 离线安装

```bash
# 1. 在有网络的机器上下载
pip download isage -d ./sage-packages

# 2. 复制到离线机器，安装
pip install --no-index --find-links=./sage-packages isage
```

### 指定镜像源

```bash
# 使用清华镜像
pip install isage -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用阿里云镜像
pip install isage -i https://mirrors.aliyun.com/pypi/simple
```

---

## 📚 相关文档

- [包架构说明](PACKAGE_ARCHITECTURE.md)
- [快速入门](../README.md)
- [开发者指南](DEVELOPER.md)
- [贡献指南](../CONTRIBUTING.md)
