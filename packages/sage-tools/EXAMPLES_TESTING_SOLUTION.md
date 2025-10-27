# Examples Testing Tools - PyPI 分发问题解决方案

## 📋 问题

开发者如果通过 PyPI 安装 `sage-tools`，那么 `examples/` 代码不会被安装，导致 Examples 测试工具无法使用。

## ✅ 解决方案

**将 Examples 测试工具定位为"仅开发环境可用"的功能**

### 核心思路

1. **目标用户明确**：这些工具主要服务于 SAGE 的开发者和贡献者，而非普通用户
2. **使用场景清晰**：开发者总是会克隆完整的仓库进行开发
3. **职责分离**：开发工具应该在开发环境中使用

## 🎯 实现方式

### 1. 智能环境检测

```python
def find_examples_directory() -> Optional[Path]:
    """按优先级查找 examples 目录"""
    # 1. 检查 SAGE_ROOT 环境变量
    # 2. 从当前目录向上查找
    # 3. 从包安装位置推断
    # 4. Git 仓库根目录检测
```

**支持的场景：**
- ✅ 从源码安装：`pip install -e packages/sage-tools[dev]`
- ✅ Git 仓库中运行
- ✅ 设置 SAGE_ROOT 环境变量
- ❌ 从 PyPI 安装（预期行为）

### 2. 友好的错误提示

```python
raise RuntimeError(
    "SAGE development environment not found.\n\n"
    "To use these tools:\n"
    "  1. Clone: git clone https://github.com/intellistream/SAGE\n"
    "  2. Install: pip install -e packages/sage-tools[dev]\n"
    "  3. Or set: export SAGE_ROOT=/path/to/SAGE\n"
)
```

### 3. 分层错误处理

- **导入时**：只警告（warning），不阻止
- **使用时**：详细错误，附带解决方案

## 📊 对不同用户的影响

### 普通用户（PyPI 安装）

```bash
pip install isage-tools
```

**影响**：
- ✅ 正常安装和使用所有核心功能
- ⚠️ Examples 测试工具不可用（但他们不需要）
- ✅ 不会有任何错误（除非主动使用 examples 工具）

### 开发者（源码安装）

```bash
git clone https://github.com/intellistream/SAGE
cd SAGE
pip install -e packages/sage-tools[dev]
```

**影响**：
- ✅ 所有功能完全可用
- ✅ 可以运行 `sage-dev examples test`
- ✅ 自动检测开发环境

### CI/CD 环境

```yaml
- uses: actions/checkout@v3  # 克隆仓库
- run: pip install -e packages/sage-tools[dev]
- run: sage-dev examples test
```

**影响**：
- ✅ 完全正常工作
- ✅ 无需额外配置

## 🎨 设计优势

### 1. 简洁性 🎯
- 代码简单，易于维护
- 无需复杂的下载、缓存逻辑
- 职责清晰

### 2. 性能 ⚡
- PyPI 包保持小巧（不包含 examples）
- 无需网络下载
- 无需版本同步检查

### 3. 可维护性 🔧
- Examples 更新不影响工具发布
- 工具和示例在同一仓库，保持同步
- 测试数据易于管理

### 4. 用户体验 😊
- **开发者**：零额外配置
- **普通用户**：不受影响
- **错误提示**：清晰且可操作

## 📝 使用示例

### 检查环境

```python
from sage.tools.dev.examples.utils import (
    get_development_info,
    ensure_development_environment
)

# 获取环境信息
info = get_development_info()
print(f"Examples directory: {info['examples_dir']}")

# 确保环境可用
if ensure_development_environment():
    print("✓ Ready to test examples")
```

### 运行测试

```bash
# 分析示例
sage-dev examples analyze

# 快速测试
sage-dev examples test --quick

# 测试特定类别
sage-dev examples test --category tutorials
```

### Python API

```python
from sage.tools.dev.examples import ExampleTestSuite

try:
    suite = ExampleTestSuite()
    stats = suite.run_all_tests(quick_only=True)
    print(f"Pass rate: {stats['passed'] / stats['total'] * 100:.1f}%")
except RuntimeError as e:
    print(f"Not in development environment: {e}")
```

## 🚫 拒绝的替代方案

### ❌ 方案 1：打包 examples 到 PyPI
- **问题**：显著增加包大小
- **问题**：更新频繁，发布困难
- **问题**：包含测试数据不适合分发

### ❌ 方案 2：运行时下载 examples
- **问题**：需要网络连接
- **问题**：版本同步复杂
- **问题**：离线环境无法使用
- **问题**：过度工程化

### ❌ 方案 3：创建独立包
- **问题**：没有解决核心问题
- **问题**：增加管理复杂度

## 📚 文档位置

1. **设计文档**：`docs/dev-notes/architecture/examples-testing-pypi-strategy.md`
2. **使用指南**：`packages/sage-tools/src/sage/tools/dev/examples/README.md`
3. **API 文档**：模块 docstrings
4. **示例代码**：`packages/sage-tools/examples/demo_examples_testing.py`

## ✨ 关键要点

1. **这不是 bug，而是设计决策** - Examples 测试工具本就是为开发者设计的
2. **普通用户不需要** - 他们通过 PyPI 安装后使用 SAGE 框架即可
3. **开发者自然满足条件** - 他们会克隆仓库进行开发
4. **清晰的错误提示** - 如果误用会得到明确的指引

## 🎓 经验总结

- ✅ **明确目标用户**：不是所有功能都需要对所有人可用
- ✅ **职责分离**：开发工具服务于开发者
- ✅ **简洁优于复杂**：避免过度工程化
- ✅ **清晰沟通**：通过文档和错误消息说明设计意图

---

**结论**：这是一个经过深思熟虑的设计决策，平衡了实用性、可维护性和用户体验。
