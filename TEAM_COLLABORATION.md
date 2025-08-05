# 🤝 SAGE 团队协作指南

## 🎯 重新设计的协作模式

### 问题解决方案

❌ **之前的问题：**
- 商业代码被gitignore，团队无法协作
- 强制要求Makefile，不够灵活

✅ **新的解决方案：**
- 商业代码正常提交到git，通过智能脚本控制安装
- 支持多种安装方式，不强制Makefile

## 📁 代码组织方式

```
/home/shuhao/SAGE/
├── packages/
│   ├── sage-kernel/           # 开源核心
│   ├── sage-middleware/       # 开源中间件
│   ├── sage-userspace/        # 开源用户空间
│   ├── sage-tools/            # 开源工具
│   └── commercial/            # 🏢 商业版 (在git中)
│       ├── sage-kernel/       # 增强版内核
│       ├── sage-middleware/   # 企业级中间件
│       └── sage-userspace/    # 企业用户空间
├── sage-config.yml            # 配置文件
└── scripts/sage-install.py    # 智能安装脚本
```

## 🚀 多种安装方式

### 方式1: 智能脚本 (推荐)
```bash
# 自动检测并安装 (推荐)
python scripts/sage-install.py --dev

# 强制指定开源版
python scripts/sage-install.py --version open-source --dev

# 强制指定商业版
python scripts/sage-install.py --version commercial --dev

# 仅生成requirements文件
python scripts/sage-install.py --generate-only --dev
```

### 方式2: 传统pip方式
```bash
# 1. 生成requirements文件
python scripts/sage-install.py --generate-only --dev

# 2. 使用pip安装
pip install -r requirements-open-source-dev.txt
# 或
pip install -r requirements-commercial-dev.txt
```

### 方式3: Makefile (可选)
```bash
make dev-install          # 开源版
make commercial-install   # 商业版
```

## 👥 团队协作流程

### 🌍 开源团队成员
```bash
# 1. 克隆代码
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 自动安装开源版 (脚本会自动检测)
python scripts/sage-install.py --dev

# 3. 开始开发
# 商业代码存在但不会被安装
```

### 🏢 商业团队成员  
```bash
# 1. 克隆完整代码 (包含商业版)
git clone https://internal-git.company.com/sage.git
cd SAGE

# 2. 自动安装商业版 (脚本会自动检测commercial目录)
python scripts/sage-install.py --dev

# 3. 开始开发
# 所有功能都可用
```

## 🔀 版本控制策略

### Git仓库设置
```bash
# 公共开源仓库 (GitHub)
https://github.com/intellistream/SAGE.git
├── packages/sage-*        # ✅ 包含
├── packages/commercial/   # ❌ 不包含 (通过.gitignore排除)
└── scripts/sage-install.py # ✅ 包含

# 私有企业仓库
https://internal-git.company.com/sage.git  
├── packages/sage-*        # ✅ 包含
├── packages/commercial/   # ✅ 包含
└── scripts/sage-install.py # ✅ 包含
```

### 分离策略
```bash
# 公共仓库的.gitignore
packages/commercial/
requirements-commercial*.txt

# 私有仓库的.gitignore  
# (不排除commercial目录)
```

## 🛠️ 开发工作流

### 日常开发
```bash
# 1. 修改代码 (任何packages/下的代码)
vim packages/sage-kernel/src/sage/api/datastream.py

# 2. 代码立即生效 (editable模式)
python -c "from sage.api import DataStream; ..."

# 3. 测试
pytest packages/sage-kernel/tests/

# 4. 提交
git add . && git commit -m "feature: add new API"
```

### 新成员加入
```bash
# 1. 克隆代码
git clone <repository-url>

# 2. 一键安装 (自动检测版本)
python scripts/sage-install.py --dev

# 3. 验证安装
python -c "import sage; print('Ready!')"
```

## 🎯 优势

1. **🤝 团队协作友好** - 商业代码正常提交，团队可以协作开发
2. **🔄 灵活安装** - 支持脚本、pip、Makefile多种方式
3. **🤖 智能检测** - 自动检测环境，选择合适版本
4. **🔒 发布安全** - 公共仓库自动排除商业代码
5. **📦 统一体验** - 开发者无需关心版本差异

## 💡 常见场景

```bash
# 新员工入职
python scripts/sage-install.py --dev

# 切换到开源版本测试
python scripts/sage-install.py --version open-source --dev

# 生成生产环境requirements
python scripts/sage-install.py --version open-source --generate-only

# CI/CD使用
python scripts/sage-install.py --version open-source
```

---

**现在团队可以正常协作开发，同时保持灵活的安装方式！** 🎉
