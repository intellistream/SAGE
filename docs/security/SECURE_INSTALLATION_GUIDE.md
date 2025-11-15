# SAGE 安全安装指南 (Secure Installation Guide)

本文档提供了安全安装 SAGE 的最佳实践，包括包验证、漏洞扫描和深度依赖检查。

## 📋 目录

- [概述](#%E6%A6%82%E8%BF%B0)
- [快速开始](#%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
- [包完整性验证](#%E5%8C%85%E5%AE%8C%E6%95%B4%E6%80%A7%E9%AA%8C%E8%AF%81)
- [安全漏洞扫描](#%E5%AE%89%E5%85%A8%E6%BC%8F%E6%B4%9E%E6%89%AB%E6%8F%8F)
- [深度依赖验证](#%E6%B7%B1%E5%BA%A6%E4%BE%9D%E8%B5%96%E9%AA%8C%E8%AF%81)
- [安全安装工作流](#%E5%AE%89%E5%85%A8%E5%AE%89%E8%A3%85%E5%B7%A5%E4%BD%9C%E6%B5%81)
- [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)

______________________________________________________________________

## 概述

### 安全关注点

SAGE 的安全安装涉及以下几个方面：

1. **包完整性** - 确保下载的包未被篡改
1. **漏洞检查** - 检测依赖中的已知安全漏洞
1. **依赖验证** - 验证所有依赖的兼容性和完整性
1. **权限管理** - 使用最小权限原则

### 新增功能

从 SAGE 0.1.6+ 版本起，我们提供了以下安全增强功能：

- ✅ **Checksum 验证** - 验证下载包的 SHA256
- ✅ **Pip-Audit 集成** - 检查已知的安全漏洞
- ✅ **Safety 检查** - 额外的漏洞扫描工具
- ✅ **`--verify-deps`** - 深度依赖验证选项

______________________________________________________________________

## 快速开始

### 基础安全安装

```bash
# 1. 创建虚拟环境
python3 -m venv sage-env
source sage-env/bin/activate

# 2. 升级 pip、setuptools 和 wheel
pip install --upgrade pip setuptools wheel

# 3. 进行深度验证后安装
./quickstart.sh --verify-deps --standard
```

### 完整安全流程

```bash
# 1. 系统依赖检查和安装
./quickstart.sh --check-system

# 2. 深度依赖验证
./quickstart.sh --verify-deps

# 3. 安全安装
./quickstart.sh --verify-deps --standard --yes
```

______________________________________________________________________

## 包完整性验证

### 什么是 Checksum 验证？

Checksum（校验和）是文件的数字指纹。通过比对官方 checksum 和下载文件的 checksum，可以验证文件在传输过程中未被篡改。

### SHA256 验证流程

#### 步骤 1: 获取官方 checksum

从 PyPI 官方页面获取文件的 SHA256：

```bash
# 方式 1: 访问 PyPI 网站
# https://pypi.org/project/isage/

# 方式 2: 使用 PyPI JSON API
curl -s https://pypi.org/pypi/isage/json | jq '.releases[] | .[] | "\(.filename) \(.digests.sha256)"'
```

**示例输出**：

```
isage-0.1.6-py3-none-any.whl sha256:1a2b3c4d5e6f7g8h9i0j...
```

#### 步骤 2: 验证下载的文件

```bash
# 使用 sha256sum 验证
sha256sum isage-0.1.6-py3-none-any.whl

# 或使用 shasum（macOS）
shasum -a 256 isage-0.1.6-py3-none-any.whl

# 比对结果应该匹配官方 checksum
```

#### 步骤 3: 手动验证脚本

我们提供了自动验证脚本：

```bash
# 初始化验证模块
source tools/install/examination_tools/dependency_verification.sh

# 验证单个文件
verify_package_checksum /path/to/isage-0.1.6.whl "expected_sha256_hash"

# 示例
verify_package_checksum \
  /tmp/isage-0.1.6-py3-none-any.whl \
  "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t"
```

### pip 的内置验证

现代 pip 版本会自动验证 PyPI 包的 checksum：

```bash
# pip 会自动验证（建议升级 pip）
pip install --upgrade pip
pip install isage

# 详细输出
pip install -v isage
```

### 离线 Checksum 验证

如果无法联网，可以使用预下载的 checksum 文件：

```bash
# 从官方仓库下载 checksum 文件
wget https://github.com/intellistream/SAGE/releases/download/v0.1.6/SHA256SUMS

# 验证
sha256sum -c SHA256SUMS

# 输出应该显示所有文件 OK
```

______________________________________________________________________

## 安全漏洞扫描

### 什么是漏洞扫描？

漏洞扫描工具会检查已安装的依赖是否存在已知的安全漏洞。常用工具包括：

- **pip-audit** - PyPA 官方推荐的审计工具（推荐）
- **safety** - 独立的漏洞检查工具
- **Bandit** - 源代码安全分析工具

### 快速扫描

#### 方式 1: 使用安装脚本

```bash
# 在安装过程中进行漏洞扫描
./quickstart.sh --verify-deps

# 输出示例
# 1️⃣  验证 pip 包依赖...
# ✓ 所有包依赖验证通过
# 2️⃣  运行安全漏洞扫描...
# ✓ 漏洞扫描完成: security_audit_pip_audit.json
```

#### 方式 2: 手动扫描

```bash
# 初始化验证模块
source tools/install/examination_tools/dependency_verification.sh

# 扫描 requirements.txt
check_vulnerabilities requirements.txt

# 指定扫描工具
check_vulnerabilities requirements.txt . pip-audit
check_vulnerabilities requirements.txt . safety
check_vulnerabilities requirements.txt . all  # 两个工具都运行
```

### Pip-Audit 详细使用

```bash
# 1. 安装 pip-audit
pip install pip-audit

# 2. 扫描当前环境
pip-audit

# 3. 扫描特定 requirements 文件
pip-audit -r requirements.txt

# 4. 保存详细报告
pip-audit -r requirements.txt -o json > audit_report.json
pip-audit -r requirements.txt -o markdown > audit_report.md

# 5. 严格模式（有漏洞则失败）
pip-audit -r requirements.txt --strict
```

**输出示例**：

```
Vulnerability Summary
┌─────────────────────┬──────────┬──────────┬──────────────────────────────┐
│ Package             │ Version  │ ID       │ Advisory Title               │
├─────────────────────┼──────────┼──────────┼──────────────────────────────┤
│ requests            │ 2.27.0   │ GHSA-xxx │ Incorrect handling of ...     │
│ urllib3             │ 1.26.0   │ GHSA-yyy │ HTTP Request Smuggling ...   │
└─────────────────────┴──────────┴──────────┴──────────────────────────────┘
```

### Safety 详细使用

```bash
# 1. 安装 safety
pip install safety

# 2. 扫描当前环境
safety check

# 3. 扫描特定 requirements 文件
safety check -r requirements.txt

# 4. 保存 JSON 报告
safety check -r requirements.txt --json > safety_report.json

# 5. 检查特定版本
safety check --key YOUR_API_KEY
```

### 处理发现的漏洞

如果扫描发现漏洞，有以下几个选项：

#### 选项 1: 升级受影响的包

```bash
# 查看漏洞详情
pip-audit -r requirements.txt

# 升级到修复版本
pip install --upgrade requests urllib3

# 重新扫描
pip-audit -r requirements.txt
```

#### 选项 2: 根据漏洞严重程度决定

```bash
# 低危 (LOW) - 可以延迟修复
# 中危 (MEDIUM) - 应在下个版本修复
# 高危 (HIGH) - 立即修复
# 严重 (CRITICAL) - 停止使用该版本
```

#### 选项 3: 使用不同的依赖版本

```bash
# 创建兼容版本的 requirements
pip index versions numpy
# 选择安全的版本

# 更新 requirements.txt
echo "numpy==1.21.6" > requirements.txt

# 重新安装和扫描
pip install -r requirements.txt
pip-audit -r requirements.txt
```

______________________________________________________________________

## 深度依赖验证

### --verify-deps 选项

`--verify-deps` 选项执行全面的依赖检查，包括：

1. ✅ Pip 依赖验证 (`pip check`)
1. ✅ 安全漏洞扫描 (pip-audit + safety)
1. ✅ 包版本兼容性检查
1. ✅ 生成详细报告

### 使用方法

#### 基础验证

```bash
# 验证当前环境
./quickstart.sh --verify-deps

# 输出
# === 深度依赖验证 (--verify-deps) ===
# 1️⃣  验证 pip 包依赖...
# ✓ 所有包依赖验证通过
# 2️⃣  运行安全漏洞扫描...
# ✓ 漏洞扫描完成
# 3️⃣  检查包版本兼容性...
# ✓ 所有包都已正确安装
# ✅ 深度验证通过
```

#### 严格模式

```bash
# 严格模式：有任何问题则失败
./quickstart.sh --verify-deps --strict

# 用于 CI/CD 管道
# 如果验证失败，退出码非零
```

#### 指定安装模式

```bash
# 先验证，再以开发模式安装
./quickstart.sh --verify-deps --dev

# 先验证，再以标准模式安装
./quickstart.sh --verify-deps --standard --yes
```

### 验证报告

验证完成后，会生成以下报告文件：

```
security_audit_pip_audit.json     # pip-audit 报告
security_audit_safety.json         # safety 报告
sage_verification_report.txt       # 综合验证报告
```

### 手动深度验证

```bash
# 初始化验证模块
source tools/install/examination_tools/dependency_verification.sh

# 对 requirements.txt 进行深度验证
perform_deep_verification requirements.txt

# 输出详细报告（严格模式）
perform_deep_verification requirements.txt . true

# 自定义输出目录
perform_deep_verification requirements.txt ./reports
```

### 验证输出解释

```
1️⃣  验证 pip 包依赖...
✓ 所有包依赖验证通过

# 含义：pip check 成功，无依赖冲突
# 如果失败：显示冲突的具体包和版本
```

```
2️⃣  运行安全漏洞扫描...
✓ 漏洞扫描完成: security_audit_pip_audit.json

# 含义：未发现漏洞
# 如果有漏洞：显示受影响的包和 CVE 编号
```

```
3️⃣  检查包版本兼容性...
✓ 所有包都已正确安装

# 含义：所有 requirements 中的包都已安装
# 如果有缺失：列出未安装的包
```

______________________________________________________________________

## 安全安装工作流

### 推荐的完整工作流

```bash
# ========================================
# 步骤 1: 环境准备
# ========================================

# 检查 Python 版本
python3 --version  # 需要 3.10+

# 创建虚拟环境
python3 -m venv sage-secure-env
source sage-secure-env/bin/activate

# 升级核心工具
pip install --upgrade pip setuptools wheel

# ========================================
# 步骤 2: 系统检查和依赖安装
# ========================================

# 检查系统是否满足要求
cd /path/to/SAGE
./quickstart.sh --check-system

# 安装系统依赖（如需 sudo）
./quickstart.sh --install-system-deps

# ========================================
# 步骤 3: 深度安全验证
# ========================================

# 运行完整的验证（包括漏洞扫描）
./quickstart.sh --verify-deps --strict

# 检查报告
cat security_audit_pip_audit.json
cat security_audit_safety.json

# ========================================
# 步骤 4: 安全安装
# ========================================

# 以标准模式安装
./quickstart.sh --verify-deps --standard --yes

# 或以开发模式安装（包含开发工具）
./quickstart.sh --verify-deps --dev --yes

# ========================================
# 步骤 5: 验证安装
# ========================================

# 检查系统状态
sage doctor

# 运行 hello world 示例
python3 docs-public/hello_world.py

# 最终验证
python3 -c "import sage; print(f'SAGE {sage.__version__} installed successfully')"
```

### CI/CD 集成示例

#### GitHub Actions

```yaml
name: Secure SAGE Installation

on: [push, pull_request]

jobs:
  secure-install:
    runs-on: ubuntu-22.04

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Create virtual environment
        run: |
          python3 -m venv sage-env
          source sage-env/bin/activate
          pip install --upgrade pip setuptools wheel

      - name: System dependency check
        run: |
          source sage-env/bin/activate
          sudo apt-get update
          sudo apt-get install -y build-essential cmake libblas-dev liblapack-dev

      - name: Deep security verification
        run: |
          source sage-env/bin/activate
          ./quickstart.sh --verify-deps --strict

      - name: Secure installation
        run: |
          source sage-env/bin/activate
          ./quickstart.sh --verify-deps --standard --yes

      - name: Verify installation
        run: |
          source sage-env/bin/activate
          sage doctor
          python3 -c "import sage; assert sage.__version__"

      - name: Upload security reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: |
            security_audit_*.json
            sage_verification_report.txt
```

#### GitLab CI

```yaml
secure-install:
  stage: build
  image: ubuntu:22.04

  before_script:
    - apt-get update
    - apt-get install -y build-essential cmake python3-venv python3-dev libblas-dev liblapack-dev

  script:
    - python3 -m venv sage-env
    - source sage-env/bin/activate
    - pip install --upgrade pip setuptools wheel
    - ./quickstart.sh --verify-deps --strict
    - ./quickstart.sh --verify-deps --standard --yes
    - sage doctor

  artifacts:
    paths:
      - security_audit_*.json
      - sage_verification_report.txt
    expire_in: 1 week
```

______________________________________________________________________

## 常见问题

### Q1: pip-audit 显示漏洞但我无法更新包怎么办？

**A:** 评估风险：

```bash
# 查看漏洞详情
pip-audit -v

# 检查是否有其他包依赖此版本
pip show conflicting-package

# 选项 1: 等待修复版本（低危）
# 选项 2: 立即升级（高危）
# 选项 3: 替换为替代包（严重）
```

### Q2: --verify-deps 验证失败，我可以跳过吗？

**A:** 不建议跳过，但如果必须：

```bash
# 强制安装（不推荐）
./quickstart.sh --standard --yes --force

# 更好的做法：修复问题后重试
./quickstart.sh --verify-deps --standard --yes
```

### Q3: 企业代理导致校验和验证失败

**A:** 配置 pip 信任代理：

```bash
pip install \
  --index-url https://your-mirror.com/simple \
  --trusted-host your-mirror.com \
  isage[standard]
```

### Q4: 可以离线进行安全验证吗？

**A:** 可以，使用预下载的数据库：

```bash
# 离线模式
pip-audit --skip-editable

# 或使用本地 vulnerability 数据库
pip-audit --db /path/to/local/db
```

### Q5: 验证报告在哪里？

**A:** 报告文件在当前目录中：

```bash
ls -la security_audit_*.json sage_verification_report.txt

# 查看 pip-audit 报告
cat security_audit_pip_audit.json | python3 -m json.tool

# 查看 safety 报告
cat security_audit_safety.json | python3 -m json.tool
```

______________________________________________________________________

## 相关文档

- [权限管理指南](./PERMISSION_MANAGEMENT.md)
- [离线安装指南](./OFFLINE_INSTALLATION.md)
- [主安装指南](../../docs-public/docs_src/getting-started/installation.md)
- [SAGE 故障排除](../../docs/TROUBLESHOOTING.md)

______________________________________________________________________

## 支持和反馈

如发现安全问题：

1. **安全漏洞**：请联系 security@intellistream.com
1. **安装问题**：提交 [GitHub Issue](https://github.com/intellistream/SAGE/issues)
1. **建议和反馈**：加入 [SAGE 社区讨论](https://github.com/intellistream/SAGE/discussions)

______________________________________________________________________

**最后更新**：2025-11-15\
**版本**：1.0.0\
**维护者**：SAGE Security Team
