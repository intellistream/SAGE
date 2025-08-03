# IDE代码跳转支持指南

## 🎯 问题说明

当我们将`sage.utils`等模块拆分为独立的包后，可能遇到以下IDE跳转问题：

1. **导入解析失败**: IDE无法找到`from sage.utils import xxx`的定义位置
2. **跳转不准确**: 点击跳转到错误的位置或无法跳转
3. **自动补全失效**: 无法获得正确的代码补全建议
4. **类型检查问题**: mypy/pylance无法正确识别类型

## 💡 解决方案

### 方案一：开发模式安装 (推荐)

使用`pip install -e`安装包的开发模式，这样IDE就能正确解析包路径：

```bash
# 在SAGE根目录运行
pip install -e packages/sage-utils
pip install -e packages/sage-core
pip install -e packages/sage-extensions
pip install -e packages/sage-dashboard

# 或者使用我们的脚本一键设置
python scripts/setup-ide-support-simple.py
```

**优点**:
- ✅ IDE跳转完全正常
- ✅ 类型检查正确
- ✅ 自动补全完整
- ✅ 调试功能正常

**缺点**:
- ⚠️ 需要每个开发者都运行一次
- ⚠️ 虚拟环境切换时需要重新安装

### 方案二：VS Code配置优化

通过配置VS Code的Python路径来支持跳转：

```json
// .vscode/settings.json
{
  "python.analysis.extraPaths": [
    "packages/sage-core/src",
    "packages/sage-utils/src", 
    "packages/sage-extensions/src",
    "packages/sage-dashboard/backend/src"
  ],
  "python.autoComplete.extraPaths": [
    "packages/sage-core/src",
    "packages/sage-utils/src",
    "packages/sage-extensions/src", 
    "packages/sage-dashboard/backend/src"
  ],
  "python.analysis.autoSearchPaths": true,
  "python.analysis.useLibraryCodeForTypes": true,
  "python.languageServer": "Pylance"
}
```

**优点**:
- ✅ 不需要安装包
- ✅ 对所有开发者自动生效
- ✅ 支持跨包跳转

**缺点**:
- ⚠️ 只对VS Code有效
- ⚠️ 某些复杂导入可能不工作

### 方案三：PYTHONPATH环境变量

设置环境变量来帮助Python找到包：

```bash
# 在.env文件中或shell配置中添加
export PYTHONPATH="${PYTHONPATH}:packages/sage-core/src:packages/sage-utils/src:packages/sage-extensions/src"
```

**优点**:
- ✅ 对所有工具和IDE都有效
- ✅ 运行时也能正确工作

**缺点**:
- ⚠️ 需要手动维护路径
- ⚠️ 可能与其他项目冲突

## 🔧 实际测试

让我们测试一下当前的跳转功能：

### 测试代码示例

```python
# 测试文件: test_ide_jumping.py

# 这些导入应该能正确跳转
from sage.utils.config_loader import load_config
from sage.utils.logger.custom_logger import CustomLogger
from sage.utils.embedding_methods.openai import OpenAIEmbedding

# 测试使用
config = load_config("config.yaml")
logger = CustomLogger("test")
embedder = OpenAIEmbedding()

# IDE应该能够：
# 1. 跳转到load_config的定义 (Ctrl+Click)
# 2. 显示CustomLogger的方法和属性
# 3. 提供OpenAIEmbedding的自动补全
```

### 验证步骤

1. **安装开发环境**:
   ```bash
   python scripts/setup-ide-support-simple.py
   ```

2. **重启VS Code**: 确保新配置生效

3. **测试跳转**:
   - 打开包含`from sage.utils import xxx`的文件
   - 按住Ctrl并点击导入的函数/类名
   - 应该能跳转到正确的定义位置

4. **测试补全**:
   - 输入`sage.utils.`
   - 应该看到所有可用的模块和函数

## 🚨 常见问题

### Q1: 跳转到了错误的位置
**解决方案**: 清除IDE缓存，重新加载窗口
```
Ctrl+Shift+P -> "Python: Clear Cache and Reload Window"
```

### Q2: 自动补全不工作
**解决方案**: 检查Python解释器设置
```
Ctrl+Shift+P -> "Python: Select Interpreter"
```
选择正确的虚拟环境

### Q3: 类型检查报错
**解决方案**: 更新mypy配置，添加包路径
```toml
[tool.mypy]
mypy_path = [
    "packages/sage-core/src",
    "packages/sage-utils/src"
]
```

### Q4: 某些导入仍然无法跳转
**解决方案**: 检查包的`__init__.py`文件，确保正确导出了所有符号

## 📊 方案对比

| 特性 | 开发模式安装 | VS Code配置 | PYTHONPATH |
|------|-------------|-------------|------------|
| **设置复杂度** | 低 | 低 | 中 |
| **IDE兼容性** | 所有IDE | 仅VS Code | 所有IDE |
| **跳转准确性** | 100% | 95% | 90% |
| **类型检查** | 完美 | 很好 | 一般 |
| **维护成本** | 低 | 低 | 中 |

## 🎯 推荐配置

**最佳实践**: 组合使用多种方案

1. **主方案**: 开发模式安装 (保证功能完整)
2. **辅助方案**: VS Code配置 (提升用户体验)  
3. **备用方案**: PYTHONPATH (应急解决)

```bash
# 一键设置所有方案
python scripts/setup-ide-support-simple.py
```

这样可以确保在各种情况下IDE跳转都能正常工作！
