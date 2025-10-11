# SAGE Tools 目录结构重组总结

## 重组日期
2025-10-07

## 重组目标
优化 `sage-tools` 包的目录结构，遵循模块化和单一职责原则，将管理器类移动到其对应的功能模块目录中。

## 重组内容

### 1. Studio Manager 重组
**移动文件：**
- `cli/managers/studio_manager.py` → `studio/studio_manager.py`

**更新导入：**
- `cli/commands/studio.py`: `from ..managers.studio_manager` → `from ...studio.studio_manager`
- `studio/__init__.py`: 添加了 `StudioManager` 的导出

**删除目录：**
- `cli/managers/` (空目录已删除)

### 2. 通用管理器重组
**移动文件：**
- `cli/config_manager.py` → `management/config_manager.py`
- `cli/deployment_manager.py` → `management/deployment_manager.py`

**创建新模块：**
- `management/__init__.py`: 导出 `ConfigManager`, `get_config_manager`, `DeploymentManager`

**更新导入：**
- `cli/commands/config.py`: `from ..config_manager` → `from ...management.config_manager`
- `cli/commands/cluster.py`: `from ..config_manager` → `from ...management.config_manager`
- `cli/commands/cluster.py`: `from ..deployment_manager` → `from ...management.deployment_manager`
- `cli/commands/head.py`: `from ..config_manager` → `from ...management.config_manager`
- `cli/commands/worker.py`: `from ..config_manager` → `from ...management.config_manager`
- `cli/commands/worker.py`: `from ..deployment_manager` → `from ...management.deployment_manager`
- `management/deployment_manager.py`: `from .config_manager` → `from .config_manager` (已正确)

### 3. Pipeline Blueprints 重组
**移动文件：**
- `cli/pipeline_blueprints.py` → `templates/pipeline_blueprints.py`

**更新模块导出：**
- `templates/__init__.py`: 添加了 `pipeline_blueprints` 的导入和导出

**更新导入：**
- `cli/commands/pipeline.py`: `from sage.tools.cli import pipeline_blueprints` → `from sage.tools import templates` 和 `from sage.tools.templates import pipeline_blueprints`

**移动测试文件：**
- `tests/cli/test_pipeline_blueprints.py` → `tests/templates/test_pipeline_blueprints.py`

## 重组后的目录结构

```
sage/tools/
├── cli/
│   ├── commands/           # CLI 命令定义
│   │   ├── config.py      # 使用 management.config_manager
│   │   ├── cluster.py     # 使用 management.config_manager, management.deployment_manager
│   │   ├── head.py        # 使用 management.config_manager
│   │   ├── worker.py      # 使用 management.config_manager, management.deployment_manager
│   │   ├── studio.py      # 使用 studio.studio_manager
│   │   └── pipeline.py    # 使用 templates.pipeline_blueprints
│   ├── core/              # CLI 核心功能
│   └── utils/             # CLI 工具函数
│
├── studio/                # Studio 功能模块
│   ├── __init__.py        # 导出 StudioManager
│   ├── studio_manager.py  # Studio 管理器
│   ├── frontend/          # 前端代码
│   ├── config/            # Studio 配置
│   └── data/              # Studio 数据
│
├── management/            # 通用管理功能模块（新增）
│   ├── __init__.py        # 导出 ConfigManager, DeploymentManager
│   ├── config_manager.py  # 配置管理器
│   └── deployment_manager.py  # 部署管理器
│
├── templates/             # 模板和蓝图模块
│   ├── __init__.py        # 导出模板相关功能和 pipeline_blueprints
│   ├── catalog.py         # 模板目录
│   └── pipeline_blueprints.py  # Pipeline 蓝图
│
├── enterprise/            # 企业版功能
├── dev/                   # 开发工具
├── finetune/              # 微调工具
├── license/               # 许可证管理
├── utils/                 # 通用工具
└── web_ui/                # Web UI

tests/
├── cli/                   # CLI 相关测试
│   ├── test_chat_pipeline.py
│   └── test_pipeline_builder.py
├── templates/             # 模板相关测试
│   ├── test_catalog.py
│   └── test_pipeline_blueprints.py  # 已移动到这里
└── ...
```

## 设计原则

1. **模块化原则**：每个功能模块（studio, management, templates）都有自己的目录
2. **单一职责原则**：管理器类放在其对应的功能模块中
3. **测试对齐原则**：测试文件的位置与被测试模块的位置对应
4. **清晰的依赖关系**：CLI commands 依赖各个功能模块，而不是在 CLI 目录中混合业务逻辑

## 优势

1. **更清晰的模块边界**：每个功能模块独立，职责明确
2. **更好的可维护性**：相关代码聚合在一起，易于理解和修改
3. **更好的可扩展性**：新增功能模块时，只需创建新目录，不会影响现有模块
4. **测试组织更合理**：测试文件位置与被测试代码位置对应，易于查找

## 验证状态

✅ 所有文件移动完成
✅ 所有导入路径已更新
✅ 测试文件已重新组织
✅ 无编译错误
✅ 模块导出已正确配置

## 后续建议

考虑是否需要进一步重组其他 CLI 相关文件，例如：
- `cli/core_cli.py` - 检查是否应该移到更合适的位置
- 其他可能的功能模块拆分
