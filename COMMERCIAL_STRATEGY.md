# 🏢 SAGE 商业版本策略

## 🎯 双版本架构设计

### 📁 目录结构
```
/home/shuhao/SAGE/
├── packages/
│   ├── sage-kernel/           # 开源核心
│   ├── sage-middleware/       # 开源中间件
│   ├── sage-userspace/        # 开源用户空间
│   ├── sage-tools/            # 开源工具
│   └── commercial/            # 🔒 商业版 (闭源)
│       ├── sage-kernel/       # 增强版内核
│       ├── sage-middleware/   # 企业级中间件
│       └── sage-userspace/    # 企业用户空间
├── requirements.txt           # 开源版 (可上传PyPI)
├── requirements-dev.txt       # 开源开发版
└── requirements-commercial.txt # 🔒 商业版 (不上传)
```

## 🔐 商业版保护机制

### 1. 文件级保护
```bash
# .gitignore 已配置保护商业文件
requirements-commercial.txt   # 商业安装文件
packages/commercial/          # 整个商业目录
*.commercial.*               # 商业相关文件
*-commercial-*              # 商业命名文件
```

### 2. 安装分离
```bash
# 开源版安装 (安全上传PyPI)
pip install -r requirements.txt        # ✅ 可公开
pip install -r requirements-dev.txt    # ✅ 可公开

# 商业版安装 (内部使用)
pip install -r requirements-commercial.txt  # 🔒 绝不上传
make commercial-install                      # 🔒 内部命令
```

## 📦 PyPI 发布策略

### ✅ 可以安全上传到PyPI的文件:
- `requirements.txt` - 只包含开源包路径
- `requirements-dev.txt` - 只包含开源包路径
- `packages/sage-kernel/` - 开源核心
- `packages/sage-middleware/` - 开源中间件
- `packages/sage-userspace/` - 开源用户空间
- `packages/sage-tools/` - 开源工具

### 🔒 绝对不能上传的文件:
- `requirements-commercial.txt`
- `packages/commercial/` 整个目录
- 任何包含 "commercial" 的文件

## 🚀 使用方式

### 开源开发者
```bash
# 社区开发者使用
git clone https://github.com/intellistream/SAGE.git
cd SAGE
pip install -r requirements-dev.txt
```

### 商业版开发者 (内部)
```bash
# 内部开发者额外步骤
# 1. 通过内部渠道获取商业包
# 2. 解压到 packages/commercial/
# 3. 创建 requirements-commercial.txt (不在git中)
make commercial-install
```

## 🛡️ 安全检查

### 上传前检查清单:
- [ ] `packages/commercial/` 不在git中
- [ ] `requirements-commercial.txt` 不在git中  
- [ ] 所有开源requirements只指向 `packages/` 下的开源目录
- [ ] .gitignore 包含商业文件保护规则

### 自动检查脚本:
```bash
# 检查是否包含商业内容
grep -r "commercial" requirements*.txt
if [ $? -eq 0 ]; then
    echo "❌ 发现商业内容，禁止上传!"
    exit 1
fi
```

## 💡 优势

1. **完全分离** - 开源和商业版本完全隔离
2. **安全上传** - requirements.txt 可以安全上传PyPI
3. **灵活部署** - 开源用户获得完整开源功能
4. **商业保护** - 商业功能完全闭源
5. **统一体验** - 相同的pip install体验

---

**这样既能保护商业代码，又能安全地将开源版本发布到PyPI！** 🎯
