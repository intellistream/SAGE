# 🚀 SAGE 快速安装指南

## 🎯 三种安装方式，任选其一

### 方式1: 智能脚本 (推荐) 🤖
```bash
# 自动检测版本并安装
python scripts/sage-install.py --dev

# 手动指定开源版
python scripts/sage-install.py --version open-source --dev

# 手动指定商业版 (需要权限)
python scripts/sage-install.py --version commercial --dev
```

### 方式2: 传统pip方式 📦
```bash
# 开发者安装
pip install -r requirements-dev.txt

# 生产环境安装  
pip install -r requirements.txt
```

### 方式3: Makefile 🔧
```bash
# 开源版开发安装
make dev-install

# 商业版开发安装
make commercial-install
```

## 🏢 商业版本协作

### ✅ 解决方案
- **商业代码在git中** - 团队可以正常协作开发
- **智能版本检测** - 脚本自动选择安装版本
- **多仓库策略** - 公共仓库排除商业代码，私有仓库包含全部

### 🤝 团队协作流程
```bash
# 新成员加入 (任何版本)
git clone <repository>
python scripts/sage-install.py --dev

# 开发 (代码立即生效)
vim packages/sage-kernel/src/sage/api/datastream.py
python -c "from sage.api import DataStream; ..."

# 测试和提交
pytest packages/sage-kernel/tests/
git commit -m "feature: new API"
```

## 🔄 版本切换
```bash
# 切换到开源版测试
python scripts/sage-install.py --version open-source --dev

# 切换回商业版
python scripts/sage-install.py --version commercial --dev
```

## 💡 常用命令
```bash
# 查看帮助
python scripts/sage-install.py --help

# 仅生成requirements文件
python scripts/sage-install.py --generate-only --dev

# 验证安装
python -c "import sage; print('SAGE Ready!')"
```

---

**现在无需强制Makefile，团队可以正常协作，灵活选择安装方式！** 🎉
