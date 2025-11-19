# SAGE 权限管理指南 (Permission Management Guide)

本文档详细说明了 SAGE 安装和使用过程中的权限需求，以及如何在不同环境下安全且有效地管理权限。

## 📋 目录

- [概述](#%E6%A6%82%E8%BF%B0)
- [权限需求分类](#%E6%9D%83%E9%99%90%E9%9C%80%E6%B1%82%E5%88%86%E7%B1%BB)
- [详细权限说明](#%E8%AF%A6%E7%BB%86%E6%9D%83%E9%99%90%E8%AF%B4%E6%98%8E)
- [权限管理最佳实践](#%E6%9D%83%E9%99%90%E7%AE%A1%E7%90%86%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5)
- [受限环境部署](#%E5%8F%97%E9%99%90%E7%8E%AF%E5%A2%83%E9%83%A8%E7%BD%B2)
- [故障排除](#%E6%95%85%E9%9A%9C%E6%8E%92%E9%99%A4)

______________________________________________________________________

## 概述

SAGE 的安装和使用涉及多个不同的权限级别。为了提高安全性和灵活性，我们明确区分了各个步骤的权限需求。

### 权限级别

- **用户权限 (User)**：标准用户权限，无需特殊权限
- **Sudo 权限 (Sudo)**：需要使用 `sudo`，但用户账户必须在 sudoers 列表中
- **Root 权限 (Root)**：需要 root 用户身份（仅在必要时）

______________________________________________________________________

## 权限需求分类

### 1️⃣ Python 包安装 (User - 用户权限)

SAGE Python 包的安装可以完全在用户权限下进行。

| 步骤           | 权限级别 | 说明                           |
| -------------- | -------- | ------------------------------ |
| 创建虚拟环境   | User     | `python3 -m venv sage-env`     |
| 激活虚拟环境   | User     | `source sage-env/bin/activate` |
| 升级 pip       | User     | `pip install --upgrade pip`    |
| 安装 SAGE 包   | User     | `pip install isage[standard]`  |
| 导入 SAGE 模块 | User     | `import sage`                  |

**推荐方案**：始终使用虚拟环境（venv 或 conda）避免对系统 Python 的污染。

```bash
# ✅ 推荐：使用虚拟环境（完全用户权限）
python3 -m venv sage-env
source sage-env/bin/activate
pip install isage[standard]

# ⚠️ 不推荐：全局安装（需要 sudo）
sudo pip install isage[standard]  # 避免此方式
```

### 2️⃣ 系统依赖安装 (Sudo/Root - 需要特殊权限)

C++ 扩展编译需要系统依赖，这些步骤需要提升权限。

| 步骤         | 权限级别 | 说明             | 命令                                             |
| ------------ | -------- | ---------------- | ------------------------------------------------ |
| 安装编译工具 | Sudo     | gcc, cmake, make | `sudo apt-get install build-essential`           |
| 安装数学库   | Sudo     | BLAS, LAPACK     | `sudo apt-get install libblas-dev liblapack-dev` |
| 安装头文件   | Sudo     | Python 开发包    | `sudo apt-get install python3-dev`               |

**为什么需要 sudo？**

- 这些包安装在 `/usr/lib` 和 `/usr/include` 等系统目录
- 只有 root 用户有写入这些目录的权限

**最小化 sudo 使用的策略**：

```bash
# 1. 先检查是否已安装（避免不必要的 sudo）
gcc --version
cmake --version

# 2. 只安装缺失的依赖
./quickstart.sh --check-deps-only  # 仅检查，不安装

# 3. 批量安装所有依赖（一次 sudo）
sudo bash -c 'apt-get update && apt-get install -y build-essential cmake python3-dev'

# 4. 验证安装（用户权限）
pip install --dry-run isage[standard]
```

### 3️⃣ C++ 扩展编译 (User - 用户权限)

编译本身在用户权限下进行（前提是系统依赖已安装）。

```bash
# 用户权限下编译 C++ 扩展
pip install isage[standard]  # 自动编译

# 或手动重新编译
sage extensions install --force  # 用户权限
```

### 4️⃣ 文件系统操作 (Varies - 取决于目录权限)

| 操作              | 权限需求 | 解决方案                           |
| ----------------- | -------- | ---------------------------------- |
| 写入 `/home/user` | User     | 默认，无需特殊权限                 |
| 写入 `/opt`       | Sudo     | 安装到用户目录或使用 `--user` 标志 |
| 写入 `/etc`       | Sudo     | 修改配置文件需要权限               |
| 访问 GPU 设备     | Sudo     | 将用户加入 `docker` 或 `video` 组  |

______________________________________________________________________

## 详细权限说明

### 安装阶段的权限需求

#### 步骤 1: 系统检查（用户权限）

```bash
./quickstart.sh --check-system  # ✅ 用户权限
```

输出：系统是否满足 SAGE 要求

#### 步骤 2: 系统依赖安装（Sudo 权限）

```bash
# 方式 A: 由安装脚本自动处理
./quickstart.sh  # 脚本会在需要时请求 sudo

# 方式 B: 预先手动安装（推荐用于自动化）
sudo apt-get update
sudo apt-get install -y build-essential cmake python3-dev libblas-dev liblapack-dev

# 方式 C: 仅检查，不自动安装
./quickstart.sh --verify-system-deps
```

#### 步骤 3: Python 虚拟环境（用户权限）

```bash
python3 -m venv ~/sage-env  # ✅ 完全用户权限
source ~/sage-env/bin/activate
```

#### 步骤 4: 安装 SAGE（用户权限）

```bash
pip install isage[standard]  # ✅ 虚拟环境中的用户权限
```

### 运行时权限需求

#### 标准使用（用户权限）

```python
from sage.core.api import LocalEnvironment
env = LocalEnvironment()  # ✅ 用户权限
```

#### GPU 加速（可能需要特殊权限）

```python
# 如果使用 GPU，可能需要访问 `/dev/nvidia*`
# 解决方案：将用户加入 docker 组
sudo usermod -aG docker $USER
newgrp docker
```

#### 日志和缓存（用户权限）

```bash
# SAGE 的日志和缓存存储在用户主目录
ls ~/.cache/sage
ls ~/.local/share/sage
```

______________________________________________________________________

## 权限管理最佳实践

### ✅ 推荐做法

#### 1. 使用虚拟环境

```bash
# 创建隔离的 Python 环境
python3 -m venv ~/projects/sage-env

# 激活环境
source ~/projects/sage-env/bin/activate

# 在虚拟环境中安装
pip install isage[standard]
```

**优点**：

- 不污染系统 Python
- 无需 sudo
- 容易切换版本
- 便于团队协作

#### 2. 预先安装系统依赖

```bash
# 作为管理员一次性安装
sudo bash << 'EOF'
apt-get update
apt-get install -y \
    build-essential \
    cmake \
    python3-dev \
    libblas-dev \
    liblapack-dev
EOF

# 之后用户无需 sudo
```

#### 3. 使用 Conda（如果已安装）

```bash
# Conda 管理所有依赖（无需 sudo）
conda create -n sage python=3.11
conda activate sage
pip install isage[standard]  # 通常无需 sudo
```

#### 4. 明确的权限检查

```bash
# 在脚本中检查权限
if [ "$EUID" -ne 0 ]; then
    echo "此步骤需要 root 权限"
    sudo -E bash "$0"
    exit
fi
```

### ❌ 避免的做法

#### 1. ❌ 使用 `sudo pip`

```bash
# 不要这样做！
sudo pip install isage  # ❌ 污染系统 Python

# 改用虚拟环境
python3 -m venv env && source env/bin/activate && pip install isage  # ✅
```

#### 2. ❌ 过度使用 sudo

```bash
# 不要这样做
sudo bash quickstart.sh  # ❌ 整个脚本以 root 运行

# 改用混合模式（脚本在需要时请求 sudo）
./quickstart.sh  # ✅ 脚本会在需要时自动请求 sudo
```

#### 3. ❌ 将 root 权限写入脚本环境

```bash
# 不要这样做
SUDO_ASKPASS=/dev/null sudo -E bash script.sh  # ❌ 跳过密码提示

# 改用正常的 sudo 提示
sudo bash script.sh  # ✅ 正常的权限提示
```

#### 4. ❌ 为用户文件更改所有权

```bash
# 不要这样做
sudo chown root ~/.cache/sage  # ❌ 破坏用户权限

# 保持用户所有权
chown $USER:$USER ~/.cache/sage  # ✅
```

______________________________________________________________________

## 受限环境部署

### 企业网络（Corporate Networks）

在企业网络中，通常存在以下限制：

- 代理服务器要求
- 防火墙限制
- Sudo 权限限制

#### 解决方案

```bash
# 配置 pip 代理
pip install -i https://your-mirror.com/simple isage

# 或在 ~/.pip/pip.conf 中设置
[global]
index-url = https://your-mirror.com/simple

# 安装时使用信任主机
pip install --trusted-host your-mirror.com isage
```

### Air-Gapped 系统（完全离线）

在没有互联网连接的系统中：

```bash
# 1. 在有网络的系统上下载依赖
pip download -d ./deps isage[standard]

# 2. 传输到目标系统（使用 USB、SCP 等）
scp -r deps/ user@target:/tmp/

# 3. 在目标系统上离线安装
pip install --no-index --find-links /tmp/deps isage[standard]
```

### 无 Sudo 的系统

在无 sudo 权限的系统中：

```bash
# 1. 联系系统管理员预先安装系统依赖
# 需要安装：build-essential, cmake, libblas-dev, liblapack-dev

# 2. 使用用户级别的虚拟环境
python3 -m venv ~/.local/sage-env
source ~/.local/sage-env/bin/activate

# 3. 安装 SAGE（无需 sudo）
pip install isage[standard]

# 4. 配置环境变量
export PATH="$HOME/.local/sage-env/bin:$PATH"
```

______________________________________________________________________

## 故障排除

### 问题 1: `permission denied` 错误

**症状**：

```
permission denied: ./quickstart.sh
```

**解决方案**：

```bash
# 添加执行权限
chmod +x quickstart.sh
./quickstart.sh
```

### 问题 2: `sudo: no tty present`

**症状**：

```
sudo: no tty present and no -S option was specified
```

**原因**：脚本以非交互模式运行（如 cron、CI/CD）

**解决方案**：

```bash
# 方法 1：预授权（sudoers 配置）
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/apt-get" | sudo tee /etc/sudoers.d/sage

# 方法 2：提前安装依赖
sudo apt-get install -y build-essential cmake python3-dev

# 方法 3：使用容器（Docker）
docker run -it ubuntu:22.04 bash /path/to/quickstart.sh
```

### 问题 3: `can't write to /usr/local/lib`

**症状**：

```
error: can't create or remove files in /usr/local/lib
```

**原因**：试图在系统目录中安装 Python 包

**解决方案**：

```bash
# ✅ 使用虚拟环境
python3 -m venv ~/sage-env
source ~/sage-env/bin/activate
pip install isage

# ❌ 避免
sudo pip install isage  # 不要这样做
```

### 问题 4: GPU 访问权限不足

**症状**：

```
NVIDIA GPU not found / CUDA device not accessible
```

**原因**：用户无权访问 GPU 设备

**解决方案**：

```bash
# 将用户加入相关组
sudo usermod -aG docker $USER
sudo usermod -aG video $USER
newgrp docker  # 刷新组成员身份

# 验证
nvidia-smi
```

### 问题 5: Conda 环境权限问题

**症状**：

```
CondaError: Cannot unlink file
```

**原因**：Conda 环境中的文件权限不正确

**解决方案**：

```bash
# 修复 Conda 环境权限
conda clean --all
conda remove -n sage --all  # 删除问题环境
conda create -n sage python=3.11  # 重建
```

______________________________________________________________________

## 权限检查清单

在部署 SAGE 前，检查以下各项：

### 用户权限检查

- [ ] 用户可以创建虚拟环境
- [ ] 用户可以写入 `$HOME` 目录
- [ ] 用户可以执行 pip 安装

### Sudo 权限检查

- [ ] 用户在 sudoers 列表中
- [ ] 用户可以无密码运行必要的命令
- [ ] 用户可以访问 apt/yum/dnf

### 系统权限检查

- [ ] 系统依赖已安装（gcc, cmake 等）
- [ ] Python 开发包已安装
- [ ] 数学库已安装（BLAS, LAPACK）

### GPU 权限检查

- [ ] 用户可以访问 GPU 设备
- [ ] CUDA/cuDNN 正确安装
- [ ] NVIDIA 驱动已更新

______________________________________________________________________

## 安全建议

### 1. 最小权限原则 (Principle of Least Privilege)

> 仅为需要的操作授予最小必要权限。

```bash
# ✅ 好：只为系统包管理授予 sudo
sudo apt-get install -y build-essential

# ❌ 不好：为所有操作授予 sudo
sudo bash -c 'pip install && make && ...'
```

### 2. 定期审计权限

```bash
# 检查 sudoers 配置
sudo visudo -c

# 查看用户组
id

# 查看 sudo 权限
sudo -l
```

### 3. 避免密码存储

```bash
# ❌ 不要
echo "password" | sudo -S command

# ✅ 改用 SSH key 或预授权
ssh -i /path/to/key user@host "sudo command"
```

### 4. 日志记录

```bash
# 启用 sudo 日志记录
sudo grep sudo /var/log/auth.log

# 监控安装日志
pip install --log /tmp/pip-install.log isage
```

______________________________________________________________________

## 相关文档

- [SAGE 安装指南](../docs-public/docs_src/getting-started/installation.md)
- [安全安装指南](./SECURE_INSTALLATION_GUIDE.md)
- [离线安装指南](./OFFLINE_INSTALLATION.md)
- [故障排除指南](../docs/TROUBLESHOOTING.md)

______________________________________________________________________

## 获取帮助

如遇到权限相关问题，请：

1. 查看 [故障排除](#%E6%95%85%E9%9A%9C%E6%8E%92%E9%99%A4) 部分
1. 检查 [权限检查清单](#%E6%9D%83%E9%99%90%E6%A3%80%E6%9F%A5%E6%B8%85%E5%8D%95)
1. 联系 SAGE 社区
1. 提交 Issue 到 [GitHub Issues](https://github.com/intellistream/SAGE/issues)

______________________________________________________________________

**最后更新**：2025-11-15\
**版本**：1.0.0\
**维护者**：SAGE Team
