# SAGE Enterprise Installation Guide

基于license的现代Python包管理方式，支持开源和企业功能的条件安装。

## 📋 安装方式概览

SAGE使用现代Python包管理最佳实践，通过`optional-dependencies`来管理企业功能：

```
sage/                           # 主包（元包）
├── [base]                     # 开源核心功能
├── [enterprise]               # 企业功能（需要license）
├── [dev]                      # 开发工具
└── [all]                      # 所有功能

packages/
├── sage-kernel/               # 内核包
│   ├── [base]                # 开源内核
│   └── [enterprise]          # 企业内核扩展
├── sage-middleware/           # 中间件包  
│   ├── [base]                # 开源中间件
│   └── [enterprise]          # 企业中间件扩展
└── sage-userspace/           # 用户空间包
    ├── [base]                # 开源用户空间
    └── [enterprise]          # 企业用户空间扩展
```

## 🚀 快速开始

### 1. 开源版本安装

```bash
# 标准开源安装
pip install -r requirements.txt

# 或者直接安装主包
pip install sage
```

### 2. 企业版本安装

```bash
# 方式1: 使用requirements-commercial.txt (推荐)
pip install -r requirements-commercial.txt

# 方式2: 直接安装企业版
pip install sage[enterprise]

# 方式3: 按模块安装
pip install intsage-kernel[enterprise] intsage-middleware[enterprise] intsage-userspace[enterprise]
```

### 3. 开发环境安装

```bash
# 开发模式安装
pip install -e .[enterprise]

# 或者安装开发依赖
pip install sage[dev]
```

## 🔑 License管理

### 设置License Key

```bash
# 方式1: 环境变量
export SAGE_LICENSE_KEY="SAGE-COMM-2024-ABCD-EFGH-1234"
pip install -r requirements-commercial.txt

# 方式2: 使用license工具
python -m tools.license.sage_license install SAGE-COMM-2024-ABCD-EFGH-1234

# 方式3: 通过enterprise manager
sage-enterprise install --license-key SAGE-COMM-2024-ABCD-EFGH-1234
```

### 检查License状态

```bash
# 使用license工具
sage-license status

# 使用enterprise manager
sage-enterprise check

# 在Python中检查
python -c "import sage; sage.info()"
```

## 📦 包结构说明

### 开源包 (packages/)

| 包名 | 描述 | 主要功能 |
|-----|------|---------|
| `sage` | 主包/元包 | 统一入口，依赖管理 |
| `intsage-kernel` | 内核组件 | 核心运行时，调度器，基础队列 |
| `intsage-middleware` | 中间件 | API服务，基础数据库，消息队列 |
| `intsage-userspace` | 用户空间 | 应用框架，基础分析工具 |

### 企业扩展 (enterprise/)

每个开源包都包含对应的企业扩展：

| 企业扩展 | 位置 | 功能 |
|---------|------|------|
| `sage.kernel.enterprise` | `intsage-kernel[enterprise]` | 高性能队列，优化算法 |
| `sage.middleware.enterprise` | `intsage-middleware[enterprise]` | 企业数据库，高级API |
| `sage.userspace.enterprise` | `intsage-userspace[enterprise]` | 向量数据库，图计算 |

## 🛠️ 使用示例

### 基础使用

```python
import sage

# 检查安装状态
sage.info()

# 检查可用功能
features = sage.check_features()
print(f"Enterprise licensed: {features['enterprise_licensed']}")
```

### 开源功能

```python
# 开源功能始终可用
from sage.kernel import Queue
from sage.middleware import BasicDB
from sage.userspace import SimpleAnalytics

queue = Queue()
db = BasicDB()
analytics = SimpleAnalytics()
```

### 企业功能 (需要license)

```python
# 企业功能需要有效license
try:
    from sage.kernel.enterprise import HighPerformanceQueue
    from sage.middleware.enterprise import EnterpriseDB
    from sage.userspace.enterprise import VectorDB
    
    hq_queue = HighPerformanceQueue()
    ent_db = EnterpriseDB()
    vector_db = VectorDB()
    
    print("✅ Enterprise features available")
except ImportError as e:
    print(f"❌ Enterprise features not available: {e}")
```

### License验证

```python
from sage.enterprise_manager import SAGEEnterpriseInstaller

installer = SAGEEnterpriseInstaller()

# 检查license状态
status = installer.check_license_status()
print(f"License type: {status['type']}")
print(f"Features: {status['features']}")

# 验证企业安装
validation = installer.validate_enterprise_installation()
print(f"Enterprise components: {validation['available_components']}/{validation['total_components']}")
```

## 🔧 CLI工具

### sage-enterprise 命令

```bash
# 检查状态
sage-enterprise check

# 安装企业功能
sage-enterprise install --license-key YOUR-KEY

# 验证安装
sage-enterprise validate

# 查看安装命令
sage-enterprise commands --mode enterprise
```

### sage-license 命令

```bash
# 安装license
sage-license install SAGE-COMM-2024-ABCD-EFGH-1234

# 检查license状态  
sage-license status

# 移除license
sage-license remove
```

## 🎯 不同场景的安装方式

### 场景1: 开发者本地开发

```bash
# 1. Clone项目
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 安装开发依赖
pip install -e .[dev]

# 3. 如果有enterprise license
export SAGE_LICENSE_KEY="your-license-key"
pip install -e .[enterprise]
```

### 场景2: 生产环境部署

```bash
# 开源版本
pip install sage

# 企业版本 (with license)
SAGE_LICENSE_KEY="your-license-key" pip install sage[enterprise]
```

### 场景3: CI/CD环境

```yaml
# .github/workflows/test.yml
- name: Install SAGE
  run: |
    pip install sage[dev]
    
- name: Install Enterprise (if licensed)
  if: ${{ secrets.SAGE_LICENSE_KEY }}
  env:
    SAGE_LICENSE_KEY: ${{ secrets.SAGE_LICENSE_KEY }}
  run: |
    pip install sage[enterprise]
```

### 场景4: Docker容器

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install open source version
RUN pip install sage

# Install enterprise version if license available
ARG SAGE_LICENSE_KEY
RUN if [ ! -z "$SAGE_LICENSE_KEY" ]; then \
    SAGE_LICENSE_KEY=$SAGE_LICENSE_KEY pip install sage[enterprise]; \
    fi
```

## 📊 验证和故障排除

### 检查安装状态

```python
import sage

# 全面检查
sage.info()

# 详细检查
features = sage.check_features()
for key, value in features.items():
    print(f"{key}: {value}")
```

### 常见问题

1. **License未找到**
   ```bash
   # 检查license文件
   ls -la ~/.sage/license.key
   
   # 重新安装license
   sage-license install YOUR-LICENSE-KEY
   ```

2. **企业功能导入失败**
   ```python
   # 检查license状态
   from sage.enterprise_manager import check_enterprise_features
   status = check_enterprise_features()
   print(status)
   ```

3. **包依赖冲突**
   ```bash
   # 清理重装
   pip uninstall sage intsage-kernel intsage-middleware intsage-userspace
   pip install sage[enterprise]
   ```

## 🏗️ 开发者指南

### 添加新的企业功能

1. **在对应包中添加enterprise模块**
   ```
   packages/your-package/src/sage/your_module/enterprise/
   ├── __init__.py          # License检查
   ├── your_feature.py      # 企业功能实现
   └── tests/              # 企业功能测试
   ```

2. **更新pyproject.toml**
   ```toml
   [project.optional-dependencies]
   enterprise = [
       "your-enterprise-dependencies>=1.0.0",
   ]
   ```

3. **添加License检查**
   ```python
   from sage.kernel.enterprise import require_license
   
   @require_license
   def enterprise_function():
       # 企业功能实现
       pass
   ```

### 测试enterprise功能

```bash
# 运行enterprise测试
pytest packages/*/tests/ -k "enterprise"

# 验证license集成
sage-enterprise validate
```

## 📚 参考文档

- [License Management Guide](../tools/license/README.md)
- [Package Development Guide](../docs/building_system/)
- [Commercial Migration Report](../packages/commercial/MIGRATION_REPORT.md)
- [API Documentation](https://sage-docs.example.com/api/)

---

通过这种方式，SAGE实现了现代Python包管理的最佳实践：
- ✅ 统一的安装入口
- ✅ 条件性功能启用
- ✅ 清晰的license管理
- ✅ 开发友好的工作流
- ✅ 企业级功能控制
