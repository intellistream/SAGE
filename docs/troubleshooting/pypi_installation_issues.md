# PyPI 安装故障排除

## 🚨 常见安装问题

### 1. 依赖包冲突

**问题描述**：安装 SAGE 时出现依赖包版本冲突

**错误示例**：
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
some-package 1.0.0 requires dependency-x>=2.0.0, but you have dependency-x 1.5.0 which is incompatible.
```

**解决方案**：

1. **创建新的虚拟环境**（推荐）
   ```bash
   # 使用 venv
   python -m venv sage-env
   source sage-env/bin/activate  # Linux/Mac
   # sage-env\Scripts\activate  # Windows
   
   # 使用 conda
   conda create -n sage python=3.11 -y
   conda activate sage
   
   # 安装 SAGE
   pip install isage
   ```

2. **强制重新安装**
   ```bash
   pip install --force-reinstall isage
   ```

3. **使用交互式安装向导**
   ```bash
   pip install isage
   sage-install  # 自动处理依赖问题
   ```

### 2. 网络连接问题

**问题描述**：安装过程中网络超时或连接失败

**错误示例**：
```
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None)) after connection broken
ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443)
```

**解决方案**：

1. **使用国内镜像源**
   ```bash
   # 清华大学镜像
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple isage
   
   # 阿里云镜像
   pip install -i https://mirrors.aliyun.com/pypi/simple isage
   
   # 中科大镜像
   pip install -i https://pypi.mirrors.ustc.edu.cn/simple isage
   ```

2. **配置永久镜像源**
   ```bash
   # 创建 pip 配置文件
   mkdir -p ~/.pip
   cat > ~/.pip/pip.conf << EOF
   [global]
   index-url = https://pypi.tuna.tsinghua.edu.cn/simple
   trusted-host = pypi.tuna.tsinghua.edu.cn
   EOF
   ```

3. **增加超时时间**
   ```bash
   pip install --timeout 300 isage
   ```

### 3. 权限问题

**问题描述**：没有权限安装到系统目录

**错误示例**：
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied: '/usr/local/lib/python3.x/site-packages/'
```

**解决方案**：

1. **用户模式安装**（推荐）
   ```bash
   pip install --user isage
   ```

2. **使用虚拟环境**
   ```bash
   python -m venv ~/.sage-env
   source ~/.sage-env/bin/activate
   pip install isage
   ```

3. **使用 sudo**（不推荐）
   ```bash
   sudo pip install isage
   ```

### 4. Python 版本不兼容

**问题描述**：Python版本过低或过高

**错误示例**：
```
ERROR: Package 'isage' requires a different Python: 3.7.0 not in '>=3.8,<3.12'
```

**解决方案**：

1. **检查当前Python版本**
   ```bash
   python --version
   ```

2. **使用兼容的Python版本**
   ```bash
   # 使用 conda 安装兼容版本
   conda install python=3.11
   
   # 或者使用 pyenv
   pyenv install 3.11.0
   pyenv global 3.11.0
   ```

3. **使用系统上的其他Python版本**
   ```bash
   # 查找可用的Python版本
   ls /usr/bin/python*
   
   # 使用特定版本
   python3.11 -m pip install isage
   ```

### 5. 磁盘空间不足

**问题描述**：安装过程中磁盘空间不够

**错误示例**：
```
OSError: [Errno 28] No space left on device
```

**解决方案**：

1. **清理pip缓存**
   ```bash
   pip cache purge
   ```

2. **检查磁盘空间**
   ```bash
   df -h
   ```

3. **清理不必要的文件**
   ```bash
   # 清理临时文件
   sudo rm -rf /tmp/*
   
   # 清理系统日志
   sudo journalctl --vacuum-time=3d
   ```

### 6. 企业网络环境

**问题描述**：企业防火墙或代理设置导致安装失败

**解决方案**：

1. **配置代理**
   ```bash
   # HTTP代理
   pip install --proxy http://user:password@proxy.company.com:8080 isage
   
   # 环境变量方式
   export http_proxy=http://proxy.company.com:8080
   export https_proxy=https://proxy.company.com:8080
   pip install isage
   ```

2. **跳过SSL验证**（仅测试环境）
   ```bash
   pip install --trusted-host pypi.org --trusted-host pypi.python.org isage
   ```

3. **离线安装**
   ```bash
   # 在有网络的机器上下载
   pip download isage -d ./wheels
   
   # 在离线机器上安装
   pip install --find-links ./wheels --no-index isage
   ```

## 🔍 安装验证

安装完成后，验证是否正确安装：

```bash
# 基础验证
python -c "import sage; print('✅ SAGE 安装成功！')"

# 版本检查
python -c "import sage; print(f'SAGE版本: {sage.__version__}')"

# 模块检查
python -c "from sage.common.cli.main import app; print('✅ CLI模块正常')"

# 企业版验证（如果安装了企业版）
python -c "import sage.kernel.enterprise; print('✅ 企业版功能可用')"
```

## 🚀 下一步

安装成功后：

1. **运行交互式设置**
   ```bash
   sage-install
   ```

2. **查看快速开始指南**
   ```bash
   sage --help
   ```

3. **启动 JobManager**
   ```bash
   sage jobmanager start
   ```

---

💡 **提示**：如果遇到其他问题，请使用 `sage-install` 交互式安装向导，它会自动检测并解决大多数常见问题。
