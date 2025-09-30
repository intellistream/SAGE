# SAGE 工具脚本

本目录包含SAGE开发和演示相关的工具脚本。

## 脚本说明

## 可用脚本

- `common_utils.sh` - 通用 Shell 工具函数，供维护脚本复用
- `config.sh` - 环境配置变量与路径设置
- `logging.sh` - 统一的彩色日志输出封装

这些脚本会被 `tools/conda/` 与 `tools/maintenance/` 下的运维脚本加载，提供一致的日志与配置管理能力。