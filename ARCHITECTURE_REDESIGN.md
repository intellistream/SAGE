# 🎯 SAGE 优雅的商业版控制设计

## 核心设计理念

### 🚀 用户体验至上
```bash
# 普通用户 - 简单到极致
pip install sage

# 商业用户 - 添加一个环境变量
export SAGE_LICENSE_KEY="your-commercial-key"
pip install sage
```

## 🏗️ 架构设计

### 1. 包结构重组
```
packages/
├── sage-core/                 # 核心包 (必须)
├── sage-open/                 # 开源功能包
├── sage-commercial/           # 商业功能包 (可选)
└── sage/                      # 元包 (自动检测并聚合)
```

### 2. 元包智能检测机制
```python
# packages/sage/setup.py
def get_install_requires():
    requires = [
        "sage-core>=1.0.0",
        "sage-open>=1.0.0",
    ]
    
    # 检测商业许可
    if has_commercial_license():
        requires.append("sage-commercial>=1.0.0")
    
    return requires
```

### 3. 许可密钥分发策略

#### 🔑 密钥类型
- **环境变量**: `SAGE_LICENSE_KEY=xxxxx`
- **配置文件**: `~/.sage/license.key`
- **包内置**: 企业内部构建时内置

#### 🔒 验证机制
```python
def has_commercial_license():
    # 方法1: 环境变量
    if os.getenv('SAGE_LICENSE_KEY'):
        return validate_license_key(os.getenv('SAGE_LICENSE_KEY'))
    
    # 方法2: 配置文件
    license_file = Path.home() / '.sage' / 'license.key'
    if license_file.exists():
        return validate_license_file(license_file)
    
    # 方法3: 网络验证 (可选)
    return check_online_license()
```

## 🎁 分发策略

### 开源版本 (PyPI)
```bash
# 用户安装
pip install sage  # 自动获得开源功能

# 开发者安装
pip install -e .  # 在SAGE项目目录下
```

### 商业版本密钥分发
```bash
# 方式1: 环境变量 (临时使用)
export SAGE_LICENSE_KEY="SAGE-COMM-XXXX-XXXX-XXXX"
pip install sage

# 方式2: 许可文件 (持久使用)
sage-license install /path/to/license.key
pip install sage

# 方式3: 企业内部PyPI
pip install sage --index-url https://pypi.yourcompany.com/simple/
```

## 🛠️ 实现方案

### Phase 1: 基础重构
1. 重组包结构 (core/open/commercial)
2. 实现许可检测机制
3. 元包自动聚合功能

### Phase 2: 分发优化
1. 商业密钥管理工具
2. 在线许可验证
3. 企业内部PyPI设置

### Phase 3: 用户体验
1. 一键安装脚本
2. 图形界面许可管理
3. 自动更新机制

## 💡 优势

1. **🎯 用户友好**: `pip install sage` 就是全部
2. **🔒 商业保护**: 密钥控制，源码依然闭源
3. **📦 标准化**: 完全符合Python生态系统
4. **🔄 灵活部署**: 支持多种企业环境
5. **🤝 开发友好**: 开发者无感知切换

## 📋 实施计划

### 立即可做
- [x] 设计架构方案
- [ ] 重组包结构  
- [ ] 实现基础许可检测
- [ ] 更新安装脚本

### 中期目标
- [ ] 商业密钥管理工具
- [ ] 在线许可验证系统
- [ ] 企业部署指南

### 长期愿景
- [ ] 自动化许可续费
- [ ] 使用分析和计费
- [ ] 多级许可体系
