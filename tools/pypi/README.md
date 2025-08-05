# SAGE PyPI 发布工具

🚀 **一键上传SAGE开源包到PyPI的完整工具链**

## 📁 文件结构

```
tools/pypi/
├── README.md                   # 本文件 - 快速入门指南
├── upload_to_pypi.sh          # 🎯 主上传脚本
├── setup_pypi_auth.sh         # 🔐 认证设置助手  
├── setup_team_pypi.sh         # 👥 团队认证设置
├── manage_versions.sh         # 📋 版本管理工具
├── pypi_config.ini           # ⚙️ 配置文件
├── PYPI_RELEASE_GUIDE.md      # 📖 详细使用指南
└── TEAM_PYPI_SETUP.md         # 👨‍💻 团队协作指南
```

## 🎯 支持的包

- **sage-kernel** - 核心处理引擎
- **sage-middleware** - 中间件层  
- **sage-userspace** - 用户空间库
- **sage** - 主包
- **sage-dev-toolkit** - 开发工具包
- **sage-frontend** - Web前端

## ⚡ 快速开始

### 1️⃣ 首次设置（只需一次）

```bash
cd tools/pypi

# 设置PyPI认证
./setup_pypi_auth.sh --interactive
```

### 2️⃣ 一键上传

```bash
# 预览模式（安全，推荐先运行）
./upload_to_pypi.sh --dry-run

# 实际上传所有包
./upload_to_pypi.sh

# 上传特定包
./upload_to_pypi.sh sage-kernel sage-frontend
```

## 🛠️ 主要功能

| 脚本 | 功能 | 使用场景 |
|-----|------|---------|
| `upload_to_pypi.sh` | 🎯 **主上传脚本** | 一键上传包到PyPI |
| `setup_pypi_auth.sh` | 🔐 认证设置 | 首次配置API token |
| `setup_team_pypi.sh` | 👥 团队设置 | 团队成员快速配置 |
| `manage_versions.sh` | 📋 版本管理 | 统一管理包版本号 |

## 🔥 常用命令

### 版本管理
```bash
# 查看所有包版本
./manage_versions.sh show

# 统一递增版本号
./manage_versions.sh bump minor --all

# 设置特定版本
./manage_versions.sh set 1.2.0 --all
```

### PyPI上传
```bash
# 🔍 预览模式 - 查看将要上传什么
./upload_to_pypi.sh --dry-run

# 🧪 测试环境 - 先在TestPyPI测试
./upload_to_pypi.sh --test

# 🚀 正式上传 - 发布到PyPI
./upload_to_pypi.sh

# 📦 上传特定包
./upload_to_pypi.sh sage-kernel

# 🔧 强制重新构建
./upload_to_pypi.sh --force
```

### 团队协作
```bash
# 其他同事快速设置
./setup_team_pypi.sh --shared

# 检查当前配置
./setup_pypi_auth.sh --check
```

## 🚦 发布流程

### 标准发布流程
```bash
# 1. 检查当前状态
./manage_versions.sh show

# 2. 更新版本号
./manage_versions.sh bump minor --all

# 3. 预览上传
./upload_to_pypi.sh --dry-run

# 4. 测试环境验证
./upload_to_pypi.sh --test

# 5. 正式发布
./upload_to_pypi.sh
```

### 紧急补丁发布
```bash
# 快速补丁版本发布
./manage_versions.sh bump patch --all
./upload_to_pypi.sh --dry-run
./upload_to_pypi.sh
```

## 💡 核心特性

- ✅ **一键上传** - 支持批量上传所有开源包
- ✅ **安全预演** - `--dry-run` 模式确保安全
- ✅ **测试环境** - TestPyPI 测试支持
- ✅ **版本管理** - 自动化版本号管理
- ✅ **团队协作** - 简化团队成员设置
- ✅ **错误处理** - 完善的错误检查和恢复
- ✅ **详细日志** - 彩色输出和进度跟踪

## 🔐 认证设置

### 个人使用
```bash
# 交互式设置
./setup_pypi_auth.sh --interactive

# 检查配置
./setup_pypi_auth.sh --check
```

### 团队使用
```bash
# 团队成员使用共享token
./setup_team_pypi.sh --shared

# 或者设置个人token（更安全）
./setup_team_pypi.sh --personal
```

## 📋 检查清单

发布前请确认：

- [ ] ✅ 已设置PyPI认证信息
- [ ] ✅ 版本号已正确更新
- [ ] ✅ 所有包都通过了测试
- [ ] ✅ 已使用 `--dry-run` 预览
- [ ] ✅ 已在TestPyPI测试过
- [ ] ✅ 检查了包的依赖关系

## 🆘 获取帮助

```bash
# 查看脚本帮助
./upload_to_pypi.sh --help
./manage_versions.sh --help
./setup_pypi_auth.sh --help

# 查看详细文档
cat PYPI_RELEASE_GUIDE.md
cat TEAM_PYPI_SETUP.md
```

## 🚨 注意事项

1. **🔐 API Token安全**：不要将token提交到代码库
2. **🧪 先测试**：建议先用 `--test` 在TestPyPI测试
3. **📦 版本唯一**：PyPI上的版本号不可修改
4. **👥 团队协作**：使用 `setup_team_pypi.sh` 简化团队设置

## 📞 支持

- 📖 **详细文档**：`PYPI_RELEASE_GUIDE.md`
- 👥 **团队指南**：`TEAM_PYPI_SETUP.md`  
- 🐛 **问题反馈**：GitHub Issues
- 📧 **联系我们**：intellistream@outlook.com

---

**🎉 现在上传SAGE包到PyPI只需要一个命令！**

```bash
./upload_to_pypi.sh --dry-run  # 先预览
./upload_to_pypi.sh            # 再上传
```
