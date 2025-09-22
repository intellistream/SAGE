# SAGE 脚本配置文件
# 用于配置各个脚本模块的行为

# 日志配置
export SAGE_DEBUG=0                    # 设置为1启用调试日志
export SAGE_LOG_TIMESTAMP=0            # 设置为1启用时间戳

# Conda 配置
export SAGE_CONDA_PATH="$HOME/miniconda3"          # Miniconda 安装路径
export SAGE_ENV_NAME="sage"                        # 默认环境名称
export SAGE_PYTHON_VERSION="3.11"                  # 默认Python版本

# 项目配置
export SAGE_PROJECT_ROOT=""             # 项目根目录（自动检测）
export SAGE_AUTO_ACTIVATE_ENV=1         # 自动激活环境

# 网络配置
export SAGE_DOWNLOAD_TIMEOUT=300        # 下载超时时间（秒）
export SAGE_MIRROR_URL=""               # 镜像地址（可选）

# 安装选项
export SAGE_SKIP_DEPS_CHECK=0           # 跳过依赖检查
export SAGE_FORCE_REINSTALL=0           # 强制重新安装
