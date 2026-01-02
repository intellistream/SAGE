# Examples Testing Tools - PyPI Distribution Strategy

**Date**: 2025-10-27\
**Author**: Development Team\
**Summary**: Decision to position Examples testing tools as development-only features rather than
PyPI distribution\
**Status**: Implemented\
**Category**: Architecture Decision

## 📋 Summary

决定将 Examples 测试工具定位为"仅开发环境可用"的功能，而不是打包到 PyPI 分发。

## 🎯 Background

### 问题

SAGE 项目有一套完整的 Examples 测试工具（位于 `tools/tests/`），用于验证 `examples/` 目录中的示例代码。在将这些工具集成到 `sage-tools`
包时，面临一个关键问题：

**通过 PyPI 安装的包不包含 `examples/` 目录，导致测试工具无法运行。**

### 需求

1. 保持 Examples 测试工具的功能完整性
1. 不影响普通用户通过 PyPI 安装 `sage-tools`
1. 为开发者提供清晰的使用指引
1. 避免增加 PyPI 包的大小

## 🤔 Options Considered

### Option 1: 将 Examples 代码打包到 PyPI ❌

**方案**：在 `pyproject.toml` 中包含 examples 作为 package data

```toml
[tool.setuptools.package-data]
"sage.tools.examples_data" = [
    "tutorials/*.py",
    "apps/*.py",
]
```

**优点**：

- ✅ 从 PyPI 安装也能使用测试工具

**缺点**：

- ❌ 显著增加包大小（examples 目录可能有数百个文件）
- ❌ Examples 更新频繁，会导致 sage-tools 频繁发版
- ❌ 违背了工具和示例分离的原则
- ❌ 包含测试数据、配置文件等不适合分发的内容

**结论**：不可行

### Option 2: 运行时从 GitHub 下载 ❌

**方案**：首次使用时自动从 GitHub 下载 examples

```python
def ensure_examples_available():
    cache_dir = Path.home() / ".sage" / "examples"
    if not cache_dir.exists():
        download_from_github(...)
```

**优点**：

- ✅ PyPI 包保持小巧
- ✅ 可以从 PyPI 安装后使用

**缺点**：

- ❌ 需要网络连接
- ❌ 版本同步复杂（工具版本与 examples 版本）
- ❌ 下载缓存管理复杂
- ❌ 离线环境无法使用
- ❌ 增加代码复杂度

**结论**：过度设计

### Option 3: 定位为开发环境专用工具 ✅ (Chosen)

**方案**：

1. 工具只在开发环境中可用（需要克隆仓库）
1. 通过环境检测提供清晰的错误信息
1. 导入时警告，使用时报错

**优点**：

- ✅ 设计简洁，职责清晰
- ✅ 符合实际使用场景（开发者会克隆仓库）
- ✅ 不增加 PyPI 包大小
- ✅ 没有网络依赖
- ✅ 版本管理简单（与仓库同步）
- ✅ 错误信息清晰，易于理解

**缺点**：

- ⚠️ 从 PyPI 安装无法使用（但这是设计目标）

**结论**：**最佳方案** ⭐

### Option 4: 拆分为独立包 🤷

**方案**：创建独立的 `sage-examples-testing` 包

**优点**：

- ✅ 完全分离关注点

**缺点**：

- ❌ 增加包管理复杂度
- ❌ 依然面临 examples 目录的问题
- ❌ 对用户来说增加了安装步骤

**结论**：没有解决核心问题

## ✅ Decision

**选择 Option 3：定位为开发环境专用工具**

### 实施策略

#### 1. 环境检测机制

```python
def find_examples_directory() -> Optional[Path]:
    """按优先级查找 examples 目录"""
    # 1. SAGE_ROOT 环境变量
    # 2. 从当前目录向上查找
    # 3. 从包安装位置推断
    # 4. Git 仓库根目录
```

#### 2. 清晰的错误提示

```python
raise RuntimeError(
    "SAGE development environment not found.\n\n"
    "To use these tools:\n"
    "  1. Clone: git clone https://github.com/intellistream/SAGE\n"
    "  2. Install: pip install -e packages/sage-tools[dev]\n"
    "  3. Or set: export SAGE_ROOT=/path/to/SAGE\n"
)
```

#### 3. 分层错误处理

- **导入时**：只警告（warning），不阻止导入
- **使用时**：抛出详细错误，指导用户设置

#### 4. 文档说明

在多个地方明确说明：

- Package README
- Module docstring
- 错误消息
- 设计文档

## 📊 Impact Analysis

### 对普通用户

```bash
pip install isage-tools
# ✅ 正常安装
# ✅ 所有核心功能可用
# ⚠️ Examples 测试功能不可用（但他们不需要）
```

**影响**：无（他们不需要这个功能）

### 对开发者

```bash
git clone https://github.com/intellistream/SAGE
cd SAGE
pip install -e packages/sage-tools[dev]
# ✅ 所有功能可用
# ✅ 可以测试 examples
# ✅ 可以参与开发
```

**影响**：需要克隆仓库（本来就需要）

### 对 CI/CD

```yaml
- uses: actions/checkout@v3  # ✅ 已经克隆了仓库
- run: pip install -e packages/sage-tools[dev]
- run: sage-dev examples test  # ✅ 可以正常使用
```

**影响**：无（CI 总是克隆完整仓库）

## 🎯 Target Users

### 主要用户：SAGE 开发者和贡献者

- **场景**：开发、测试、PR review
- **环境**：总是克隆完整仓库
- **需求**：验证 examples 代码质量
- **满足度**：✅ 完全满足

### 次要用户：Documentation writers

- **场景**：编写和验证示例
- **环境**：克隆仓库编辑文档
- **需求**：测试示例是否可运行
- **满足度**：✅ 完全满足

### 非目标用户：End users

- **场景**：使用 SAGE 框架
- **环境**：通过 PyPI 安装
- **需求**：运行自己的代码
- **影响**：✅ 无影响（不需要这个功能）

## 📈 Benefits

### 简洁性 🎯

- 代码简单，易于维护
- 没有复杂的下载、缓存逻辑
- 职责清晰：开发工具服务于开发者

### 性能 ⚡

- PyPI 包保持小巧
- 无需网络下载
- 无需版本同步检查

### 可维护性 🔧

- Examples 更新不需要发布新版本
- 工具和示例代码在同一仓库，保持同步
- 测试数据和配置文件易于管理

### 用户体验 😊

- **开发者**：零额外配置（克隆仓库即可）
- **普通用户**：不受影响
- **错误提示**：清晰且可操作

## ⚠️ Risks and Mitigations

### Risk 1: 用户困惑

**风险**：用户可能不理解为什么某些功能需要开发环境

**缓解**：

- ✅ 在多处文档中说明
- ✅ 清晰的错误消息
- ✅ 在 README 中突出显示

### Risk 2: 环境检测失败

**风险**：某些边缘情况下无法找到 examples 目录

**缓解**：

- ✅ 多重检测机制（环境变量、向上查找、Git）
- ✅ 允许手动设置 SAGE_ROOT
- ✅ 详细的调试信息

### Risk 3: CI 环境配置

**风险**：某些 CI 环境可能配置特殊

**缓解**：

- ✅ 支持 SAGE_ROOT 环境变量
- ✅ Git 仓库自动检测
- ✅ 提供配置示例

## 🔄 Alternatives for Future

如果未来需求变化，可以考虑：

### 混合方案

- 基础测试框架在 PyPI 包中
- 实际测试需要开发环境
- 允许用户提供自己的 examples 目录

### 插件机制

- 核心工具在 PyPI
- Examples 通过插件加载
- 支持第三方 examples 集合

### 云端测试

- 提供在线测试服务
- 无需本地 examples
- 适合快速验证

**当前评估**：暂不需要，现有方案已足够

## 📝 Documentation

已创建以下文档：

1. **Module README** (`packages/sage-tools/src/sage/tools/dev/examples/README.md`)

   - 详细的使用指南
   - 环境设置说明
   - FAQ 和故障排除

1. **Package README 更新** (`packages/sage-tools/README.md`)

   - 安装说明区分 PyPI vs 源码
   - 特性列表标注开发环境需求

1. **Module Docstrings**

   - `__init__.py` 中的模块级文档
   - 清晰说明使用要求

1. **Error Messages**

   - 详细的错误信息
   - 可操作的解决步骤

## ✅ Implementation Checklist

- [x] 创建环境检测工具 (`utils.py`)
- [x] 实现友好的错误处理
- [x] 编写模块文档
- [x] 更新包 README
- [ ] 迁移核心代码 (analyzer, runner, suite)
- [ ] 创建 CLI 命令 (`sage-dev examples`)
- [ ] 编写单元测试
- [ ] 更新 CI/CD 配置
- [ ] 创建用户指南

## 🎓 Lessons Learned

1. **明确目标用户**：不是所有功能都需要对所有人可用
1. **职责分离**：开发工具应该服务于开发者
1. **简洁优于复杂**：避免过度工程化
1. **清晰的沟通**：通过文档和错误消息说明设计意图

## 🔗 Related Documents

- [SAGE Architecture](../../../../docs/dev-notes/architecture/)
- [Package Structure](../../../../README.md)
- [Examples Testing Tools](../examples/README.md)

## 📅 Review Schedule

- **每季度回顾**：检查这个决策是否仍然适用
- **用户反馈**：收集开发者和用户的使用体验
- **备选方案评估**：如果需求变化，重新评估

______________________________________________________________________

**结论**：将 Examples 测试工具定位为开发环境专用是最符合实际需求的设计，保持了代码的简洁性和可维护性，同时为目标用户（开发者）提供了良好的体验。
