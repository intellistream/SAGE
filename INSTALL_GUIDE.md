# SAGE 安装指南

## 快速开始

### 开源版本

```bash
# 1. 克隆仓库
git clone <repo-url>
cd SAGE

# 2. 安装核心包 (生产环境)
pip install -r requirements.txt

# 3. 开发环境 (推荐)
pip install -r requirements-dev.txt
```

### 商业版本

```bash
# 1. 安装开源版本
pip install -r requirements.txt

# 2. 安装许可证
python scripts/sage-license.py install <your-license-key>

# 3. 安装商业版组件
pip install -r requirements-commercial.txt

# 4. 验证安装
python scripts/sage-license.py status
```

## 安装选项说明

| 文件 | 用途 | 包含内容 |
|------|------|----------|
| `requirements.txt` | 生产环境 | 核心SAGE包 |
| `requirements-dev.txt` | 开发环境 | 核心包 + 开发工具 |
| `requirements-commercial.txt` | 商业版 | 核心包 + 商业功能 |

## 包结构

```
SAGE/
├── packages/sage/              # 元包
├── packages/sage-kernel/       # 核心引擎
├── packages/sage-middleware/   # 中间件
├── packages/sage-userspace/    # 用户空间
├── packages/sage-tools/        # 工具集
│   ├── sage-cli/              # 命令行工具
│   └── sage-dev-toolkit/      # 开发工具
└── packages/commercial/        # 商业版组件 (需要许可证)
    ├── sage-kernel/
    ├── sage-middleware/
    └── sage-userspace/
```

## 验证安装

```bash
# 检查核心包
python -c "import sage; print('SAGE installed successfully')"

# 检查CLI工具
sage --version

# 检查商业版许可证 (如果适用)
python scripts/sage-license.py status
```

## 故障排除

### 常见问题

1. **导入错误**: 确保使用editable install (`-e`)
2. **依赖冲突**: 建议使用虚拟环境
3. **商业版访问**: 检查许可证状态

### 开发者注意事项

- 所有包都使用editable install，修改代码后无需重新安装
- 商业版代码需要有效许可证才能访问
- 使用`requirements-dev.txt`获得最佳开发体验

# 立即测试
python -c "from sage.api import DataStream; ..."
```

### 验证安装
```bash
# 检查安装的包
pip list | grep sage

# 测试导入
python -c "import sage; print('SAGE Ready!')"
```

## 🏢 商业版本

如需商业版本功能，请使用许可管理工具：

```bash
# 安装商业许可
python scripts/sage-license.py install YOUR-LICENSE-KEY

# 重新安装以获得商业功能
pip install --upgrade --force-reinstall -e .
```

## 💡 常见问题

### Q: 如何切换开发/生产模式？
```bash
# 开发模式 (包含测试工具)
pip install -e ".[dev]"

# 生产模式 (仅核心功能)
pip install -e .
```

### Q: 如何更新依赖？
```bash
# 重新安装所有依赖
pip install --upgrade --force-reinstall -e ".[dev]"
```

### Q: 如何卸载？
```bash
# 卸载SAGE相关包
pip uninstall sage sage-kernel sage-middleware sage-userspace sage-cli sage-dev-toolkit
```

---

**现在安装更简单了！推荐使用 `pip install -e ".[dev]"` 进行开发。** 🎯
