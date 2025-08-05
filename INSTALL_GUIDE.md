# 🚀 SAGE 安装指南 (开源 + 商业版)

## 🎯 双版本Requirements文件

### 📁 文件结构
```
/home/shuhao/SAGE/
├── requirements.txt           # 🌍 开源生产版 (可上传PyPI)
├── requirements-dev.txt       # 👨‍💻 开源开发版 (可上传PyPI)  
└── requirements-commercial.txt # 🏢 商业版 (� 绝不上传)
```

## 🌍 开源版本安装

### �‍💻 开发者安装（推荐）
```bash
# 方法1: 使用Makefile (推荐)
make dev-install

# 方法2: 直接使用pip
pip install -r requirements-dev.txt
```

**包含功能：**
- ✅ **sage-kernel** - 核心流处理引擎
- ✅ **sage-middleware** - 中间件服务  
- ✅ **sage-userspace** - 用户应用层
- ✅ **sage-tools/sage-cli** - 命令行工具
- ✅ **sage-tools/sage-dev-toolkit** - 开发工具包
- ✅ **开发工具** - pytest, black, isort, flake8, mypy, jupyter

### � 生产环境安装
```bash
pip install -r requirements.txt
```

## 🏢 商业版本安装 (内部使用)

### 🔒 商业版开发者安装
```bash
# 需要商业授权和内部访问权限
make commercial-install

# 或直接使用pip (如果有requirements-commercial.txt)
pip install -r requirements-commercial.txt
```

**额外商业功能：**
- ⭐ **sage-kernel-commercial** - 高性能队列，企业级优化
- ⭐ **sage-middleware-commercial** - 数据库连接器，存储中间件
- ⭐ **sage-userspace-commercial** - 企业用户空间，高级安全

## 🔐 PyPI 发布安全性

### ✅ 可以安全上传的内容：
- `requirements.txt` - 只包含开源包路径
- `requirements-dev.txt` - 只包含开源包路径
- 所有 `packages/` 下的开源目录

### 🔒 绝对不能上传的内容：
- `requirements-commercial.txt` 
- `packages/commercial/` 目录
- 任何包含 "commercial" 的文件

### 🛡️ 安全检查
```bash
# 上传前运行安全检查
./scripts/check-commercial-safety.sh

# 如果通过检查，显示: ✅ 安全! 可以上传到PyPI
# 如果发现商业内容，显示: ❌ 危险! 发现商业内容
```

## 🔄 开发体验

### Editable模式优势
```python
# 修改代码后立即生效，无需重新安装
# 编辑 packages/sage-kernel/src/sage/api/datastream.py

# 立即测试
python -c "from sage.api import DataStream; ..."
```

## 💡 常用命令

```bash
# 开源版安装
make dev-install                    # 开发版
pip install -r requirements.txt     # 生产版

# 商业版安装 (内部)
make commercial-install             # 需要商业授权

# 安全检查
./scripts/check-commercial-safety.sh

# 查看安装的包
pip list | grep sage

# 测试安装
python -c "import sage; print(f'SAGE {sage.__version__} ready!')"
```

## 🎯 总结

1. **完美分离** - 开源和商业版本完全隔离
2. **安全发布** - 可以安心上传requirements.txt到PyPI
3. **统一体验** - 相同的pip install开发体验
4. **商业保护** - 商业功能完全闭源保护
5. **自动检查** - 防止意外泄露商业内容

---

**现在您既有简单的pip安装体验，又有完善的商业版本保护！** 🎯
