# SAGE 离线安装指南 (Offline Installation Guide)

本文档提供了在受限网络环境（企业网络、Air-Gapped 系统）中离线安装 SAGE 的完整指南。

## 📋 目录

- [概述](#%E6%A6%82%E8%BF%B0)
- [环境类型](#%E7%8E%AF%E5%A2%83%E7%B1%BB%E5%9E%8B)
- [企业网络安装](#%E4%BC%81%E4%B8%9A%E7%BD%91%E7%BB%9C%E5%AE%89%E8%A3%85)
- [Air-Gapped 系统安装](#air-gapped-%E7%B3%BB%E7%BB%9F%E5%AE%89%E8%A3%85)
- [离线包准备](#%E7%A6%BB%E7%BA%BF%E5%8C%85%E5%87%86%E5%A4%87)
- [离线依赖管理](#%E7%A6%BB%E7%BA%BF%E4%BE%9D%E8%B5%96%E7%AE%A1%E7%90%86)
- [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98)

______________________________________________________________________

## 概述

### 受限网络环境的常见场景

1. **企业网络**

   - 需要代理服务器访问互联网
   - 防火墙限制特定域名
   - 强制使用企业 PyPI 镜像
   - SSL/TLS 证书拦截

1. **Air-Gapped 系统**

   - 完全隔离，无互联网连接
   - 需要通过物理介质传输数据（USB、SCP 等）
   - 没有任何外部网络访问

1. **受限企业环境**

   - 无法使用 sudo 权限安装系统依赖
   - 限制使用特定工具和库
   - 严格的安全审计要求

______________________________________________________________________

## 环境类型

### 类型 1: 有代理的企业网络

```
┌─────────────────────┐
│  开发人员本地环境   │
│   (有网络连接)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌─────────────────┐
│   企业代理服务器    │◄────►│  PyPI 官方镜像  │
│  (HTTP/HTTPS)       │      │  或企业镜像     │
└──────────┬──────────┘      └─────────────────┘
           │
           ▼
┌─────────────────────┐
│  隔离服务器或桌面   │
│  (需要代理才能访问) │
└─────────────────────┘
```

### 类型 2: 完全 Air-Gapped 系统

```
┌─────────────────────┐
│  准备系统           │
│  (有网络连接)       │
│  1. 下载依赖        │
│  2. 创建离线包      │
└──────────┬──────────┘
           │ USB/SCP
           ▼
┌─────────────────────┐
│  Air-Gapped 系统    │
│  (完全隔离)         │
│  1. 离线安装        │
│  2. 验证安装        │
└─────────────────────┘
```

______________________________________________________________________

## 企业网络安装

### 步骤 1: 配置代理设置

#### 方式 A: 环境变量配置（推荐）

```bash
# 设置 HTTP/HTTPS 代理
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=https://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.company.com

# 如果需要代理认证
export HTTP_PROXY=http://username:password@proxy.company.com:8080
export HTTPS_PROXY=https://username:password@proxy.company.com:8080
```

#### 方式 B: Git 代理配置

```bash
# 如果使用 git clone SAGE 源码
git config --global http.proxy http://proxy.company.com:8080
git config --global https.proxy https://proxy.company.com:8080

# 仅为特定域名配置代理
git config --global http.https://github.com.proxy http://proxy.company.com:8080
```

#### 方式 C: pip 配置文件（~/.pip/pip.conf）

```ini
[global]
# 企业代理配置
proxy = [user:passwd@]proxy.company.com:8080

# 企业 PyPI 镜像
index-url = https://your-mirror.company.com/simple/

# 信任主机（避免 SSL 证书验证错误）
trusted-host =
    your-mirror.company.com
    mirrors.aliyun.com

# 连接超时设置（企业网络可能较慢）
timeout = 120
```

### 步骤 2: 虚拟环境设置

```bash
# 创建虚拟环境
python3 -m venv sage-env
source sage-env/bin/activate

# 升级 pip
pip install --upgrade pip --proxy "[user:passwd@]proxy.company.com:8080"

# 或使用配置文件（推荐）
pip install --upgrade pip
```

### 步骤 3: 使用企业镜像安装

#### 配置企业镜像源

```bash
# 如果企业有内部 PyPI 镜像
pip config set global.index-url https://your-mirror.company.com/simple/

# 信任企业镜像服务器
pip config set global.trusted-host your-mirror.company.com
```

#### 安装 SAGE

```bash
# 标准安装（使用企业镜像）
pip install isage[standard]

# 开发者安装
pip install -e .[dev]

# 或指定镜像
pip install -i https://your-mirror.company.com/simple/ isage[standard]
```

### 步骤 4: SSL 证书问题解决

如果企业 SSL 代理导致证书验证错误：

```bash
# ⚠️ 临时禁用 SSL 验证（仅在内部网络中，不安全）
pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org isage

# ✅ 推荐：添加企业证书
# 获取企业代理的 CA 证书
openssl s_client -connect proxy.company.com:8080 -showcerts > /tmp/ca.crt

# 配置 pip 使用该证书
pip install --cert /tmp/ca.crt isage

# 或永久配置在 ~/.pip/pip.conf
# [global]
# cert = /path/to/ca.crt
```

### 企业网络完整示例

```bash
#!/bin/bash
# SAGE 企业网络安装脚本

# 1. 设置代理
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=https://proxy.company.com:8080

# 2. 创建虚拟环境
python3 -m venv sage-env
source sage-env/bin/activate

# 3. 配置 pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
proxy = proxy.company.com:8080
index-url = https://your-mirror.company.com/simple/
trusted-host = your-mirror.company.com
timeout = 120
EOF

# 4. 安装依赖
pip install --upgrade pip setuptools wheel

# 5. 安装 SAGE
pip install isage[standard]

# 6. 验证安装
python3 -c "import sage; print(f'SAGE {sage.__version__} installed')"
```

______________________________________________________________________

## Air-Gapped 系统安装

### 场景: 完全离线环境

适用于：

- 国防、金融等高度受限环境
- 云平台无外网访问权限
- 内网测试环境

### 步骤 1: 在连网系统上准备离线包

#### 方式 A: 使用 pip download

```bash
# 在有网络的系统上执行

# 1. 创建下载目录
mkdir -p ~/sage-offline-packages

# 2. 下载 SAGE 及其所有依赖
pip download -d ~/sage-offline-packages isage[standard]

# 3. 查看下载的包（应包含数百个文件）
ls -lh ~/sage-offline-packages | head -20
wc -l ~/sage-offline-packages/*
```

#### 方式 B: 使用 requirements.txt

```bash
# 1. 生成 requirements.txt
pip freeze > sage-requirements.txt

# 2. 从 SAGE 源码中提取真实的依赖
# 或使用官方 requirements 文件
pip download -d ~/sage-offline-packages -r sage-requirements.txt

# 3. 创建依赖清单（用于验证）
ls ~/sage-offline-packages > packages-manifest.txt
```

#### 方式 C: 使用 pip-tools（推荐用于大型项目）

```bash
# 安装 pip-tools
pip install pip-tools

# 生成完整的依赖树
pip-compile requirements.in -o requirements.txt

# 下载所有依赖
pip download -d ~/sage-offline-packages -r requirements.txt
```

### 步骤 2: 打包离线文件

```bash
# 1. 创建压缩包
cd ~
tar -czf sage-offline-packages.tar.gz sage-offline-packages/

# 2. 计算校验和（用于验证完整性）
sha256sum sage-offline-packages.tar.gz > sage-offline-packages.tar.gz.sha256

# 3. 查看文件大小
du -sh sage-offline-packages.tar.gz
# 通常 SAGE standard 包约 200-300MB

# 4. 分割大文件（如果需要通过 USB 传输）
split -b 1G sage-offline-packages.tar.gz "sage-offline-packages.tar.gz.part"

# 生成分割清单
ls -lh sage-offline-packages.tar.gz.part* > split-manifest.txt
```

### 步骤 3: 传输到目标系统

#### 方式 A: USB 传输

```bash
# 源系统（有网络）
sudo cp sage-offline-packages.tar.gz /mnt/usb/
sudo cp sage-offline-packages.tar.gz.sha256 /mnt/usb/

# 目标系统（离线）
sudo mount /dev/sdX1 /mnt/usb
cp /mnt/usb/sage-offline-packages.tar.gz ~
cp /mnt/usb/sage-offline-packages.tar.gz.sha256 ~
```

#### 方式 B: SCP 传输

```bash
# 从有网络的系统传输到 Air-Gapped 系统
scp -P 2222 sage-offline-packages.tar.gz user@airgapped-system:/tmp/
scp -P 2222 sage-offline-packages.tar.gz.sha256 user@airgapped-system:/tmp/

# 如果需要分割传输
scp -P 2222 sage-offline-packages.tar.gz.part* user@airgapped-system:/tmp/
```

#### 方式 C: 离线介质（光盘、移动硬盘）

```bash
# 刻录到光盘或拷贝到移动硬盘
rsync -av sage-offline-packages.tar.gz /mnt/removable-media/

# 在目标系统上验证
sha256sum -c sage-offline-packages.tar.gz.sha256
```

### 步骤 4: 在目标系统上安装

#### 验证包完整性

```bash
# 验证文件未损坏
sha256sum -c sage-offline-packages.tar.gz.sha256

# 如果使用了分割文件，先重组
cat sage-offline-packages.tar.gz.part* > sage-offline-packages.tar.gz
sha256sum -c sage-offline-packages.tar.gz.sha256
```

#### 解压离线包

```bash
# 解压到临时目录
mkdir -p ~/offline-install
cd ~/offline-install
tar -xzf ../sage-offline-packages.tar.gz

# 或直接在 home 目录
tar -xzf ~/sage-offline-packages.tar.gz
```

#### 离线安装

```bash
# 1. 创建虚拟环境
python3 -m venv sage-env
source sage-env/bin/activate

# 2. 升级 pip
pip install --upgrade pip --no-index --find-links ~/sage-offline-packages

# 3. 安装 SAGE（完全离线）
pip install isage[standard] --no-index --find-links ~/sage-offline-packages

# 或使用完整路径
pip install isage[standard] \
  --no-index \
  --find-links /path/to/offline/packages \
  --no-deps
```

#### 完整离线安装脚本

```bash
#!/bin/bash
# Air-Gapped 系统离线安装脚本

set -e

# 配置
PACKAGES_DIR="$HOME/sage-offline-packages"
ENV_DIR="$HOME/sage-env"

echo "🔧 SAGE 离线安装..."

# 1. 验证离线包
echo "1️⃣  验证离线包..."
if [ ! -d "$PACKAGES_DIR" ]; then
    echo "❌ 离线包目录不存在: $PACKAGES_DIR"
    exit 1
fi

pkg_count=$(find "$PACKAGES_DIR" -type f | wc -l)
echo "   找到 $pkg_count 个离线包"

# 2. 创建虚拟环境
echo "2️⃣  创建虚拟环境..."
python3 -m venv "$ENV_DIR"
source "$ENV_DIR/bin/activate"

# 3. 升级 pip
echo "3️⃣  升级 pip..."
pip install --upgrade pip setuptools wheel \
  --no-index \
  --find-links "$PACKAGES_DIR" 2>/dev/null || true

# 4. 安装 SAGE
echo "4️⃣  安装 SAGE..."
pip install isage[standard] \
  --no-index \
  --find-links "$PACKAGES_DIR"

# 5. 验证安装
echo "5️⃣  验证安装..."
python3 -c "import sage; print(f'✅ SAGE {sage.__version__} 安装成功！')"

echo ""
echo "🎉 离线安装完成！"
echo "激活环境: source $ENV_DIR/bin/activate"
```

______________________________________________________________________

## 离线依赖管理

### 更新离线包

```bash
# 在有网络的系统上
pip download -d ~/sage-offline-packages --upgrade isage[standard]

# 生成新的清单
sha256sum sage-offline-packages/* > packages.sha256sum
```

### 管理多个版本

```bash
# 为不同版本创建独立目录
mkdir -p ~/offline-packages/{0.1.5,0.1.6,latest}

# 下载不同版本
pip download -d ~/offline-packages/0.1.5 isage[standard]==0.1.5
pip download -d ~/offline-packages/0.1.6 isage[standard]==0.1.6
```

### 依赖清单文件

```bash
# 生成可读的依赖清单
cat > packages-info.txt << 'EOF'
# SAGE 离线安装包清单
# 生成日期: 2025-11-15

## 核心包
- isage (SAGE 主包)
- numpy (数值计算)
- pandas (数据处理)
...

## 开发工具
- pytest (测试框架)
- black (代码格式化)
...

## 生成方式
pip download -d . isage[standard]
EOF
```

______________________________________________________________________

## 常见问题

### Q1: 离线包下载需要多长时间？

**A:** 取决于网络速度和包大小：

```bash
# 估算下载大小
pip download --dry-run isage[standard] 2>&1 | grep "Collecting"

# SAGE standard 通常需要：
# - 网络好: 5-10 分钟
# - 网络一般: 20-30 分钟
# - 包含 C++ 编译: 额外 10-20 分钟（编译库）
```

### Q2: 如何验证离线包的完整性？

**A:** 使用多种验证方法：

```bash
# 方式 1: 校验和验证
sha256sum -c packages.sha256sum

# 方式 2: 包数量验证
# 记录原始包数量
find ~/sage-offline-packages -type f | wc -l
# 传输后验证包数量相同

# 方式 3: 测试安装（在测试环境）
pip install isage[standard] --no-index --find-links ~/packages --dry-run
```

### Q3: 企业网络中 SSL 证书验证失败怎么办？

**A:** 几个解决方案（按推荐顺序）：

```bash
# 1. 添加企业 CA 证书（最安全）
pip install --cert /path/to/ca-bundle.crt isage

# 2. 信任特定主机（中等安全）
pip install --trusted-host your-mirror.com isage

# 3. 禁用 SSL 验证（最不安全，仅用于测试）
pip install --index-url http://your-mirror.com/simple isage
```

### Q4: 如何在 Air-Gapped 系统中更新 SAGE？

**A:** 重复准备和传输过程：

```bash
# 步骤 1: 在有网络的系统上下载新版本
pip download -d ~/sage-offline-packages --upgrade isage[standard]

# 步骤 2: 重新打包
tar -czf sage-offline-packages-new.tar.gz sage-offline-packages/

# 步骤 3: 传输到 Air-Gapped 系统
scp sage-offline-packages-new.tar.gz user@target:/tmp/

# 步骤 4: 在目标系统上安装
tar -xzf sage-offline-packages-new.tar.gz
pip install --upgrade isage[standard] --no-index --find-links ./sage-offline-packages
```

### Q5: C++ 扩展在离线环境中如何编译？

**A:** 需要系统依赖已预先安装：

```bash
# 在目标系统上，确保已安装：
# - gcc/g++ (C++ 编译器)
# - cmake (构建工具)
# - Python 开发包 (python3-dev)
# - BLAS/LAPACK (数学库)

# 验证依赖
gcc --version
cmake --version
python3-config --include

# 然后离线安装 SAGE（会自动编译 C++ 扩展）
pip install isage[standard] --no-index --find-links ~/packages
```

### Q6: 离线包太大，如何处理？

**A:** 使用几个策略：

```bash
# 1. 只下载需要的组件
pip download -d ~/packages isage[minimal]  # 最小包
pip download -d ~/packages isage[standard] # 标准包

# 2. 使用增量更新（只下载新包）
pip download -d ~/packages --upgrade-strategy only-if-needed isage

# 3. 压缩优化
tar -cjf packages.tar.bz2 packages/  # 使用 bzip2（更好压缩）

# 4. 分割大文件
split -b 500M packages.tar.bz2 packages.tar.bz2.part

# 5. 删除不需要的文件
rm ~/packages/*.tar.gz  # 删除源代码包，只保留 wheel
```

______________________________________________________________________

## 最佳实践总结

### ✅ 离线安装的最佳实践

1. **验证完整性**

   - 总是使用 SHA256 校验和验证
   - 在目标系统上重新验证

1. **记录版本信息**

   - 保存 pip freeze 输出
   - 记录 SAGE 版本和下载日期

1. **保持备份**

   - 保留离线包副本
   - 多份备份到不同介质

1. **定期更新**

   - 定期检查安全更新
   - 每季度重新下载并测试

1. **文档完善**

   - 记录安装步骤和配置
   - 保存故障排除信息

### ❌ 应避免的做法

- ❌ 混合在线和离线包
- ❌ 跳过完整性检查
- ❌ 使用过期的离线包
- ❌ 忽视系统依赖

______________________________________________________________________

## 相关文档

- [权限管理指南](./PERMISSION_MANAGEMENT.md)
- [安全安装指南](./SECURE_INSTALLATION_GUIDE.md)
- [主安装指南](../../docs-public/docs_src/getting-started/installation.md)

______________________________________________________________________

## 获取帮助

遇到离线安装问题时：

1. 检查 [常见问题](#%E5%B8%B8%E8%A7%81%E9%97%AE%E9%A2%98) 部分
1. 查看完整脚本示例
1. 联系 SAGE 社区支持
1. 提交 Issue 到 [GitHub](https://github.com/intellistream/SAGE/issues)

______________________________________________________________________

**最后更新**：2025-11-15\
**版本**：1.0.0\
**维护者**：SAGE Team
