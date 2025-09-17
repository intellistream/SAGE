# 脚本迁移说明

原有的 Shell 脚本已被新的 `sage studio` 命令替代：

## 旧脚本 → 新命令映射

### studio_manager.sh
- `./studio_manager.sh start` → `sage studio start`
- `./studio_manager.sh stop` → `sage studio stop`
- `./studio_manager.sh restart` → `sage studio restart`
- `./studio_manager.sh status` → `sage studio status`
- `./studio_manager.sh logs` → `sage studio logs`
- `./studio_manager.sh install` → `sage studio install`

### setup_frontend.sh
- 整个脚本功能 → `sage studio install`

### studio_demo.sh
已过时，使用新的命令：
- `sage studio --help` - 查看帮助
- `sage studio install` - 安装依赖
- `sage studio start` - 启动服务
- `sage studio status` - 检查状态

## 新的统一工作流程

```bash
# 1. 安装依赖（自动处理所有 npm 操作）
sage studio install

# 2. 启动服务
sage studio start

# 3. 检查状态
sage studio status

# 4. 在浏览器中打开
sage studio open

# 5. 构建生产版本
sage studio build

# 6. 停止服务
sage studio stop
```

所有操作现在都通过统一的 `sage studio` 命令完成，不再需要手动执行 npm 命令或管理脚本。