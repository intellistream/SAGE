# VS Code / Pylance 配置指南

## 问题描述

在 SAGE monorepo 中使用 VS Code 时，可能会遇到这样的错误：

```
Import "sage.platform.queue" could not be resolved
Pylance reportMissingImports
```

**注意**：这是 IDE 的**假阳性错误**，代码实际上可以正常运行：

```bash
$ python -c "from sage.platform.queue import RayQueueDescriptor; print('OK')"
OK  # ✅ 导入成功
```

## 根本原因

SAGE 采用 **monorepo** 结构，有 9 个独立的包：

```
packages/
├── sage-common/        (L1)
├── sage-platform/      (L2)
├── sage-kernel/        (L3)
├── sage-libs/          (L3)
├── sage-middleware/    (L4)
├── sage-apps/          (L5)
├── sage-benchmark/     (L5)
├── sage-studio/        (L6)
└── sage-tools/         (L6)
```

每个包都有自己的 `src/` 目录。Pylance 默认只会查找：
1. 工作区根目录
2. Python 环境的 site-packages

它**不会自动识别** monorepo 中的多个 src 目录。

## 解决方案

### 方案 1：pyrightconfig.json（已配置 ✅）

项目根目录已经包含 `pyrightconfig.json`，定义了每个包的执行环境和依赖路径。

**如果 Pylance 仍然报错**，尝试以下步骤：

1. **重新加载 VS Code 窗口**
   - `Ctrl+Shift+P` → "Developer: Reload Window"
   - 或者关闭并重新打开 VS Code

2. **重启 Pylance 语言服务器**
   - `Ctrl+Shift+P` → "Python: Restart Language Server"

3. **检查 Pylance 是否使用了配置**
   - 打开输出面板：`Ctrl+Shift+U`
   - 选择 "Python Language Server"
   - 查看是否加载了 pyrightconfig.json

### 方案 2：VS Code 用户设置（可选）

如果方案 1 不起作用，在 `.vscode/settings.json` 中添加：

```json
{
  "python.analysis.extraPaths": [
    "${workspaceFolder}/packages/sage-common/src",
    "${workspaceFolder}/packages/sage-platform/src",
    "${workspaceFolder}/packages/sage-kernel/src",
    "${workspaceFolder}/packages/sage-libs/src",
    "${workspaceFolder}/packages/sage-middleware/src",
    "${workspaceFolder}/packages/sage-apps/src",
    "${workspaceFolder}/packages/sage-benchmark/src",
    "${workspaceFolder}/packages/sage-studio/src",
    "${workspaceFolder}/packages/sage-tools/src"
  ],
  "python.analysis.autoSearchPaths": true,
  "python.analysis.diagnosticMode": "workspace"
}
```

**注意**：`.vscode/` 在 `.gitignore` 中，所以这是**本地配置**，不会提交到 git。

### 方案 3：降低错误级别（临时方案）

如果你不想看到这些警告，可以在 `.vscode/settings.json` 中添加：

```json
{
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "none"
  }
}
```

**不推荐**：这会隐藏所有导入错误，包括真正的问题。

## 验证配置是否生效

### 测试 1：命令行测试

```bash
# 在项目根目录
cd /home/shuhao/SAGE

# 测试导入
python -c "from sage.platform.queue import RayQueueDescriptor; print('✅ Import OK')"
python -c "from sage.kernel.api import LocalEnvironment; print('✅ Import OK')"
python -c "from sage.middleware.operators.rag import ChromaRetriever; print('✅ Import OK')"
```

如果这些都能成功，说明 Python 环境配置正确。

### 测试 2：VS Code 中测试

1. 在任意 Python 文件中输入：
   ```python
   from sage.platform.queue import RayQueueDescriptor
   ```

2. 将鼠标悬停在 `RayQueueDescriptor` 上

3. **如果配置正确**，你应该看到：
   - 类型提示
   - 文档字符串
   - 跳转定义（`F12`）可以工作

4. **如果配置不正确**，你会看到：
   - 红色波浪线
   - "Import could not be resolved"

## 为什么 .vscode/settings.json 不在 git 中？

`.vscode/` 目录包含**个人偏好设置**：
- 编辑器字体、主题
- 个人快捷键
- 本地路径（可能因用户而异）

为了避免配置冲突，我们使用：
- `pyrightconfig.json` - **项目级配置**（在 git 中）
- `.vscode/settings.json` - **个人配置**（不在 git 中）

## 常见问题

### Q1: 我修改了 pyrightconfig.json，但 Pylance 没有更新？

**A**: 重启 Pylance 语言服务器或重新加载窗口。

### Q2: 有些导入可以识别，有些不行？

**A**: 检查依赖方向。例如：
- ✅ `sage.kernel` → `sage.platform` （L3 → L2，正确）
- ❌ `sage.platform` → `sage.kernel` （L2 → L3，违反架构）

### Q3: 为什么在测试文件中更容易出现这个问题？

**A**: 测试文件通常会导入多个包。如果 Pylance 没有正确配置 extraPaths，它可能找不到某些包。

### Q4: 能否在每个包中单独打开 VS Code？

**A**: 可以，但**不推荐**：
```bash
# 不推荐
cd packages/sage-kernel
code .
```

**推荐**：始终在项目根目录打开：
```bash
# 推荐
cd /home/shuhao/SAGE
code .
```

这样 Pylance 可以看到整个 monorepo 结构。

### Q5: Ray Actor 相关的类型错误怎么办？

**问题示例**：
```python
@ray.remote
class MyActor:
    def my_method(self):
        pass

actor = MyActor.remote()  # ❌ Cannot access attribute "remote" for class "FunctionType"
result = actor.my_method.remote()  # ❌ Attribute "remote" is unknown
```

**原因**：Pylance 不知道 `@ray.remote` 装饰器会将类转换为 Ray Actor 类型。

**解决方案 A - 类型注释（推荐用于生产代码）**：
```python
from typing import TYPE_CHECKING
import ray

if TYPE_CHECKING:
    from ray.actor import ActorClass

@ray.remote
class MyActor:
    def my_method(self):
        pass

# 添加类型注释
actor: 'ActorClass[MyActor]' = MyActor.remote()
```

**解决方案 B - 类型忽略（推荐用于测试代码）**：
```python
actor = MyActor.remote()  # type: ignore[attr-defined]
result = actor.my_method.remote()  # type: ignore[attr-defined]
```

**解决方案 C - 全局配置（已在 pyrightconfig.json 中配置）**：
```json
{
  "reportAttributeAccessIssue": "warning",
  "reportCallIssue": "warning"
}
```

这会将这些错误降级为警告，不会影响开发体验。

### Q6: 字典取值的类型错误？

**问题示例**：
```python
info = {"operations_count": 10, "status": "ok"}
count = info["operations_count"]  # ❌ Argument of type "Literal['operations_count']" cannot be assigned
```

**原因**：Pylance 认为 `info` 的类型是 `dict[str, Any]`，但 `__getitem__` 期望 `slice` 类型（这是 Pylance 的一个已知问题）。

**解决方案 A - 使用 get() 方法**：
```python
count = info.get("operations_count", 0)  # ✅ 更安全
```

**解决方案 B - 类型断言**：
```python
from typing import cast
count = cast(int, info["operations_count"])
```

**解决方案 C - TypedDict（推荐用于固定结构）**：
```python
from typing import TypedDict

class QueueInfo(TypedDict):
    operations_count: int
    status: str

info: QueueInfo = {"operations_count": 10, "status": "ok"}
count = info["operations_count"]  # ✅ 类型正确
```

**解决方案 D - 全局配置（已在 pyrightconfig.json 中配置）**：
```json
{
  "reportArgumentType": "warning"
}
```

## 技术细节

### Monorepo 导入路径解析

当你写 `from sage.platform.queue import ...` 时：

1. **Python 运行时**：
   ```
   查找 site-packages/sage/platform/queue/
   ↓
   找到 /path/to/env/lib/python3.11/site-packages/sage/platform/
   ↓
   ✅ 导入成功（因为包已安装）
   ```

2. **Pylance（没有配置）**：
   ```
   查找 workspace_root/sage/platform/queue/
   ↓
   找不到（因为实际在 packages/sage-platform/src/sage/platform/）
   ↓
   ❌ 报告 "Import could not be resolved"
   ```

3. **Pylance（有配置）**：
   ```
   查找 extraPaths 中的路径
   ↓
   在 packages/sage-platform/src/ 中找到 sage/platform/
   ↓
   ✅ 识别成功
   ```

### 为什么使用 executionEnvironments？

`pyrightconfig.json` 中的 `executionEnvironments` 定义了每个包的依赖关系：

```json
{
  "root": "packages/sage-kernel/src",
  "extraPaths": [
    "packages/sage-common/src",
    "packages/sage-platform/src"
  ]
}
```

这告诉 Pylance：
- 当分析 `sage-kernel` 中的代码时
- 可以导入 `sage.common` 和 `sage.platform`
- **但不能**导入 `sage.middleware`（因为那是 L4，违反 L3 → L4 依赖）

这样可以在 IDE 中**强制架构约束**！

## 相关文档

- [架构文档](./PACKAGE_ARCHITECTURE.md) - 包层级和依赖规则
- [Python Environment Setup](./INSTALLATION_GUIDE.md) - Python 环境配置
- [Pylance 官方文档](https://github.com/microsoft/pylance-release)

## 总结

✅ **已配置**：`pyrightconfig.json` 已经在项目根目录

🔧 **需要做的**：
1. 重启 VS Code 或 Pylance
2. 如果仍有问题，创建本地 `.vscode/settings.json`

💡 **记住**：如果代码能运行，只是 Pylance 报错，那就是配置问题，不是代码问题！
