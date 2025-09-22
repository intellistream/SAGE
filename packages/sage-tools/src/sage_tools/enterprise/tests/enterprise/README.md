# SAGE Enterprise Edition Tests

企业版功能测试套件，用于验证企业版安装和功能。

## 🧪 测试工具

### `enterprise_test.py` - 统一企业版验证工具

**功能**：
- ✅ 许可证状态验证
- ✅ 企业版模块导入测试  
- ✅ 核心功能检查
- ✅ 详细测试报告

**使用方法**：
```bash
# 基础用法
python tests/enterprise/enterprise_test.py

# 在项目根目录运行
cd /path/to/SAGE
python tests/enterprise/enterprise_test.py
```

**输出示例**：
```
🎯 SAGE Enterprise Edition Validation
==================================================
📜 检查许可证状态...
✅ license: 许可证有效
🏢 检查企业版模块...
✅ modules: 3/3 模块正常
🔧 检查核心功能...
✅ core: SAGE核心模块正常

📊 测试总结
==============================
总测试数: 3
成功测试: 3
成功率: 100.0%
```

## 🎯 使用场景

### 开发验证
```bash
# 快速检查企业版状态
python tests/enterprise/enterprise_test.py
```

### 部署验证
```bash
# CI/CD中的自动化测试
python tests/enterprise/enterprise_test.py
echo "Enterprise test exit code: $?"
```

### 问题诊断
```bash
# 详细诊断信息
python tests/enterprise/enterprise_test.py 2>&1 | tee enterprise_test.log
```

## � 测试内容

1. **许可证验证**
   - 检查许可证文件存在性
   - 验证许可证有效期
   - 确认企业版特性可用

2. **模块导入**
   - `sage.kernel.enterprise` 
   - `sage.middleware.enterprise`
   - `sage.apps.enterprise`
   - 检查导入警告

3. **核心功能**
   - SAGE基础模块可用性
   - 模块路径正确性

## 🔧 维护

此测试工具应该与企业版功能同步更新，确保覆盖所有重要的企业版特性。
</content>
</invoke>
