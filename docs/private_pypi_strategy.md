# SAGE 私有PyPI分发方案
# Private PyPI Distribution Strategy

## 🎯 方案概述

### 公开PyPI (pypi.org)
```bash
pip install sage-oss              # 开源版本
pip install sage-oss[basic]       # 开源版 + 基础功能
```

### 私有PyPI (企业客户)
```bash
# 配置私有PyPI源
pip install -i https://pypi.intellistream.com/simple/ sage-enterprise
# 或
pip install --extra-index-url https://pypi.intellistream.com/simple/ sage[enterprise]
```

## 📦 包分发策略

### A. 开源包 (公开PyPI)
- `sage-oss-kernel`     # 纯开源核心
- `sage-oss-middleware` # 纯开源中间件
- `sage-oss-apps`       # 纯开源应用
- `sage-oss`            # 开源元包

### B. 企业包 (私有PyPI)
- `sage-enterprise-kernel`     # 企业版核心扩展
- `sage-enterprise-middleware` # 企业版中间件扩展
- `sage-enterprise-apps`       # 企业版应用扩展  
- `sage-enterprise`            # 企业版元包

### C. 统一安装包
- `sage` # 智能检测许可证，自动选择开源/企业版

## 🚀 实现步骤

### 1. 搭建私有PyPI服务器
```bash
# 使用 pypiserver
pip install pypiserver
pypi-server -p 8080 -P .htpasswd packages/
```

### 2. 配置用户安装
```bash
# 开源用户
pip install sage-oss

# 企业用户 (需要账号密码)
pip install -i https://pypi.intellistream.com/simple/ \
    --trusted-host pypi.intellistream.com \
    sage-enterprise
```

### 3. 企业版激活
```python
import sage
sage.activate_enterprise_license("YOUR-LICENSE-KEY")
```

## 💰 商业模式

### 开源版 (免费)
- 基础功能
- 社区支持
- 公开GitHub仓库

### 企业版 (付费)
- 高级功能
- 商业支持
- 私有仓库访问
- 专业服务

## 🔐 安全考虑

1. **许可证绑定**：企业版包含许可证验证
2. **访问控制**：私有PyPI需要认证
3. **代码保护**：企业版关键代码混淆
4. **使用监控**：跟踪企业版使用情况

## 📋 用户体验

### 开源用户 (极简)
```bash
pip install sage-oss
python -c "import sage; sage.hello()"
```

### 企业用户 (稍复杂但完整)
```bash
# 一次性配置
pip install --extra-index-url https://pypi.intellistream.com/simple/ sage[enterprise]
export SAGE_LICENSE_KEY="your-key"

# 日常使用
python -c "import sage; sage.run_enterprise_workflow()"
```
