# sageTSDB Quick Reference

## 🚀 快速开始

### 初始化 sageTSDB 仓库并推送

```bash
# 1. 运行设置脚本
cd /home/shuhao/SAGE/packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
./setup_repo.sh

# 2. 在 GitHub 创建 sageTSDB 仓库
# 访问 https://github.com/intellistream，创建新仓库 'sageTSDB'

# 3. 推送代码
git push -u origin main
```

### 将 sageTSDB 设置为 SAGE 的 submodule

```bash
# 1. 移除当前目录
cd /home/shuhao/SAGE
rm -rf packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Prepare for sageTSDB submodule"

# 2. 添加 submodule
git submodule add https://github.com/intellistream/sageTSDB.git \
    packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB

# 3. 提交
git add .gitmodules packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Add sageTSDB as submodule"
git push
```

## 🔧 常用命令

### 构建 C++ 核心

```bash
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
./build.sh              # 构建
./build.sh --test       # 构建+测试
./build.sh --install    # 构建+安装
```

### 更新 sageTSDB

```bash
# 在 sageTSDB 目录
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git add .
git commit -m "Update feature"
git push origin main

# 在 SAGE 根目录
cd /home/shuhao/SAGE
git add packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git commit -m "Update sageTSDB submodule"
git push
```

### Submodule 管理

```bash
# 初始化 submodules
git submodule update --init --recursive

# 更新 submodule 到最新版本
git submodule update --remote

# 查看 submodule 状态
git submodule status

# 在 submodule 中切换分支
cd packages/sage-middleware/src/sage/middleware/components/sage_tsdb/sageTSDB
git checkout main
```

## 📂 文件位置

| 内容 | 路径 |
|------|------|
| C++ 头文件 | `sageTSDB/include/sage_tsdb/` |
| C++ 实现 | `sageTSDB/src/` |
| CMake 配置 | `sageTSDB/CMakeLists.txt` |
| 构建脚本 | `sageTSDB/build.sh` |
| Python 服务层 | `python/` |
| 示例代码 | `examples/` |
| 主文档 | `README.md` |
| Submodule 设置 | `SUBMODULE_SETUP.md` |

## 🐛 故障排除

| 问题 | 解决方案 |
|------|---------|
| Submodule 为空 | `git submodule update --init --recursive` |
| Detached HEAD | `cd sageTSDB && git checkout main` |
| 构建失败 | 确保 submodule 已初始化，重新运行 `./build.sh` |
| 找不到头文件 | 检查 `sageTSDB/` 是否存在且有内容 |

## 📞 获取帮助

- 详细文档: [SUBMODULE_SETUP.md](SUBMODULE_SETUP.md)
- 问题反馈: https://github.com/intellistream/SAGE/issues
- 邮件: shuhao_zhang@hust.edu.cn
