# SAGE 依赖验证系统

## 概述

依赖验证系统（Dependency Verification System）提供了安全的依赖包安装机制，包括 SHA256 校验和验证、安全漏洞扫描等功能，确保安装过程的安全性和完整性。

## 核心功能

### 1. Checksum 验证

- 计算下载包的 SHA256 校验和
- 从 PyPI 获取官方校验和
- 对比验证包的完整性
- 检测包是否被篡改

### 2. 安全漏洞扫描

- 使用 `pip-audit` 检查已知漏洞
- 使用 `safety` 扫描安全问题
- 使用 `bandit` 进行代码审计
- 生成详细的安全报告

### 3. 深度验证

- 验证依赖链的完整性
- 检查许可证合规性
- 分析依赖冲突
- 生成依赖关系图

## 安装安全工具

```bash
# 安装 pip-audit（推荐）
pip install pip-audit

# 安装 safety
pip install safety

# 安装 bandit（代码安全审计）
pip install bandit

# 一次性安装所有工具
pip install pip-audit safety bandit
```

## 使用方法

### 基本用法

依赖验证功能已集成到安装脚本中，使用 `--verify-deps` 参数启用：

```bash
# 标准安装时启用依赖验证
./quickstart.sh --standard --verify-deps --yes

# 开发安装时启用依赖验证
./quickstart.sh --dev --verify-deps --yes
```

### 手动验证单个包

```bash
# 加载验证模块
source tools/install/examination_tools/dependency_verification.sh

# 验证下载的包
verify_package_checksum "package.whl" "expected_sha256_checksum"

# 计算文件 checksum
compute_file_checksum "package.whl"
```

### 获取 PyPI 官方 Checksum

```bash
# 获取包的所有版本 checksum
get_pypi_package_checksums "numpy"

# 获取特定版本 checksum
get_pypi_package_checksums "numpy" "1.24.0"
```

### 漏洞扫描

```bash
# 扫描 requirements.txt 中的所有包
check_vulnerabilities "requirements.txt"

# 指定输出目录
check_vulnerabilities "requirements.txt" "/tmp/scan_results"

# 使用特定扫描工具
check_vulnerabilities "requirements.txt" "/tmp" "pip-audit"
check_vulnerabilities "requirements.txt" "/tmp" "safety"
check_vulnerabilities "requirements.txt" "/tmp" "both"
```

### 深度验证

```bash
# 执行完整的依赖验证
perform_deep_verification "requirements.txt" "/tmp/report" "strict"

# 非严格模式（仅警告，不中断）
perform_deep_verification "requirements.txt" "/tmp/report" "loose"
```

## API 函数参考

### compute_file_checksum(file_path)

计算文件的 SHA256 校验和。

**参数：**

- `file_path` - 文件路径

**返回：**

- 成功：SHA256 字符串
- 失败：错误信息

**示例：**

```bash
checksum=$(compute_file_checksum "package.whl")
echo "SHA256: $checksum"
```

### verify_package_checksum(package_path, expected_checksum)

验证包文件的校验和。

**参数：**

- `package_path` - 包文件路径
- `expected_checksum` - 期望的 SHA256 值

**返回：**

- 0：验证通过
- 1：验证失败

**示例：**

```bash
if verify_package_checksum "numpy.whl" "abc123..."; then
    echo "验证通过"
else
    echo "验证失败"
fi
```

### get_pypi_package_checksums(package_name, [version])

从 PyPI 获取包的官方校验和。

**参数：**

- `package_name` - 包名
- `version` - 可选，指定版本

**返回：**

- 文件名:校验和 列表

**示例：**

```bash
get_pypi_package_checksums "requests" "2.28.0"
```

### check_vulnerabilities(requirements_file, [output_dir], [scan_type])

检查依赖包的安全漏洞。

**参数：**

- `requirements_file` - requirements.txt 路径
- `output_dir` - 可选，报告输出目录
- `scan_type` - 可选，扫描类型：`pip-audit`, `safety`, `both`

**返回：**

- 0：无漏洞或轻微问题
- 1：发现严重漏洞

**示例：**

```bash
if check_vulnerabilities "requirements.txt" "/tmp/reports" "both"; then
    echo "安全检查通过"
else
    echo "发现安全问题"
fi
```

### perform_deep_verification(requirements_file, [output_dir], [mode])

执行深度依赖验证。

**参数：**

- `requirements_file` - requirements.txt 路径
- `output_dir` - 可选，报告输出目录
- `mode` - 可选，验证模式：`strict`, `loose`

**返回：**

- 0：验证通过
- 1：验证失败

**示例：**

```bash
perform_deep_verification "requirements.txt" "/tmp/reports" "strict"
```

## 在安装脚本中集成

### quickstart.sh 集成示例

```bash
#!/bin/bash
source tools/install/examination_tools/dependency_verification.sh

# 检查是否启用依赖验证
VERIFY_DEPS=false
for arg in "$@"; do
    if [ "$arg" = "--verify-deps" ]; then
        VERIFY_DEPS=true
        break
    fi
done

# 安装依赖前进行验证
if [ "$VERIFY_DEPS" = true ]; then
    echo "🔒 开始依赖验证..."

    # 检查漏洞
    if ! check_vulnerabilities "requirements.txt" ".sage/reports" "both"; then
        echo "❌ 发现安全漏洞！"
        exit 1
    fi

    # 深度验证
    if ! perform_deep_verification "requirements.txt" ".sage/reports" "strict"; then
        echo "❌ 依赖验证失败！"
        exit 1
    fi

    echo "✅ 依赖验证通过"
fi

# 继续正常安装流程
pip install -r requirements.txt
```

### 下载后验证

```bash
# 下载包
pip download numpy==1.24.0 -d /tmp/packages

# 获取官方 checksum
expected_checksum=$(get_pypi_package_checksums "numpy" "1.24.0" | grep "numpy-1.24.0" | cut -d':' -f2)

# 验证下载的包
for wheel in /tmp/packages/*.whl; do
    if ! verify_package_checksum "$wheel" "$expected_checksum"; then
        echo "❌ 包验证失败，请勿安装"
        exit 1
    fi
done

# 验证通过，安装
pip install /tmp/packages/*.whl
```

## 安全报告

### 报告结构

验证系统会生成以下报告文件：

```
.sage/reports/
├── pip-audit-report.json       # pip-audit 扫描结果
├── pip-audit-report.txt        # pip-audit 文本报告
├── safety-report.json          # safety 扫描结果
├── safety-report.txt           # safety 文本报告
├── bandit-report.json          # bandit 代码审计
├── verification-summary.txt    # 验证总结
└── checksums.txt               # 包校验和列表
```

### 查看报告

```bash
# 查看 pip-audit 报告
cat .sage/reports/pip-audit-report.txt

# 查看 safety 报告
cat .sage/reports/safety-report.txt

# 查看验证总结
cat .sage/reports/verification-summary.txt
```

### 报告示例

```
=== 依赖验证报告 ===
日期: 2025-11-15 14:30:00
验证模式: strict

--- 漏洞扫描结果 ---
✓ pip-audit: 无漏洞
✓ safety: 无漏洞

--- Checksum 验证 ---
✓ numpy-1.24.0.whl: abc123...
✓ pandas-1.5.0.whl: def456...
✓ requests-2.28.0.whl: ghi789...

总计: 3 个包
验证通过: 3
验证失败: 0

结论: ✅ 所有依赖验证通过
```

## 配置选项

### 环境变量

```bash
# 强制启用依赖验证
export SAGE_FORCE_VERIFY_DEPS=1

# 设置验证级别：loose, normal, strict
export SAGE_VERIFY_LEVEL=strict

# 指定安全扫描工具
export SAGE_SECURITY_TOOL=pip-audit  # 或 safety, both

# 自定义报告目录
export SAGE_REPORT_DIR=/custom/path/reports

# 跳过特定包的验证（逗号分隔）
export SAGE_SKIP_VERIFY_PACKAGES=package1,package2
```

### 配置文件

在 `.sage/config/verification.json` 中配置：

```json
{
    "verify_level": "strict",
    "security_tools": ["pip-audit", "safety"],
    "skip_packages": [],
    "checksum_required": true,
    "fail_on_warning": false,
    "report_format": "both"
}
```

## 故障排查

### 问题：pip-audit 未安装

```bash
# 安装 pip-audit
pip install pip-audit

# 或在 requirements.txt 中添加
echo "pip-audit" >> requirements.txt
```

### 问题：PyPI API 访问失败

```bash
# 使用国内镜像
export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 或手动下载 checksum 文件
curl -s https://pypi.org/pypi/numpy/json > /tmp/numpy.json
```

### 问题：Checksum 不匹配

```bash
# 重新下载包
pip download --no-cache-dir numpy==1.24.0

# 清除 pip 缓存
pip cache purge

# 从官方 PyPI 下载
pip download --index-url https://pypi.org/simple numpy==1.24.0
```

### 问题：发现漏洞

```bash
# 查看详细漏洞信息
cat .sage/reports/pip-audit-report.txt

# 升级有漏洞的包
pip install --upgrade vulnerable-package

# 或锁定到安全版本
pip install vulnerable-package==safe-version
```

## 性能影响

- Checksum 计算：~100ms per package
- PyPI API 查询：~200ms per package
- pip-audit 扫描：~5-10s for 100 packages
- safety 扫描：~3-5s for 100 packages

对于标准安装（~50 个包），总验证时间约 30-60 秒。

## 最佳实践

1. **CI/CD 中启用验证**

   ```yaml
   - name: Install with verification
     run: ./quickstart.sh --standard --verify-deps --yes
   ```

1. **定期更新安全数据库**

   ```bash
   pip install --upgrade pip-audit safety
   ```

1. **保存验证报告**

   ```bash
   mkdir -p reports/$(date +%Y%m%d)
   cp -r .sage/reports/* reports/$(date +%Y%m%d)/
   ```

1. **使用锁定文件**

   ```bash
   pip freeze > requirements.lock
   # 从锁定文件安装，确保可重现性
   pip install -r requirements.lock
   ```

1. **审查漏洞报告**

   - 定期查看安全报告
   - 及时更新有漏洞的包
   - 评估漏洞影响范围

## 安全性考虑

### 信任链

- 仅从官方 PyPI 获取 checksum
- 使用 HTTPS 防止中间人攻击
- 验证 PyPI 响应的完整性

### 漏洞数据库

- pip-audit：使用 OSV 数据库
- safety：使用 SafetyDB 数据库
- 定期更新数据库以获取最新漏洞信息

### 隐私保护

- 扫描过程在本地进行
- 不上传包信息到第三方服务
- 报告仅存储在本地

## 未来改进

- [ ] 支持 PGP 签名验证
- [ ] 集成 Sigstore/Cosign 验证
- [ ] 自动修复已知漏洞
- [ ] 依赖关系可视化
- [ ] 许可证合规性检查
- [ ] SBOM (Software Bill of Materials) 生成

## 相关资源

- **实现代码**: `tools/install/examination_tools/dependency_verification.sh`
- **安全文档**: `docs/security/SECURITY_BEST_PRACTICES.md`
- **故障排查**: `docs/TROUBLESHOOTING.md`
- **pip-audit 文档**: https://pypi.org/project/pip-audit/
- **safety 文档**: https://pypi.org/project/safety/

## 参考标准

- [PEP 458](https://peps.python.org/pep-0458/) - PyPI 安全增强
- [PEP 480](https://peps.python.org/pep-0480/) - 存活的 PEP
- [SLSA Framework](https://slsa.dev/) - 软件供应链安全
- [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/)
