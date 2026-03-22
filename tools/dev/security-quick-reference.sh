#!/bin/bash
# SAGE 安全性改进 - 快速参考命令

# ============================================================================
# 安全安装（推荐）
# ============================================================================

# 方式 1: 标准安全安装（带深度验证）
echo "📦 标准安全安装"
# conda activate sage
# ./quickstart.sh --verify-deps --standard

# ============================================================================
# CI/CD 部署
# ============================================================================

# 方式 2: 严格验证模式（用于 CI/CD）
echo "🔒 CI/CD 严格验证模式"
# ./quickstart.sh --verify-deps-strict --dev --yes

# ============================================================================
# 企业网络部署
# ============================================================================

# 方式 3: 企业网络（配置代理）
echo "🏢 企业网络部署"
# export HTTP_PROXY=http://proxy.company.com:8080
# export HTTPS_PROXY=https://proxy.company.com:8080
# ./quickstart.sh --verify-deps --standard --yes

# ============================================================================
# Air-Gapped 离线系统
# ============================================================================

# 方式 4: Air-Gapped 系统（完全离线）
echo "🌐 Air-Gapped 离线安装"

# 步骤 1: 在有网络的系统上下载离线包
# pip download -d ~/packages isage[standard]
# tar -czf packages.tar.gz packages/
# # 通过 USB/SCP 传输到目标系统

# 步骤 2: 在离线系统上安装
# tar -xzf packages.tar.gz
# pip install isage[standard] --no-index --find-links ./packages

# ============================================================================
# 快速诊断
# ============================================================================

# 诊断环境问题
echo "🔍 环境诊断"
# ./quickstart.sh --doctor

# 诊断并自动修复
echo "🔧 诊断并修复"
# ./quickstart.sh --doctor-fix

# ============================================================================
# 验证安装
# ============================================================================

# 查看 SAGE 版本
echo "✅ 验证安装"
# python3 -c "import sage; print(f'SAGE {sage.__version__} installed')"

# 运行 SAGE 诊断
# sage doctor

# ============================================================================
# 帮助和文档
# ============================================================================

# 查看所有可用选项
echo "📖 查看帮助"
# ./quickstart.sh --help

# 查看 --verify-deps 选项
echo "🔐 验证选项说明"
# ./quickstart.sh --help | grep -A 10 "verify-deps"

# ============================================================================
# 安全文档导航
# ============================================================================

echo ""
echo "📚 安全文档导航"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🏠 安全文档首页"
echo "   docs/security/README.md"
echo ""
echo "🔐 权限管理指南"
echo "   docs/security/PERMISSION_MANAGEMENT.md"
echo ""
echo "🔒 安全安装指南"
echo "   docs/security/SECURE_INSTALLATION_GUIDE.md"
echo ""
echo "🌐 离线安装指南"
echo "   docs/security/OFFLINE_INSTALLATION.md"
echo ""
echo "📋 安全改进总结"
echo "   docs/security/SECURITY_IMPROVEMENTS.md"
echo ""
echo "📊 实现总结"
echo "   docs/security/IMPLEMENTATION_SUMMARY.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 更多帮助: ./quickstart.sh --help"
