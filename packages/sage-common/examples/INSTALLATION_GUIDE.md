# SAGE Tutorials - Installation Guide

## 📚 About Tutorials

SAGE Tutorials 是完整的学习资源集合，包含：

- 分层教程（L1-L5）
- 完整的示例代码
- 配置文件和测试数据
- 详细的注释和说明

**⚠️ 重要提示**: Tutorials **不包含在 PyPI 包中**，需要从源码获取。

______________________________________________________________________

## 🎯 如何获取 Tutorials

### 方式 1: 克隆完整仓库（推荐）

```bash
# 1. 克隆 SAGE 仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 安装开发环境
./quickstart.sh --dev --yes

# 3. 运行 tutorials
python tutorials/L1-common/hello_world.py
python tutorials/L1-common/unified_inference_client_example.py
```

**适用场景**:

- ✅ 学习 SAGE 完整功能
- ✅ 本地开发和测试
- ✅ 需要修改示例代码

### 方式 2: 仅下载 Tutorials 目录

```bash
# 使用 sparse-checkout 只下载 tutorials
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/intellistream/SAGE.git
cd SAGE
git sparse-checkout set tutorials

# 安装 SAGE（从 PyPI）
pip install isage[standard]

# 运行 tutorials
python tutorials/L1-common/hello_world.py
```

**适用场景**:

- ✅ 只需要教程，不需要修改源码
- ✅ 快速下载（只下载 tutorials 目录）
- ✅ 使用 PyPI 版本的 SAGE

### 方式 3: 在线浏览（无需安装）

访问在线文档查看所有示例代码：

- **Tutorials 文档**: https://intellistream.github.io/SAGE-Pub/tutorials/
- **GitHub 浏览**: https://github.com/intellistream/SAGE/tree/main-dev/tutorials

**适用场景**:

- ✅ 快速查阅代码
- ✅ 学习 API 用法
- ✅ 复制粘贴代码片段

______________________________________________________________________

## 💡 为什么 Tutorials 不打包到 PyPI？

参考:
[EXAMPLES_TESTING_PYPI_STRATEGY.md](../docs-public/docs_src/dev-notes/cross-layer/architecture/EXAMPLES_TESTING_PYPI_STRATEGY.md)

### ❌ 打包的问题

1. **包体积**：Tutorials 包含大量文件（~500+ 文件），会显著增加 PyPI 包大小
1. **更新频率**：教程经常更新，会导致 SAGE 包频繁发版
1. **测试数据**：包含大量测试数据、配置文件，不适合分发
1. **依赖复杂**：不同教程需要不同依赖，难以管理

### ✅ 当前方案的优势

1. **灵活性**：可以随时更新教程，无需发版
1. **完整性**：可以包含大文件、数据集
1. **清晰性**：PyPI 包保持精简，仅包含核心代码
1. **可访问性**：通过 Git 和在线文档都能访问

______________________________________________________________________

## 📦 PyPI 包中的示例

虽然 Tutorials 不在 PyPI 包中，但各个包都包含轻量级示例：

### isage-kernel

```bash
pip install isage-kernel
python -m sage.kernel.examples.simple_streaming
```

### isage-libs

```bash
pip install isage-libs
python -m sage.libs.examples.rag_basic
```

### Applications (sage-examples)

应用示例已迁移到独立仓库：

```bash
# 克隆 sage-examples 仓库
git clone https://github.com/intellistream/sage-examples.git
cd sage-examples

# 安装依赖
pip install -r requirements.txt

# 运行应用示例
python examples/run_video_intelligence.py
python examples/run_medical_diagnosis.py
```

查看更多: https://github.com/intellistream/sage-examples

这些示例是 **可运行的代码片段**，专门设计用于 PyPI 安装的用户。

______________________________________________________________________

## 🎓 学习路径

### 1. PyPI 用户（快速开始）

```bash
# 安装 SAGE
pip install isage[standard]

# 运行包内示例
python -m sage.libs.examples.hello_world

# 查看在线文档
浏览器打开: https://intellistream.github.io/SAGE-Pub/
```

### 2. 开发者（完整学习）

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 开发环境安装
./quickstart.sh --dev --yes

# 运行 Tutorials
python tutorials/L1-common/hello_world.py
python tutorials/L3-libs/rag/simple_rag.py
# 完整应用示例见 sage-examples 仓库
```

### 3. 研究人员（深度定制）

```bash
# 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 安装可编辑模式
pip install -e packages/sage-kernel
pip install -e packages/sage-libs
pip install -e packages/sage-middleware

# 修改和运行教程
# 代码更改会立即生效
```

______________________________________________________________________

## 🔧 Tutorials 依赖管理

### 通用依赖

```bash
# 基础教程（L1-L3）
pip install isage[standard]

# 中间件教程（L4）
pip install isage-middleware[all]

# 应用教程（L5）
pip install isage-apps[all]
```

### 特定教程依赖

某些教程需要额外依赖：

```bash
# RAG 教程
pip install faiss-cpu sentence-transformers

# Agent 教程
pip install langchain langchain-community

# 视频教程
pip install opencv-python-headless

# 医疗教程
pip install pydicom nibabel
```

详见各教程目录下的 `requirements.txt`。

______________________________________________________________________

## ❓ 常见问题

### Q1: 为什么 `import tutorials` 不工作？

A: Tutorials 不是 Python 包，不能被 import。它们是独立的脚本文件，需要直接运行：

```bash
# ✅ 正确
python tutorials/L1-common/hello_world.py

# ❌ 错误
python -c "import tutorials"
```

### Q2: 我只需要某几个教程，如何下载？

A: 使用 sparse-checkout（见上文方式 2），或直接从 GitHub 下载单个文件：

```bash
# 下载单个文件
wget https://raw.githubusercontent.com/intellistream/SAGE/main-dev/tutorials/L1-common/hello_world.py
python hello_world.py
```

### Q3: Tutorials 和 Examples 有什么区别？

A:

- **Tutorials** (`tutorials/`): 完整的学习资源，按层级组织，包含数据和配置
- **Examples** (`packages/*/examples/`): 轻量级代码片段，打包到 PyPI，专注单一功能

两者互补，根据需求选择。

### Q4: 如何贡献新的 Tutorial？

A:

```bash
# 1. Fork 并克隆仓库
git clone https://github.com/YOUR_USERNAME/SAGE.git

# 2. 创建分支
git checkout -b tutorial/my-new-tutorial

# 3. 添加 tutorial
# 放在合适的层级目录（L1-L5）

# 4. 提交 PR
git add tutorials/L3-libs/my_tutorial.py
git commit -m "docs: add tutorial for XYZ feature"
git push origin tutorial/my-new-tutorial
```

______________________________________________________________________

## 📖 相关资源

- **在线文档**: https://intellistream.github.io/SAGE-Pub/
- **GitHub 仓库**: https://github.com/intellistream/SAGE
- **PyPI 页面**: https://pypi.org/project/isage/
- **问题反馈**: https://github.com/intellistream/SAGE/issues

______________________________________________________________________

## 📧 获取帮助

- **Email**: shuhao_zhang@hust.edu.cn
- **GitHub Issues**: https://github.com/intellistream/SAGE/issues
- **文档**: https://intellistream.github.io/SAGE-Pub/

______________________________________________________________________

**Happy Learning with SAGE! 🚀**
