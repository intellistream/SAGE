# SAGE Shell Library

`tools/lib` 集中存放可复用的 Shell 脚本模块，供 `tools/conda`、`tools/maintenance` 等运维工具共享使用。

## 模块清单

- `logging.sh`：统一的彩色日志输出与终端交互助手。
- `config.sh`：运维脚本可复用的环境变量配置项。
- `common_utils.sh`：常见的 Shell 工具函数集合（目录、文件、网络检测等）。

## 使用方式

在 Bash 脚本中根据自身目录结构引用对应模块，例如：

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/logging.sh"
source "$SCRIPT_DIR/../lib/common_utils.sh"
```

所有模块均兼容从仓库根目录或模块子目录执行，路径解析基于脚本当前位置计算。
