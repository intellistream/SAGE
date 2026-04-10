# SAGE 安装一致性说明

本目录记录本地开发与 CI 安装路径应如何保持一致。当前规则很简单：优先使用仓库根目录的 `quickstart.sh`，并复用现有的非 venv Python 环境。

## 目标

- 本地与 CI 尽量复用同一安装入口
- 避免出现“CI 通过但本地失败”的安装偏差
- 遵守仓库的非 venv 约束

## 当前相关工具

### CI 包装器

文件：`tools/install/installers/ci_install_wrapper.sh`

```bash
./tools/install/installers/ci_install_wrapper.sh --dev --yes
```

该脚本在 CI 中包装 `quickstart.sh`，并记录安装日志。

### 安装验证工具

文件：`tools/install/installers/validate_installation.sh`

```bash
./tools/install/installers/validate_installation.sh
./tools/install/installers/validate_installation.sh --fix
./tools/install/installers/validate_installation.sh --strict --ci-compare
```

### Pre-commit 检查

文件：`tools/install/checks/installation_consistency_check.sh`

该检查通过 `.pre-commit-config.yaml` 中的 `installation-consistency-check` hook 接入。

当前触发范围与配置保持一致：

- `quickstart.sh`
- `tools/install/**/*.sh`
- `pyproject.toml`
- `.github/workflows/*.yml`

## 推荐工作流

### 本地开发

```bash
./quickstart.sh --dev --yes
./tools/install/installers/validate_installation.sh
sage-dev maintain hooks install
```

### CI

```yaml
- name: Install SAGE
  run: |
    chmod +x ./tools/install/installers/ci_install_wrapper.sh
    ./tools/install/installers/ci_install_wrapper.sh --dev --yes
```

## 约束

### 应该做的

- 始终以 `quickstart.sh` 作为主要安装入口
- 定期运行 `validate_installation.sh`
- 使用当前已配置的非 venv Python 环境，例如 Conda
- 在修改安装脚本或 workflow 后做一致性检查

### 不应该做的

- 不要创建新的 `venv` 或 `.venv`
- 不要在 SAGE 工作流中依赖活动的 Python venv
- 不要在 CI 中加入与本地完全不同的临时安装路径
- 不要混合使用多套互不一致的安装方式

## 排查建议

### CI 通过但本地失败

```bash
./tools/install/installers/validate_installation.sh --ci-compare
./quickstart.sh --doctor
ls -la .sage/logs 2>/dev/null || true
```

### 怀疑本地环境被手动安装污染

```bash
python -m pip uninstall isage -y
./quickstart.sh --dev --yes
./tools/install/installers/validate_installation.sh
```

### pre-commit 检查失败

```bash
pre-commit run installation-consistency-check --all-files
./tools/install/installers/validate_installation.sh --fix
```

## 参考文档

- [DEVELOPER.md](../../DEVELOPER.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [CHANGELOG.md](../../CHANGELOG.md)
