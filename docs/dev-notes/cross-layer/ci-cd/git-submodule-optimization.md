# Git Submodule 克隆速度优化

**Date**: 2025-11-11  
**Author**: SAGE Development Team  
**Summary**: Git submodule cloning speed optimization guide with parallel fetching and shallow cloning  
**Type**: Performance Optimization  
**Status**: Completed  
**Related**: CI/CD Pipeline, Installation Process

---

## 🐌 问题

在克隆 SAGE 项目时，submodule 克隆速度很慢，主要原因：

1. **串行克隆**：默认一个接一个地克隆 8 个子仓库
2. **完整历史**：克隆完整的 Git 历史记录，数据量大
3. **网络延迟**：国内访问 GitHub 速度较慢

## ⚡ 优化方案

### 自动优化（推荐）

现在 SAGE 安装脚本已自动应用以下优化：

```bash
./quickstart.sh  # 自动应用所有优化
```

### 手动优化

如果需要手动优化 Git 配置：

```bash
# 1. 应用 Git 优化配置
./tools/maintenance/optimize_git.sh

# 2. 手动克隆 submodules
./manage.sh
```

## 📊 优化效果

| 优化项 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| 克隆方式 | 串行 | 4 线程并行 | ~4x |
| 历史深度 | 完整历史 | 浅克隆 (depth=1) | ~10x |
| **总体速度** | **10-15 分钟** | **2-5 分钟** | **~3-5x** |

## 🔧 技术细节

### 并行克隆

```bash
git submodule update --init --recursive --jobs 4
```

- `--jobs 4`: 同时克隆 4 个仓库
- 根据 CPU 核心数自动调整

### 浅克隆

```bash
git submodule update --init --recursive --depth 1
```

- `--depth 1`: 只克隆最新的提交
- 大幅减少下载数据量（约 90%）

### Git 配置优化

```bash
# 本地仓库配置
git config --local submodule.fetchJobs 4        # 并行数
git config --local http.postBuffer 524288000   # 500MB 缓冲区
```

## 📝 注意事项

### 浅克隆的限制

使用 `--depth 1` 浅克隆后：

✅ **可以做**：
- 查看最新代码
- 进行开发和提交
- 推送更改

❌ **不能做**：
- 查看完整历史记录
- 执行某些需要完整历史的 Git 操作

### 转换为完整克隆

如果需要完整历史记录：

```bash
# 进入 submodule 目录
cd packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB

# 转换为完整克隆
git fetch --unshallow

# 返回主目录
cd -
```

## 🌐 网络优化建议

### 1. 使用 Git 镜像（国内推荐）

编辑 `.gitmodules`，将 GitHub URL 替换为镜像：

```bash
# 方法 1: 使用 gitee 镜像（如果有）
# 将 https://github.com/intellistream/xxx.git
# 改为 https://gitee.com/mirrors/xxx.git

# 方法 2: 使用 GitHub 代理
git config --global url."https://ghproxy.com/https://github.com".insteadOf "https://github.com"
```

### 2. 配置 HTTP 代理

如果有代理服务器：

```bash
# 设置代理
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy https://127.0.0.1:7890

# 取消代理
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 3. 使用 SSH 而不是 HTTPS

```bash
# 配置 SSH 密钥后，修改 submodule URL
git config --file=.gitmodules submodule.<name>.url git@github.com:intellistream/<repo>.git
git submodule sync
```

## 🔍 故障排查

### 克隆卡住不动

1. **检查网络连接**：
   ```bash
   ping github.com
   curl -I https://github.com
   ```

2. **增加 HTTP 超时**：
   ```bash
   git config --local http.lowSpeedLimit 0
   git config --local http.lowSpeedTime 999999
   ```

3. **使用代理或镜像**（见上文）

### 克隆失败

1. **清理并重试**：
   ```bash
   git submodule deinit -f --all
   rm -rf .git/modules/*
   ./manage.sh
   ```

2. **手动克隆单个 submodule**：
   ```bash
   git submodule update --init packages/sage-middleware/src/sage/middleware/components/sage_db/sageDB
   ```

## 📚 相关文档

- [Git Submodule 官方文档](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [Git 性能优化](https://git-scm.com/docs/git-config#Documentation/git-config.txt-submodulefetchJobs)

## 🆘 获取帮助

如果仍然遇到问题：

1. 查看 [SAGE 安装文档](../docs/installation.md)
2. 提交 [Issue](https://github.com/intellistream/SAGE/issues)
3. 联系开发团队
