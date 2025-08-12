# SAGE ```bash
pip install isage
```

### 企业版安装

```bash
pip install isage[enterprise]
```allation Guide
# SAGE PyPI 安装指南

## 🎯 用户如何从PyPI安装SAGE

### 📦 开源版安装

```bash
pip install isage
```

### 🏢 企业版安装

```bash
pip install isage[enterprise]
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

1. **`isage`** - 元包，依赖所有子包
   - 基础版：`isage` (包含 kernel, middleware)
   - 企业版：`isage[enterprise]` 

2. **`isage-kernel`** - 核心包
   - 基础版：`isage-kernel` (标准队列)
   - 企业版：`isage-kernel[enterprise]` (高性能队列)

3. **`isage-middleware`** - 中间件包  
   - 基础版：`isage-middleware` (基础数据库)
   - 企业版：`isage-middleware[enterprise]` (企业数据库)

### 不发布到PyPI的内容：

- 商业许可证文件
- 内部开发工具
- 企业版测试套件
- 私有配置文件

## 🚀 快速开始示例

### 开源用户：
```python
# 安装
pip install isage

# 使用
import sage
sage.run_basic_workflow()
```

### 企业版用户：
```python  
# 安装
pip install isage[enterprise]

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
RUN pip install isage[enterprise]
ENV SAGE_LICENSE_KEY="your-license-key"
```

### conda环境：
```bash
conda create -n sage python=3.10
conda activate sage
pip install isage[enterprise]
```

### 离线安装：
```bash
# 下载wheel文件
pip download isage[enterprise] -d ./wheels

# 离线安装
pip install --find-links ./wheels --no-index isage[enterprise]
```

## 🔍 验证安装

```bash
# 验证开源版
python -c "import sage; print('SAGE Open Source Ready!')"

# 验证企业版
python -c "import sage.kernel.enterprise; print('SAGE Enterprise Ready!')"
```

## ⚠️ 故障排除

### 1. 安装问题

**依赖冲突？**
```bash
# 创建新的虚拟环境
python -m venv sage-env
source sage-env/bin/activate  # Linux/Mac
# 或者 sage-env\Scripts\activate  # Windows

pip install isage
```

**安装缓慢？**
```bash
# 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple isage
```

**权限错误？**
```bash
# 用户安装模式
pip install --user isage
```

### 2. 导入问题

**ModuleNotFoundError？**
```bash
# 检查安装路径
pip show isage

# 重新安装
pip uninstall isage
pip install isage
```

**版本冲突？**
```bash
# 检查版本
pip list | grep isage

# 强制重新安装
pip install --force-reinstall isage
```

### 3. 企业版问题

**许可证错误？**
```bash
# 检查许可证设置
echo $SAGE_LICENSE_KEY

# 验证许可证文件
cat ~/.sage/license

# 重新设置许可证
export SAGE_LICENSE_KEY="your-valid-license-key"
```

**企业功能导入失败？**
```bash
# 确认安装了企业版
pip list | grep isage

# 重新安装企业版
pip install --upgrade isage[enterprise]
```

### 4. RemoteEnvironment 连接问题

**JobManager未启动？**
```bash
# 安装后首次使用
sage jobmanager start

# 检查状态
sage jobmanager status
```

**网络连接问题？**
```bash
# 检查端口是否被占用
netstat -tlnp | grep 19001

# 使用自定义端口
sage jobmanager start --port 19002
```

### 5. 性能问题

**启动缓慢？**
```bash
# 预编译模块
python -c "import sage; sage.compile_cache()"

# 检查系统资源
sage system-info
```

### 📞 获取帮助

- 🔍 交互式安装向导：`sage-install`
- 📚 完整文档：[GitHub文档](https://github.com/ShuhuaGao/SAGE/tree/main/docs)
- 🐛 Bug报告：[GitHub Issues](https://github.com/ShuhuaGao/SAGE/issues)
- 💬 社区讨论：[GitHub Discussions](https://github.com/ShuhuaGao/SAGE/discussions)
- 📧 企业支持：enterprise@sage-ai.com
