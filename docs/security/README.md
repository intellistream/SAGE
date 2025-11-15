# SAGE 安全性改进 (Security Enhancements)

🔐 SAGE 0.1.6+ 版本引入了全面的安全性改进，包括依赖验证、权限管理和离线安装支持。

## 🎯 快速开始

### 最安全的安装方式

```bash
# 1. 创建虚拟环境
python3 -m venv sage-env
source sage-env/bin/activate

# 2. 执行深度安全验证
./quickstart.sh --verify-deps --standard

# 3. 验证安装
sage doctor
```

## 📚 核心文档

### 必读文档

1. **[权限管理指南](./PERMISSION_MANAGEMENT.md)** 🔐

   - 权限需求分类
   - 避免不必要的 sudo 使用
   - 各种环境的解决方案
   - 权限问题故障排除

1. **[安全安装指南](./SECURE_INSTALLATION_GUIDE.md)** 🔒

   - Checksum 验证方法
   - 漏洞扫描工具集成
   - --verify-deps 深度验证
   - CI/CD 集成示例

1. **[离线安装指南](./OFFLINE_INSTALLATION.md)** 🌐

   - 企业网络部署
   - Air-Gapped 系统安装
   - 离线包准备和管理
   - 受限环境解决方案

1. **[安全性改进总结](./SECURITY_IMPROVEMENTS.md)** 📋

   - 完整的改进清单
   - 实施统计
   - 功能对比
   - 后续优化方向

## 🚀 常见场景

### 场景 1: 标准安装（推荐）

适用于：大多数用户

```bash
python3 -m venv sage-env
source sage-env/bin/activate
./quickstart.sh --verify-deps --standard --yes
```

**特点**：

- ✅ 自动验证依赖
- ✅ 检测安全漏洞
- ✅ 最小化权限使用
- ✅ 完整的错误报告

### 场景 2: 企业网络部署

适用于：有代理服务器的企业环境

```bash
# 配置代理
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=https://proxy.company.com:8080

# 安装
./quickstart.sh --verify-deps --standard --yes
```

**参考**：[企业网络安装](./OFFLINE_INSTALLATION.md#%E4%BC%81%E4%B8%9A%E7%BD%91%E7%BB%9C%E5%AE%89%E8%A3%85)

### 场景 3: Air-Gapped 系统

适用于：完全隔离的离线系统

**准备阶段**（有网络）：

```bash
pip download -d ~/packages isage[standard]
tar -czf packages.tar.gz packages/
```

**部署阶段**（离线）：

```bash
tar -xzf packages.tar.gz
pip install isage[standard] --no-index --find-links ./packages
```

**参考**：[Air-Gapped 安装](./OFFLINE_INSTALLATION.md#air-gapped-%E7%B3%BB%E7%BB%9F%E5%AE%89%E8%A3%85)

### 场景 4: CI/CD 流程

适用于：自动化测试和部署

```bash
# 严格验证模式（有任何问题则失败）
./quickstart.sh --verify-deps-strict --dev --yes

# 生成安全报告
ls -la security_audit_*.json
```

**参考**：[CI/CD 集成](./SECURE_INSTALLATION_GUIDE.md#cicd-%E9%9B%86%E6%88%90%E7%A4%BA%E4%BE%8B)

## 🔑 关键功能

### 1. Checksum 验证 ✅

验证下载的包是否被篡改

```bash
verify_package_checksum /path/to/package.whl "expected_sha256"
```

### 2. 漏洞扫描 🛡️

检测已知的安全漏洞

```bash
# 使用 pip-audit（推荐）
pip-audit -r requirements.txt

# 或使用 safety
safety check -r requirements.txt
```

### 3. 深度依赖验证 🔍

综合验证依赖的所有方面

```bash
# 标准验证
./quickstart.sh --verify-deps --standard

# 严格验证（CI/CD）
./quickstart.sh --verify-deps-strict --dev
```

### 4. 权限管理 👤

最小权限原则，避免不必要的 sudo

- **用户权限**：虚拟环境、Python 包
- **Sudo 权限**：系统依赖（仅一次）
- **最小化**：自动检测权限需求

## 📊 验证流程

```
./quickstart.sh --verify-deps
    ↓
├─ 1. pip 依赖检查 (pip check)
├─ 2. 漏洞扫描 (pip-audit + safety)
├─ 3. 版本兼容性检查
└─ 4. 生成报告
    ↓
✅ 所有检查通过
❌ 发现问题（继续 | 中止）
```

## 🆘 故障排除

### 问题：验证失败，有安全漏洞

**解决方案**：

1. 查看报告文件：`cat security_audit_pip_audit.json`
1. 升级受影响的包：`pip install --upgrade <package>`
1. 重新运行验证：`./quickstart.sh --verify-deps`

**详情**：[处理发现的漏洞](./SECURE_INSTALLATION_GUIDE.md#%E5%A4%84%E7%90%86%E5%8F%91%E7%8E%B0%E7%9A%84%E6%BC%8F%E6%B4%9E)

### 问题：企业网络中 SSL 证书错误

**解决方案**：

```bash
# 方式 1：信任企业镜像
pip install --trusted-host your-mirror.com isage

# 方式 2：添加 CA 证书
pip install --cert /path/to/ca.crt isage
```

**详情**：[SSL 证书问题](./OFFLINE_INSTALLATION.md#q3-%E4%BC%81%E4%B8%9A%E7%BD%91%E7%BB%9C%E4%B8%AD-ssl-%E8%AF%81%E4%B9%A6%E9%AA%8C%E8%AF%81%E5%A4%B1%E8%B4%A5%E6%80%8E%E4%B9%88%E5%8A%9E)

### 问题：权限不足

**解决方案**：

1. 使用虚拟环境（推荐）
1. 让管理员预先安装系统依赖
1. 使用 Conda（管理所有依赖）

**详情**：[权限故障排除](./PERMISSION_MANAGEMENT.md#%E6%95%85%E9%9A%9C%E6%8E%92%E9%99%A4)

## 📖 完整文档列表

### 主要指南

- ✅ [权限管理指南](./PERMISSION_MANAGEMENT.md)
- ✅ [安全安装指南](./SECURE_INSTALLATION_GUIDE.md)
- ✅ [离线安装指南](./OFFLINE_INSTALLATION.md)
- ✅ [安全性改进总结](./SECURITY_IMPROVEMENTS.md)

### 相关文档

- 📖 [SAGE 主安装指南](../../docs-public/docs_src/getting-started/installation.md)
- 📖 [SAGE 故障排除](../../docs/TROUBLESHOOTING.md)
- 📖 [SAGE 开发指南](../../DEVELOPER.md)

## 🔐 安全最佳实践

### ✅ 推荐做法

- 使用虚拟环境（venv/conda）
- 启用 --verify-deps 验证
- 定期更新依赖
- 在 CI/CD 中使用严格验证
- 保留验证报告记录

### ❌ 应避免的做法

- 使用 `sudo pip install`
- 跳过安全验证
- 混合在线和离线包
- 使用过期的离线包
- 忽视漏洞报告

## 📞 获取帮助

### 问题和反馈

- 🐛 [提交 Issue](https://github.com/intellistream/SAGE/issues)
- 💬 [社区讨论](https://github.com/intellistream/SAGE/discussions)

### 安全报告

- 🔐 邮件：security@intellistream.com
- 📝 提供详细的复现步骤

### 社区支持

- 📚 [SAGE 文档](https://sage.intellistream.ai/)
- 🤝 [贡献指南](../../CONTRIBUTING.md)

## 📋 版本信息

| 版本   | 发布日期   | 改进                  |
| ------ | ---------- | --------------------- |
| 0.1.6+ | 2025-11-15 | 首次安全性改进        |
| -      | -          | ✅ Checksum 验证      |
| -      | -          | ✅ 漏洞扫描集成       |
| -      | -          | ✅ --verify-deps 选项 |
| -      | -          | ✅ 权限管理文档       |
| -      | -          | ✅ 离线安装支持       |

______________________________________________________________________

## 🚀 快速命令参考

```bash
# 基础验证安装
./quickstart.sh --verify-deps --standard

# 严格 CI/CD 安装
./quickstart.sh --verify-deps-strict --dev --yes

# 仅验证（不安装）
./quickstart.sh --verify-deps

# 查看所有选项
./quickstart.sh --help

# 诊断环境问题
./quickstart.sh --doctor

# 诊断并自动修复
./quickstart.sh --doctor-fix
```

______________________________________________________________________

**最后更新**：2025-11-15\
**维护者**：SAGE Security Team\
**许可证**：MIT

______________________________________________________________________

**开始安全使用 SAGE** 🎉

```bash
python3 -m venv sage-env && source sage-env/bin/activate
./quickstart.sh --verify-deps --standard
```
