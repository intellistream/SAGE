# SAGE 开发者指南

本文档将指导您如何以 **开发者模式** 安装 SAGE 源码及其相关依赖，并开始贡献代码。

______________________________________________________________________

## *A*. 前置要求 (Prerequisites)

在开始之前，请确保您的开发环境满足以下要求：

- **操作系统**：Ubuntu 22.04+ / macOS / Windows (WSL2)
- **Python 版本**：Python 3.10+ （推荐 3.11）
- **Git**：用于版本控制
- **可选**：[Anaconda/Miniconda](https://www.anaconda.com/) 用于环境管理

### 克隆 SAGE 仓库

```bash
# 使用 SSH（推荐，需配置 SSH key）
git clone git@github.com:intellistream/SAGE.git
cd SAGE

# 或使用 HTTPS
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 切换到开发分支
git checkout main-dev
```

______________________________________________________________________

## *B*. 开发环境安装

### 方式 1：使用 quickstart.sh（推荐）

quickstart.sh 提供交互式和非交互式两种安装模式。

#### 交互式安装

```bash
./quickstart.sh
```

运行后会显示交互式菜单：

1. 选择安装模式（选择 **开发模式**）
1. 选择 Python 环境（Conda 或系统 Python）
1. 输入环境名称（如 `sage-dev`）
1. 确认并开始安装

#### 非交互式安装（自动化）

```bash
# 开发模式 + Conda 环境
./quickstart.sh --dev --yes

# 开发模式 + 系统 Python
./quickstart.sh --dev --pip --yes

# 开发模式 + vLLM 支持
./quickstart.sh --dev --vllm --yes
```

**开发模式特性**：

- ✅ 安装所有 SAGE 包（9 个包）
- ✅ 安装开发工具（pytest、pre-commit、ruff 等）
- ✅ 可编辑模式（`pip install -e`）- 代码修改即时生效
- ✅ 自动初始化 Git 子模块
- ✅ 配置 pre-commit hooks
- ✅ 自动安装代码质量检查工具（black、isort、ruff、mypy 等）
- ✅ 自动安装架构合规性检查工具

### 方式 2：手动安装

如果您希望手动控制安装过程：

```bash
# 1. 创建并激活虚拟环境
conda create -n sage-dev python=3.11
conda activate sage-dev

# 2. 初始化子模块（C++ 扩展依赖）
./tools/maintenance/sage-maintenance.sh submodule init

# 3. 安装 SAGE（开发模式）
pip install -e packages/sage[dev]

# 4. 安装 pre-commit hooks
pre-commit install

# 5. 编译 C++ 扩展
sage extensions install all
```

______________________________________________________________________

## *C*. 验证开发环境

### 1. 运行 Hello World 示例

```bash
python examples/tutorials/hello_world.py
```

预期输出：

```
HELLO, WORLD! #1
HELLO, WORLD! #2
...
HELLO, WORLD! #10
Hello World 批处理示例结束
```

### 2. 检查系统状态

```bash
sage doctor
```

该命令会检查：

- Python 版本和环境
- 已安装的 SAGE 包
- C++ 扩展状态
- 环境变量配置
- 开发工具（pytest、pre-commit 等）

### 3. 运行测试套件

```bash
# 运行所有测试
pytest

# 运行特定包的测试
pytest packages/sage-common/tests/
pytest packages/sage-kernel/tests/

# 运行并行测试（更快）
pytest -n auto

# 跳过慢速测试
pytest -m "not slow"
```

### 4. 检查代码格式

```bash
# 运行 pre-commit 检查（自动格式化）
pre-commit run --all-files

# 手动运行 ruff
ruff check .
ruff format .
```

______________________________________________________________________

## *D*. 开发工作流

### 1. 创建功能分支

```bash
# 从 main-dev 创建新分支
git checkout main-dev
git pull origin main-dev
git checkout -b feature/your-feature-name
```

### 2. 编写代码

SAGE 使用可编辑安装（`pip install -e`），您的代码修改会立即生效，无需重新安装。

**包结构**：

```
packages/
├── sage-common/      # 共享工具和配置
├── sage-kernel/      # 核心流处理引擎
├── sage-middleware/  # 服务和中间件
├── sage-libs/        # 高层库（RAG、Agent等）
├── sage-tools/       # CLI 和开发工具
├── sage-apps/        # 应用模板
├── sage-benchmark/   # 基准测试
├── sage-studio/      # 可视化工具
└── sage/            # 元包（入口）
```

### 3. 编写测试

遵循 pytest 约定：

```python
# packages/sage-common/tests/unit/test_feature.py
import pytest
from sage.common.your_module import YourClass


class TestYourFeature:
    def test_basic_functionality(self):
        obj = YourClass()
        assert obj.method() == expected_value

    @pytest.mark.slow
    def test_slow_operation(self):
        # 标记慢速测试
        pass
```

### 4. 运行测试

```bash
# 运行您修改的包的测试
pytest packages/sage-common/tests/ -v

# 运行特定测试
pytest packages/sage-common/tests/unit/test_feature.py::TestYourFeature::test_basic_functionality
```

### 5. 提交代码

```bash
# pre-commit 会自动运行两步检查
git add .
git commit -m "feat: add your feature description"

# 如果检查失败，修复后重新提交
git add .
git commit -m "feat: add your feature description"
```

**自动检查流程**：

提交代码时会自动运行两步检查（无需手动操作）：

**步骤 1：代码质量检查**

- ✅ **black** - 代码格式化（自动修复）
- ✅ **isort** - 导入语句排序（自动修复）
- ✅ **ruff** - 快速 Linter 检查（自动修复）
- ✅ **mypy** - 类型检查（需手动修复）
- ✅ **shellcheck** - Shell 脚本检查
- ✅ **detect-secrets** - 密钥泄露检查

**步骤 2：架构合规性检查**

- ✅ 检查包之间的依赖关系是否符合分层架构
- ✅ 检查导入路径是否正确（禁止跨层级导入）
- ✅ 检查是否使用了内部实现（禁止使用 `._internal`）
- ✅ 验证 `__layer__` 标记是否正确

**如果检查失败**：

```bash
# 1. 代码质量问题（black/isort/ruff）会自动修复
#    只需重新添加并提交：
git add .
git commit -m "feat: add your feature description"

# 2. 架构违规（如跨层级导入）需要手动修复：
#    查看错误信息，修改代码后重新提交
vim your_file.py  # 修复导入路径
git add .
git commit -m "feat: add your feature description"

# 3. 如果需要跳过检查（不推荐，仅紧急情况）：
git commit --no-verify -m "feat: your message"
```

**提交信息规范**：

- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `test:` - 测试相关
- `refactor:` - 代码重构
- `perf:` - 性能优化
- `chore:` - 构建/工具相关

### 6. 推送并创建 Pull Request

```bash
# 推送到远程仓库
git push origin feature/your-feature-name

# 在 GitHub 上创建 Pull Request
# 目标分支：main-dev
```

______________________________________________________________________

## *E*. C++ 扩展开发

如果您需要修改 C++ 扩展：

### 编译扩展

```bash
# 强制重新编译所有扩展
sage extensions install all --force

# 编译单个扩展
sage extensions install sage_db --force
```

### C++ 扩展位置

```
src/
├── sage_db/      # 向量数据库扩展
│   ├── bindings/ # Python 绑定
│   └── src/      # C++ 源码
└── sage_flow/    # 流式算子扩展
    ├── bindings/
    └── src/
```

### 调试 C++ 扩展

```bash
# 编译 Debug 版本
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)

# 使用 gdb 调试
gdb python
(gdb) run your_script.py
```

______________________________________________________________________

## *F*. 常见开发问题

### 问题 1：子模块初始化失败

**错误信息**：

```bash
fatal: unable to access 'https://github.com/intellistream/SAGE-Pub.git/':
Failed to connect to github.com port 443
```

**原因**：网络连接问题（GitHub 访问受限）

**解决方案**：

```bash
# 方案 1：使用代理
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy https://127.0.0.1:7890

# 方案 2：使用 SSH 而非 HTTPS
git config --global url."git@github.com:".insteadOf "https://github.com/"

# 重新初始化子模块
./tools/maintenance/sage-maintenance.sh submodule init
```

### 问题 2：C++ 扩展编译失败

**错误信息**：

```
CMake Error: CMake was unable to find a build program
```

**解决方案**：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential cmake git

# macOS
brew install cmake
xcode-select --install
```

### 问题 3：pre-commit 检查失败

**错误信息**：

```
ruff....................................................................Failed
```

**解决方案**：

```bash
# pre-commit 已自动格式化代码，重新添加并提交
git add .
git commit -m "your message"

# 如果需要跳过 pre-commit（不推荐）
git commit --no-verify -m "your message"
```

### 问题 4：测试失败

**错误信息**：

```
ModuleNotFoundError: No module named 'sage.xxx'
```

**原因**：包未正确安装或环境问题

**解决方案**：

```bash
# 重新安装开发环境
pip install -e packages/sage[dev]

# 检查安装状态
pip list | grep isage

# 运行 doctor 诊断
sage doctor
```

### 问题 5：导入路径错误

**错误信息**：

```
ImportError: attempted relative import with no known parent package
```

**原因**：相对导入路径问题

**解决方案**：

- 使用绝对导入：`from sage.common.xxx import YYY`
- 不要使用相对导入：`from ..xxx import YYY`（仅在包内部使用）

______________________________________________________________________

## *G*. CI/CD 开发指南

### GitHub Actions Workflow

SAGE 使用 GitHub Actions 进行 CI/CD：

```
.github/workflows/
├── ci.yml              # 主 CI/CD 流程（包含架构检查）
├── dev-ci.yml          # 开发分支 CI（main-dev）
└── release-ci.yml      # 发布分支 CI（main）
```

**CI 自动检查**：

提交 Pull Request 或 Push 代码时，CI 会自动运行：

1. **代码质量检查**（pre-commit hooks）
1. **单元测试**（pytest）
1. **架构合规性检查**（架构检查工具）
   - PR 模式：严格模式（`--strict`），任何违规都会失败
   - Push 模式：宽松模式，仅警告不阻止

**架构检查差异**：

- **本地 pre-commit**：检查所有暂存文件
- **CI Pull Request**：检查 PR 修改的文件（严格模式）
- **CI Push**：检查最近 5 次提交的文件（宽松模式）

### 本地模拟 CI 环境

```bash
# 运行与 CI 相同的测试
pytest -n auto -m "not slow" --ignore="packages/*/tests/pypi"

# 检查代码格式（CI 会检查）
pre-commit run --all-files

# 构建所有包
./scripts/dev.sh build

# 运行完整测试套件
./scripts/dev.sh test
```

### CI 缓存策略

SAGE CI 使用以下缓存来加速构建：

1. **pip 缓存**：Python 包缓存
1. **C++ 构建缓存**：编译产物缓存
1. **HuggingFace 模型缓存**：嵌入模型缓存

如需清除缓存，在 GitHub Actions 中手动删除缓存。

______________________________________________________________________

## *H*. 贡献指南

### 代码规范

1. **Python 代码**：

   - 遵循 PEP 8
   - 使用 ruff 进行格式化和 lint
   - 类型提示（推荐）：`def func(x: int) -> str:`
   - 文档字符串：使用 Google 风格

1. **测试覆盖率**：

   - 新功能必须包含测试
   - 单元测试覆盖率 > 80%
   - 集成测试覆盖核心流程

1. **提交信息**：

   - 使用 Conventional Commits 规范
   - 清晰描述修改内容和原因

### Pull Request 流程

1. Fork 仓库并创建功能分支
1. 编写代码和测试
1. 确保所有测试通过
1. 运行 pre-commit 检查
1. 提交 PR 到 `main-dev` 分支
1. 等待 Code Review
1. 根据反馈修改
1. 合并后删除分支

### 获取帮助

- **文档**：[SAGE 文档](https://intellistream.github.io/SAGE-Pub/)
- **Issue**：[GitHub Issues](https://github.com/intellistream/SAGE/issues)
- **社区**：
  - 微信群：参见 [COMMUNITY.md](../../docs/COMMUNITY.md)
  - QQ 群：IntelliStream 课题组讨论群
  - Slack：[加入 Slack](https://join.slack.com/t/intellistream/shared_invite/...)

______________________________________________________________________

## *I*. 下一步

- 📖 阅读 [架构文档](../code_intro/architecture.md)
- 🔧 查看 [开发命令参考](../../dev-notes/DEV_COMMANDS.md)
- 📝 浏览 [示例代码](https://github.com/intellistream/SAGE/tree/main-dev/examples)
- 🤝 参与 [社区讨论](../../docs/COMMUNITY.md)

祝您开发愉快！🚀

```
```
