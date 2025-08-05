# SAGE 商业许可证使用指南

## 概述

SAGE 商业许可证管理工具提供了完整的许可证生命周期管理，包括生成、安装、验证和移除等功能。

> **🏗️ 架构更新**: 许可证管理工具已重构为模块化架构，位于 `tools/license/` 目录。旧的 `scripts/sage-license.py` 已完全移除。

## 🚀 新架构

许可证管理现在采用工业级模块化设计：

```
tools/license/
├── shared/           # 共享核心组件
├── client/           # 客户端工具
├── vendor/           # 供应商工具
└── sage_license.py   # 统一入口点
```

## 许可证格式

SAGE 商业许可证采用以下格式：
```
SAGE-COMM-YYYY-XXXX-XXXX-XXXX
```

- `SAGE`: 产品标识
- `COMM`: 商业版标识
- `YYYY`: 许可证年份
- `XXXX`: 客户标识码 (基于客户名生成)
- `XXXX`: 随机标识符
- `XXXX`: 校验码 (防伪验证)

## 供应商操作

### 生成许可证

```bash
# 生成默认365天许可证
python tools/license/sage_license.py generate "Company Name"

# 生成指定天数许可证
python tools/license/sage_license.py generate "Company Name" 180

# 生成30天试用许可证
python tools/license/sage_license.py generate "Trial Customer" 30
```

### 查看已生成的许可证

```bash
python tools/license/sage_license.py list
```

输出示例：
```
🔑 已生成的许可证:

1. 客户: Test Company
   密钥: SAGE-COMM-2025-142F-3M5G-3EDB
   生成时间: 2025-08-05 17:17:25
   到期时间: 2025-09-04 17:17:25
   状态: ✅ 有效
```

## 客户操作

### 安装许可证

```bash
python tools/license/sage_license.py install SAGE-COMM-2025-142F-3M5G-3EDB
```

### 查看许可证状态

```bash
python tools/license/sage_license.py status
```

输出示例：
```
🔍 SAGE 许可状态
==============================
类型: Commercial
来源: file
到期时间: 2026-12-31T00:00:00
可用功能: high-performance, enterprise-db, advanced-analytics
```

### 移除许可证

```bash
python tools/license/sage_license.py remove
```

## 许可证存储

- **许可证文件**: `~/.sage/license.key`
- **配置文件**: `~/.sage/config.json`
- **生成记录**: `~/.sage/generated_licenses.json` (仅供应商)

## 环境变量支持

也可以通过环境变量设置许可证：

```bash
export SAGE_LICENSE_KEY="SAGE-COMM-2025-142F-3M5G-3EDB"
python tools/license/sage_license.py status
```

## 安全特性

1. **校验码验证**: 每个许可证包含加密校验码，防止伪造
2. **时间验证**: 自动检查许可证是否过期
3. **格式验证**: 严格的许可证格式检查
4. **本地存储**: 许可证信息仅存储在用户本地

## 故障排除

### 常见错误

1. **"许可证校验码验证失败"**
   - 许可证密钥可能被损坏或输入错误
   - 请检查密钥是否完整且格式正确

2. **"许可证已过期"**
   - 许可证已超过有效期
   - 请联系供应商获取新的许可证

3. **"无效的许可密钥格式"**
   - 许可证格式不符合要求
   - 请确认使用正确的SAGE商业许可证

### 调试信息

使用 `-v` 参数获取详细信息：
```bash
python tools/license/sage_license.py status
```

## 集成开发

许可证验证可以集成到SAGE应用中：

```python
from scripts.sage_license import SageLicense

license_mgr = SageLicense()
if license_mgr.has_valid_license():
    # 启用商业功能
    enable_commercial_features()
else:
    # 仅开源功能
    print("需要商业许可证才能使用此功能")
```
