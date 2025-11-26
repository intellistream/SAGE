# SAGE 安装检查点系统

## 概述

检查点系统（Checkpoint System）提供了 SAGE 安装过程的进度保存、断点续传和自动回滚功能，确保在安装失败或中断时能够快速恢复。

## 核心功能

### 1. 进度保存

- 自动记录每个安装阶段的完成状态
- 保存安装配置和环境信息
- 生成唯一的安装 ID 用于追踪

### 2. 断点续传

- 检测上次未完成的安装
- 从中断点继续安装
- 跳过已完成的阶段

### 3. 自动回滚

- 安装失败时自动回滚到上一个检查点
- 备份关键配置文件
- 生成回滚脚本用于手动恢复

## 文件结构

```
.sage/checkpoints/
├── install_progress.json    # 安装进度记录
├── backups/                 # 配置文件备份
│   ├── requirements_*.txt
│   └── pyproject_*.toml
└── rollback.sh             # 自动生成的回滚脚本
```

## 安装阶段

系统将安装过程分为以下阶段：

1. **environment_setup** - 环境设置
1. **submodule_sync** - 子模块同步
1. **python_deps** - Python 依赖安装
1. **sage_packages** - SAGE 包安装
1. **verification** - 安装验证
1. **cleanup** - 清理工作

## 使用方法

### 基本用法

检查点系统在 `quickstart.sh` 和 `manage.sh` 中自动集成，无需手动调用。

### 查看安装进度

```bash
# 查看当前安装状态
cat .sage/checkpoints/install_progress.json | python3 -m json.tool
```

### 断点续传

如果安装中断，重新运行安装命令即可自动续传：

```bash
./quickstart.sh --standard --yes
```

系统会自动检测并提示：

```
🔍 检测到未完成的安装
   安装 ID: 20251115_143000
   当前阶段: python_deps
   已完成: environment_setup, submodule_sync

⚡ 是否从断点继续安装？[Y/n]
```

### 手动回滚

如果需要手动回滚到之前的状态：

```bash
# 运行自动生成的回滚脚本
bash .sage/checkpoints/rollback.sh

# 或使用清理命令
./manage.sh clean-env
```

## 进度文件格式

`install_progress.json` 包含以下信息：

```json
{
    "install_id": "20251115_143000",
    "start_time": "2025-11-15T14:30:00+08:00",
    "current_phase": "python_deps",
    "completed_phases": [
        "environment_setup",
        "submodule_sync"
    ],
    "failed_phases": [],
    "install_mode": "standard",
    "environment_name": ".sage/venv",
    "python_path": "/usr/bin/python3.11",
    "backup_created": true,
    "can_rollback": true,
    "last_update": "2025-11-15T14:35:00+08:00"
}
```

## API 函数

检查点系统提供以下函数（在 `tools/install/fixes/checkpoint_manager.sh` 中）：

### init_checkpoint_system()

初始化检查点系统，创建必要的目录和文件。

```bash
source tools/install/fixes/checkpoint_manager.sh
init_checkpoint_system
```

### update_checkpoint(phase, status, [additional_data])

更新检查点状态。

**参数：**

- `phase` - 安装阶段名称
- `status` - 状态：`started`, `completed`, `failed`
- `additional_data` - 可选的附加数据

**示例：**

```bash
update_checkpoint "python_deps" "started"
update_checkpoint "python_deps" "completed"
update_checkpoint "python_deps" "failed" "Package installation failed"
```

### check_resume_install()

检查是否有未完成的安装，返回检测结果。

```bash
if check_resume_install; then
    echo "检测到未完成的安装"
fi
```

### create_rollback_point(description)

创建回滚点，备份当前配置。

```bash
create_rollback_point "Before installing vLLM"
```

### execute_rollback()

执行回滚操作，恢复到上一个检查点。

```bash
execute_rollback
```

## 与安装脚本集成

### 在 quickstart.sh 中的用法

```bash
#!/bin/bash
source tools/install/fixes/checkpoint_manager.sh

# 初始化检查点系统
init_checkpoint_system

# 开始安装
update_checkpoint "environment_setup" "started"
# ... 执行环境设置 ...
update_checkpoint "environment_setup" "completed"

# 下一阶段
update_checkpoint "python_deps" "started"
if ! install_python_deps; then
    update_checkpoint "python_deps" "failed" "Dependency installation failed"
    exit 1
fi
update_checkpoint "python_deps" "completed"
```

### 错误处理

```bash
trap 'handle_install_error $LINENO' ERR

handle_install_error() {
    local line=$1
    echo "❌ 安装失败于第 $line 行"

    # 更新检查点状态
    update_checkpoint "$current_phase" "failed" "Error at line $line"

    # 询问是否回滚
    read -p "是否回滚到上一个检查点？[y/N] " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        execute_rollback
    fi
}
```

## 高级功能

### 1. 多次安装追踪

系统支持追踪多次安装，每次安装有唯一 ID：

```bash
# 查看所有安装记录
ls -la .sage/checkpoints/backups/
```

### 2. 备份管理

系统会自动备份：

- requirements.txt
- pyproject.toml
- 虚拟环境配置

### 3. 智能恢复

系统能够智能判断是否可以安全恢复：

- 检查环境一致性
- 验证备份完整性
- 确认依赖状态

## 配置选项

可以通过环境变量配置检查点系统：

```bash
# 禁用检查点系统（不推荐）
export SAGE_DISABLE_CHECKPOINT=1

# 自定义检查点目录
export SAGE_CHECKPOINT_DIR="/custom/path/checkpoints"

# 自动续传（不提示）
export SAGE_AUTO_RESUME=1
```

## 故障排查

### 问题：检查点文件损坏

```bash
# 删除损坏的检查点文件
rm -rf .sage/checkpoints/

# 重新初始化
source tools/install/fixes/checkpoint_manager.sh
init_checkpoint_system
```

### 问题：无法恢复安装

```bash
# 清理所有检查点和备份
./manage.sh clean-env

# 重新开始全新安装
./quickstart.sh --standard --yes
```

### 问题：回滚脚本无法执行

```bash
# 检查权限
chmod +x .sage/checkpoints/rollback.sh

# 手动执行
bash -x .sage/checkpoints/rollback.sh
```

## 最佳实践

1. **不要手动编辑检查点文件** - 使用提供的 API 函数
1. **定期清理旧检查点** - 使用 `./manage.sh clean-env`
1. **在关键操作前创建回滚点** - 使用 `create_rollback_point()`
1. **保留安装日志** - 检查点系统会记录时间戳，配合日志使用

## 性能影响

- 检查点更新：< 100ms
- 备份创建：< 500ms
- 恢复检查：< 50ms

对安装过程的性能影响可以忽略不计。

## 安全性

- 检查点文件仅包含配置信息，不包含敏感数据
- 备份文件存储在本地 `.sage/checkpoints/` 目录
- 建议将 `.sage/` 添加到 `.gitignore`

## 未来改进

- [ ] 支持并行安装的检查点管理
- [ ] 云端检查点同步
- [ ] 检查点压缩和归档
- [ ] 可视化安装进度界面

## 参考

- 实现代码：`tools/install/fixes/checkpoint_manager.sh`
- 测试用例：`tools/install/tests/test_checkpoint_system.sh`
- 相关文档：`docs/TROUBLESHOOTING.md`
