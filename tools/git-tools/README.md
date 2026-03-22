# Git Repository Tools

本目录只保留仍对当前 SAGE 主仓有用的 Git 仓库辅助脚本。

当前保留项：

1. `configure-git.sh`

## `configure-git.sh`

用于为当前仓库设置适合大仓库开发的 Git 本地配置，包括：

1. 提高 rename limit，降低大规模重命名时的误判
2. 启用 `core.preloadindex` 等性能相关设置
3. 配置适度的 credential cache

典型调用方式：

```bash
./tools/git-tools/configure-git.sh
```

该脚本会被开发安装流程按需调用，因此通常不需要手动执行。
