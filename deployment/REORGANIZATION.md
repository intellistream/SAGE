# Deployment 文件夹重组说明

## 重组目的

为了更好地组织 deployment 文件夹中的文件，我们对文件结构进行了重新整理：
- Python 脚本移至 `app/` 文件夹
- Shell 脚本移至 `scripts/` 文件夹
- 更新所有相关的路径引用

## 新的文件结构

```
deployment/
├── sage_deployment.sh          # 主部署脚本（保持不变）
├── app/                        # Python 应用脚本
│   ├── jobmanager_controller.py
│   └── jobmanager_daemon.py
├── scripts/                    # Shell 脚本
│   ├── cli_manager.sh
│   ├── common.sh
│   ├── daemon_manager.sh
│   ├── health_checker.sh
│   ├── install_system.sh
│   ├── permission_manager.sh
│   ├── ray_manager.sh
│   ├── sage_jm_wrapper.sh
│   ├── system_utils.sh
│   └── uninstall_system.sh
├── config/                     # 配置文件
│   ├── default.conf
│   └── environment.sh
├── templates/                  # 模板文件
└── 文档文件                     # 保持不变
    ├── README.md
    ├── SIMPLIFIED_DEPLOYMENT.md
    └── SYSTEM_INSTALLATION.md
```

## 文件移动记录

### 移至 app/ 文件夹：
- `jobmanager_controller.py` → `app/jobmanager_controller.py`
- `jobmanager_daemon.py` → `app/jobmanager_daemon.py`

### 移至 scripts/ 文件夹：
- `sage_jm_wrapper.sh` → `scripts/sage_jm_wrapper.sh`
- `install_system.sh` → `scripts/install_system.sh`
- `uninstall_system.sh` → `scripts/uninstall_system.sh`

## 更新的路径引用

### sage_deployment.sh 中的更新：
1. `$SCRIPT_DIR/jobmanager_controller.py` → `$SCRIPT_DIR/app/jobmanager_controller.py`
2. `$SCRIPT_DIR/sage_jm_wrapper.sh` → `$SCRIPT_DIR/scripts/sage_jm_wrapper.sh`
3. `$SCRIPT_DIR/jobmanager_daemon.py` → `$SCRIPT_DIR/app/jobmanager_daemon.py`

### sage_jm_wrapper.sh 中的更新：
1. 开发环境下的控制器路径：`$(dirname "$SCRIPT_DIR")/app/jobmanager_controller.py`
2. 项目根目录计算：`$(dirname "$(dirname "$SCRIPT_DIR)")`

### cli_manager.sh 中的更新：
1. 控制器脚本路径：`$(dirname "$script_dir")/app/jobmanager_controller.py`

### daemon_manager.sh 中的更新：
1. Daemon 脚本路径：`$project_root/deployment/app/jobmanager_daemon.py`

### install_system.sh 中的更新：
1. 控制器脚本路径：`$SCRIPT_DIR/../app/jobmanager_controller.py`

## 兼容性

- **向后兼容**：已安装的系统级组件（`/usr/local/lib/sage/` 下的文件）不受影响
- **功能完整**：所有功能保持不变，包括系统级安装、CLI工具、守护进程管理等
- **路径自动解析**：脚本能自动检测是系统级安装还是开发环境，并使用正确的路径

## 优势

1. **更清晰的组织结构**：Python 脚本和 Shell 脚本分别存放
2. **更易维护**：相关功能的文件归类存放
3. **减少混乱**：主目录只保留最重要的部署脚本
4. **标准化结构**：符合常见的项目组织规范

## 使用方式

重组后的使用方式完全不变：

```bash
# 完整部署
./deployment/sage_deployment.sh

# 查看状态
./deployment/sage_deployment.sh status

# 启动系统
./deployment/sage_deployment.sh start

# 停止系统
./deployment/sage_deployment.sh stop
```

所有现有的功能和命令行接口保持不变。
