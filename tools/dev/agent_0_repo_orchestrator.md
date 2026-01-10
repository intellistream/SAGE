# Agent-0: Repository Orchestrator

## 🎯 任务目标

准备和管理所有独立仓库的创建、配置和分支策略。

## 📋 任务清单

### 1. 检查现有仓库状态

**已存在的仓库**（位于 /home/shuhao/）：

- ✅ sage-agentic（将扩展：合并 Intent, Reasoning, SIAS）
- ✅ sage-amms
- ✅ sage-rag
- ✅ sage-benchmark（独立，不属于 sage-libs）
- ✅ sage-examples（独立）
- ✅ sage-studio（独立）
- ✅ sage-team-info（独立）
- ✅ sage-pypi-publisher（工具）

**需要创建的仓库**（4 个）：

- [ ] sage-privacy
- [ ] sage-finetune
- [ ] sage-eval
- [ ] sage-safety（可选，P3 优先级）

**不需要创建的仓库**（功能合并）：

- ❌ sage-intent（合并到 sage-agentic）
- ❌ sage-reasoning（合并到 sage-agentic）
- ❌ sage-sias（合并到 sage-agentic）

### 2. 仓库创建脚本

```bash
#!/bin/bash
# tools/dev/create_sage_repos.sh

set -e

REPOS=(
    "sage-privacy:isage-privacy:Privacy protection, machine unlearning, differential privacy"
    "sage-finetune:isage-finetune:Model fine-tuning toolkit with LoRA, QLoRA, PEFT"
    "sage-eval:isage-eval:Evaluation metrics, profiling tools, and benchmarking"
    "sage-safety:isage-safety:Advanced safety guardrails and jailbreak detection (optional)"
)

HOME_DIR="/home/shuhao"
ORG="intellistream"

echo "🚀 创建 SAGE 独立仓库"
echo "===================="
echo ""

for repo_spec in "${REPOS[@]}"; do
    IFS=':' read -r repo_name pypi_name description <<< "$repo_spec"

    echo "📦 处理仓库: $repo_name"

    # 检查本地是否已存在
    if [ -d "$HOME_DIR/$repo_name" ]; then
        echo "  ⚠️  本地已存在: $HOME_DIR/$repo_name"
        cd "$HOME_DIR/$repo_name"

        # 检查远程仓库是否存在
        if gh repo view "$ORG/$repo_name" &>/dev/null; then
            echo "  ✅ 远程仓库已存在"
        else
            echo "  📤 创建远程仓库..."
            gh repo create "$ORG/$repo_name" \
                --private \
                --description "$description" \
                --source=. \
                --remote=origin \
                --push || true
        fi

        # 确保分支存在
        git checkout main 2>/dev/null || git checkout -b main
        git checkout main-dev 2>/dev/null || git checkout -b main-dev

        echo "  ✅ 分支已配置"
    else
        echo "  📥 克隆/创建仓库..."

        # 尝试克隆（如果远程已存在）
        if gh repo view "$ORG/$repo_name" &>/dev/null; then
            gh repo clone "$ORG/$repo_name" "$HOME_DIR/$repo_name"
        else
            # 创建新仓库
            mkdir -p "$HOME_DIR/$repo_name"
            cd "$HOME_DIR/$repo_name"
            git init

            # 创建基础文件
            cat > README.md << EOF
# $repo_name

$description

**PyPI Package**: \`$pypi_name\`

## Installation

\`\`\`bash
pip install $pypi_name
\`\`\`

## Development

\`\`\`bash
pip install -e .
\`\`\`

## License

Apache License 2.0
EOF

            cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
venv/
EOF

            git add .
            git commit -m "chore: initial commit"

            # 创建远程仓库
            gh repo create "$ORG/$repo_name" \
                --private \
                --description "$description" \
                --source=. \
                --remote=origin \
                --push
        fi

        cd "$HOME_DIR/$repo_name"

        # 确保分支存在
        git checkout main 2>/dev/null || git checkout -b main
        git push -u origin main 2>/dev/null || true

        git checkout -b main-dev 2>/dev/null || git checkout main-dev
        git push -u origin main-dev 2>/dev/null || true

        echo "  ✅ 仓库已创建并配置"
    fi

    echo ""
done

echo "✅ 所有仓库准备完成"
```

### 3. 配置 CI/CD 模板

为每个仓库创建基础 CI/CD：

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [main, main-dev]
  pull_request:
    branches: [main, main-dev]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e .[dev]

      - name: Run tests
        run: |
          pytest tests/ -v --cov

      - name: Run linters
        run: |
          ruff check .
          ruff format --check .
```

### 4. pyproject.toml 模板

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{pypi_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Apache-2.0"}
authors = [
    {name = "IntelliStream Team", email = "shuhao_zhang@hust.edu.cn"}
]
keywords = ["ai", "sage", "llm"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "isage-libs>=0.2.0",  # Interface layer
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.8.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://github.com/intellistream/{repo_name}"
Documentation = "https://sage.intellistream.com"
Repository = "https://github.com/intellistream/{repo_name}"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

### 5. 执行步骤

1. **运行仓库创建脚本**：

```bash
cd /home/shuhao/SAGE
bash tools/dev/create_sage_repos.sh
```

2. **验证所有仓库**：

```bash
for repo in sage-privacy sage-finetune sage-intent sage-reasoning sage-eval sage-sias; do
    echo "检查 $repo..."
    gh repo view intellistream/$repo
    ls -la /home/shuhao/$repo
done
```

3. **为现有仓库添加/更新分支**：

```bash
for repo in sage-agentic sage-amms sage-rag; do
    cd /home/shuhao/$repo
    git checkout main 2>/dev/null || git checkout -b main
    git checkout main-dev 2>/dev/null || git checkout -b main-dev
    git push -u origin main main-dev 2>/dev/null || true
done
```

## ✅ 完成标准

- [ ] 4 个新仓库已创建（GitHub + 本地）
- [ ] 每个仓库都有 main 和 main-dev 分支
- [ ] 每个仓库都有基础 README、.gitignore、pyproject.toml
- [ ] CI/CD 配置已添加
- [ ] 现有 sage-agentic 仓库已同步分支（准备合并 intent/reasoning/sias）

## 📤 输出

完成后提供仓库清单：

```
✅ sage-privacy: https://github.com/intellistream/sage-privacy
✅ sage-finetune: https://github.com/intellistream/sage-finetune
✅ sage-eval: https://github.com/intellistream/sage-eval
✅ sage-safety: https://github.com/intellistream/sage-safety (可选)
```

**注意事项**：

- sage-intent, sage-reasoning, sage-sias 不创建独立仓库
- 这些功能将作为 sage-agentic 的子模块
