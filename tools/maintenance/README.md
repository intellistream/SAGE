# SAGE Maintenance Tools

SAGE 元仓库的轻量维护工具文档。

当前 `tools/maintenance/` 目录只保留仍在使用的项目维护脚本，不再承担历史上的 submodule 编排职责。SAGE 生态中的大多数组件已经拆分为独立仓库并单独发布，因此这里的工具主要用于当前元仓库本身的清理、检查、hooks 和类型问题辅助处理。

> 完整开发说明请参考：
>
> - [DEVELOPER.md](../../DEVELOPER.md)
> - [CONTRIBUTING.md](../../CONTRIBUTING.md)

## 快速开始

```bash
# 查看帮助
./tools/maintenance/sage-maintenance.sh --help

# 运行健康检查
./tools/maintenance/sage-maintenance.sh doctor

# 清理构建产物与缓存
./tools/maintenance/sage-maintenance.sh clean
```

## 当前支持的命令

### 项目维护

| 命令 | 说明 |
| --- | --- |
| `clean` | 清理常见构建产物与缓存 |
| `clean-deep` | 深度清理 Python 缓存、日志和构建目录 |
| `security-check` | 检查配置中的敏感信息 |
| `setup-hooks` | 安装或重装 Git hooks |
| `doctor` | 运行健康检查 |
| `status` | 显示当前仓库状态 |

### 类型问题辅助

| 命令 | 说明 |
| --- | --- |
| `typecheck status` | 查看当前类型错误状态 |
| `typecheck show-new` | 查看格式化后新增错误 |
| `typecheck explain <file>` | 解释某个文件的类型修复背景 |
| `typecheck safe-commit` | 以更安全的方式执行提交流程 |
| `typecheck reset` | 撤销相关自动格式化结果 |

## 目录结构

```text
tools/maintenance/
├── sage-maintenance.sh      # 主入口
├── setup_hooks.sh           # Git hooks 安装脚本
├── check_docs.sh            # 文档检查辅助脚本
├── fix-types-helper.sh      # 类型问题辅助脚本
├── git-hooks/               # Hook 模板
└── helpers/                 # 内部辅助脚本
   ├── check_config_security.sh
   ├── common.sh
   ├── pre_install_cleanup.sh
   ├── prepare_branch_checkout.sh
   ├── quick_cleanup.sh
   └── sage-jobmanager.sh
```

## 关于子仓库 / 独立仓库

- 历史 split repos 属于主仓收敛过程中的过渡边界；新增核心能力应优先直接落在 `SAGE` 主仓。
- `sage-tools` 等非核心能力仍可保持独立维护。
- 不要再假设存在历史上的嵌套路径，例如 `packages/.../sage_db/sageVDB/`、`packages/.../sage_flow/sageFlow/` 或 `packages/sage-llm-core/...`。

如果需要跨仓库协作，应优先判断该能力是否已经进入主仓收敛范围；若是，则直接在主仓实现，
不要继续扩大核心 split-repo 面。

## 常见用法

### 1. 健康检查

```bash
./tools/maintenance/sage-maintenance.sh doctor
```

适用于快速确认：

- 当前目录是否为 Git 仓库
- Git hooks 是否已安装
- Python 是否可用
- 仓库中是否残留构建产物

### 2. 日常清理

```bash
./tools/maintenance/sage-maintenance.sh clean
./tools/maintenance/sage-maintenance.sh clean-deep
```

### 3. 重新安装 hooks

```bash
./tools/maintenance/sage-maintenance.sh setup-hooks -f
```

### 4. 文档检查

```bash
bash tools/maintenance/check_docs.sh
```

### 5. 类型问题辅助

```bash
./tools/maintenance/sage-maintenance.sh typecheck status
./tools/maintenance/sage-maintenance.sh typecheck show-new
```

## 注意事项

1. 优先通过 `sage-maintenance.sh` 调用维护能力，不要直接调用 `helpers/` 中的脚本。
2. 当前 README 仅描述现存且仍受支持的维护命令。
3. 若遇到环境或仓库状态问题，先运行 `doctor`。
4. SAGE 为 polyrepo 架构，跨仓库开发请在对应独立仓库中进行，不要把子仓库实现重新放回元仓库。

## 相关文档

- [DEVELOPER.md](../../DEVELOPER.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)

💡 建议：维护前先运行 `doctor`，清理后再运行项目级质量检查。
