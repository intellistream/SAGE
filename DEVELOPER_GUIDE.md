# SAGE 开发者快速入门指南

欢迎加入 SAGE 开发团队！本指南将帮助您快速设置开发环境并开始贡献代码。

## 🚀 快速开始

## 选项1: 一键部署 (推荐新手)
```bash
./quickstart.sh
```

## 选项2: 手动部署 (推荐开发者)
```bash
python3 scripts/deployment_setup.py full --dev
```

## 选项3: 分步执行
```bash
python3 scripts/deployment_setup.py init      # 初始化submodules
python3 scripts/deployment_setup.py install   # 安装依赖
python3 scripts/deployment_setup.py build     # 构建项目
python3 scripts/deployment_setup.py test      # 运行测试
```

---

## 🛠️ 脚本工具

### Python部署脚本 (`scripts/deployment_setup.py`)

自动化部署脚本，支持以下命令：

| 命令 | 功能 | 示例 |
|------|------|------|
| `init` | 初始化Git submodules | `python3 scripts/deployment_setup.py init` |
| `install` | 安装Python依赖 | `python3 scripts/deployment_setup.py install --dev` |
| `build` | 构建项目 | `python3 scripts/deployment_setup.py build` |
| `test` | 运行测试 | `python3 scripts/deployment_setup.py test` |
| `status` | 检查项目状态 | `python3 scripts/deployment_setup.py status` |
| `full` | 完整部署 | `python3 scripts/deployment_setup.py full --dev` |

## 📋 支持的命令

### Python部署脚本 (`setup.py`)

| 命令 | 描述 | 示例 |
|------|------|------|
| `init` | 初始化Git submodules | `python3 scripts/deployment_setup.py init` |
| `install` | 安装Python依赖 | `python3 scripts/deployment_setup.py install --dev` |
| `build` | 构建项目 | `python3 scripts/deployment_setup.py build` |
| `test` | 运行测试 | `python3 scripts/deployment_setup.py test` |
| `status` | 检查项目状态 | `python3 scripts/deployment_setup.py status` |
| `full` | 完整部署 | `python3 scripts/deployment_setup.py full --dev` |

### 快速启动脚本 (`quickstart.sh`)

- **快速安装**: 仅核心功能，适合使用者
- **开发者安装**: 包含开发工具和测试环境
- **完整安装**: 包含文档构建和所有功能

## 🏗️ 项目结构

```
SAGE/
├── quickstart.sh              # 🚀 快速启动脚本  
├── scripts/                   # 📂 自动化脚本目录
│   ├── deployment_setup.py   # 🛠️ Python部署脚本
│   ├── cleanup_build_artifacts.sh # 🧹 清理构建产物
│   └── README.md             # � 脚本说明文档
├── docs-public/              # 📚 公开文档 (submodule)
├── packages/                 # 📦 核心包
│   ├── sage/                # 主包
│   ├── sage-kernel/         # 核心框架
│   ├── sage-middleware/     # 中间件服务
│   ├── sage-userspace/      # 用户空间
│   └── sage-tools/          # 工具包
├── tools/                    # 🔧 开发工具
│   └── sync_docs.sh         # 文档同步脚本
└── docs/                      # 📖 内部文档
    └── DOCUMENTATION_GUIDE.md
```

## 🔧 开发环境要求

### 必需依赖
- **Python 3.8+**
- **Git 2.0+** 
- **pip 21.0+**

### 推荐依赖
- **虚拟环境**: `venv` 或 `conda`
- **代码编辑器**: VS Code, PyCharm, Vim
- **终端**: 支持颜色输出的现代终端

### 检查环境

```bash
# 检查Python版本
python3 --version  # 应该 >= 3.8

# 检查Git版本  
git --version      # 应该 >= 2.0

# 检查pip版本
pip --version      # 应该 >= 21.0

# 使用脚本检查完整状态
python3 scripts/deployment_setup.py status
```

## 📦 安装包说明

部署脚本会自动安装以下包：

### 核心SAGE包
- `sage` - 主包
- `intsage-kernel` - 流处理内核
- `intsage-middleware` - 中间件服务  
- `intsage-userspace` - 用户空间API

### 开发工具（--dev 模式）
- `pytest` - 测试框架
- `black` - 代码格式化
- `flake8` - 代码检查
- `mypy` - 类型检查
- `pre-commit` - Git hooks

### 文档工具
- `mkdocs` - 文档生成
- `mkdocs-material` - 文档主题

## 🌐 文档系统

### 本地文档服务

```bash
# 启动本地文档服务器
cd docs-public
mkdocs serve

# 访问 http://127.0.0.1:8000
```

### 文档同步

```bash
# 同步内部文档到公开仓库
./tools/sync_docs.sh

# 手动同步
rsync -av packages/sage-kernel/docs/ docs-public/docs_src/kernel/
```

## 🧪 开发工作流

### 1. 代码开发

```bash
# 创建功能分支
git checkout -b feature/my-feature

# 安装为开发模式
pip install -e packages/sage-kernel

# 开发和测试
python3 scripts/deployment_setup.py test
```

### 2. 代码质量

```bash
# 代码格式化
black packages/sage-kernel/src

# 代码检查
flake8 packages/sage-kernel/src

# 类型检查
mypy packages/sage-kernel/src
```

### 3. 文档更新

```bash
# 更新文档
vim packages/sage-kernel/docs/api/new-feature.md

# 同步到公开仓库
./tools/sync_docs.sh
```

### 4. 测试验证

```bash
# 运行单元测试
python3 scripts/deployment_setup.py test

# 运行特定测试
pytest packages/sage-kernel/tests/test_feature.py -v

# 测试文档构建
cd docs-public && mkdocs build
```

## 🚨 常见问题

### Q: Git submodule 更新失败
```bash
# 重新初始化submodule
git submodule deinit -f docs-public
rm -rf .git/modules/docs-public
python3 scripts/deployment_setup.py init
```

### Q: 依赖安装失败
```bash
# 升级pip
python3 -m pip install --upgrade pip

# 清理缓存重装
pip cache purge
python3 scripts/deployment_setup.py install --dev
```

### Q: 文档构建失败
```bash
# 检查mkdocs配置
cd docs-public
mkdocs build --verbose

# 重装文档依赖
pip install -r requirements.txt
```

### Q: 包导入失败
```bash
# 检查安装状态
python3 scripts/deployment_setup.py status

# 重新安装包
pip install -e packages/sage-kernel
```

## 🎯 贡献指南

### 代码贡献

1. **Fork项目** 并创建功能分支
2. **使用脚本设置环境**: `./quickstart.sh`
3. **开发新功能** 并添加测试
4. **更新文档** 说明新功能
5. **运行测试** 确保通过: `python3 scripts/deployment_setup.py test`
6. **提交PR** 并描述更改

### 文档贡献

1. **内部文档**: 在 `packages/*/docs/` 目录编写
2. **同步公开**: 使用 `./tools/sync_docs.sh`
3. **格式规范**: 遵循 Markdown 标准
4. **链接检查**: 确保所有链接有效

### 发布流程

1. **更新版本号** 在 `pyproject.toml`
2. **更新CHANGELOG** 记录重要更改  
3. **构建和测试** 完整功能
4. **同步文档** 到公开仓库
5. **创建Release** 并打标签

## 📞 获取帮助

- **项目文档**: https://intellistream.github.io/SAGE-Pub/
- **GitHub Issues**: https://github.com/intellistream/SAGE/issues  
- **内部文档**: `docs/DOCUMENTATION_GUIDE.md`
- **API文档**: `packages/sage-kernel/docs/api/`

## 🎉 欢迎加入！

感谢您选择贡献 SAGE 项目！我们的自动化脚本让您可以专注于代码和创新，而不是复杂的环境配置。

Happy Coding! 🚀
