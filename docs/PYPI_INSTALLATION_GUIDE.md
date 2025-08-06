# SAGE PyPI Installation Guide
# SAGE PyPI 安装指南

## 🎯 用户如何从PyPI安装SAGE

### 📦 开源版安装

```bash
# 方式1: 安装完整SAGE框架 (推荐)
pip install intsage

# 方式2: 按需安装模块
pip install intsage-kernel      # 核心功能
pip install intsage-middleware  # 中间件功能  
pip install intsage-apps        # 应用组件

# 方式3: 一次性安装所有模块
pip install intsage-kernel intsage-middleware intsage-apps intsage
```

### 🏢 企业版安装

```bash
# 方式1: 安装企业版 (需要许可证)
pip install intsage[enterprise]

# 方式2: 分模块安装企业版
pip install intsage-kernel[enterprise]
pip install intsage-middleware[enterprise] 
pip install intsage-apps[enterprise]

# 方式3: 开发环境安装
pip install intsage[enterprise-dev]
```

### 🔐 许可证配置

企业版功能需要有效的商业许可证：

```bash
# 设置许可证密钥
export SAGE_LICENSE_KEY="your-license-key"

# 或者通过文件配置（推荐生产环境）
echo "your-license-key" > ~/.sage/license
```

## 📋 PyPI包结构

### 发布到PyPI的包：

1. **`intsage`** - 元包，依赖所有子包
   - 基础功能：完整SAGE框架
   - 企业版：`intsage[enterprise]` 

2. **`intsage-kernel`** - 核心包
   - 基础功能：计算引擎、任务调度
   - 企业版：`intsage-kernel[enterprise]` (高性能队列)

3. **`intsage-middleware`** - 中间件包  
   - 基础功能：API、认证、缓存
   - 企业版：`intsage-middleware[enterprise]` (企业数据库)

4. **`intsage-apps`** - 应用包
   - 基础功能：基础应用组件
   - 企业版：`intsage-apps[enterprise]` (向量数据库、图计算)

### 不发布到PyPI的内容：

- 商业许可证文件
- 内部开发工具
- 企业版测试套件
- 私有配置文件

## 🚀 快速开始示例

### 开源用户：
```python
# 安装
pip install intsage

# 使用
import sage
sage.run_basic_workflow()
```

### 企业版用户：
```python  
# 安装
pip install intsage[enterprise]

# 配置许可证
export SAGE_LICENSE_KEY="SAGE-COMM-2024-XXXX"

# 使用企业功能
import sage.kernel.enterprise
import sage.middleware.enterprise
import sage.apps.enterprise
```

## ⚡ 特殊安装场景

### Docker环境：
```dockerfile
FROM python:3.10
RUN pip install intsage[enterprise]
ENV SAGE_LICENSE_KEY="your-license-key"
```

### conda环境：
```bash
conda create -n sage python=3.10
conda activate sage
pip install intsage[enterprise]
```

### 离线安装：
```bash
# 下载wheel文件
pip download intsage[enterprise] -d ./wheels

# 离线安装
pip install --find-links ./wheels --no-index intsage[enterprise]
```

## 🔍 验证安装

```bash
# 验证开源版
python -c "import sage; print('SAGE Open Source Ready!')"

# 验证企业版
python -c "import sage.kernel.enterprise; print('SAGE Enterprise Ready!')"
```
