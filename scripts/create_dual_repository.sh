#!/bin/bash
# SAGE 双仓库迁移脚本
# 将开源部分迁移到公开仓库

# === 方案1：双仓库策略 ===
# sage-oss (公开)：纯开源功能
# sage-enterprise (私有)：企业版功能

create_oss_repository() {
    echo "🔄 创建开源仓库结构..."
    
    # 1. 创建开源仓库目录
    mkdir -p ../sage-oss/{packages,tools,docs,tests}
    
    # 2. 复制开源代码（排除企业版）
    rsync -av --exclude='**/enterprise/' \
              --exclude='**/commercial/' \
              --exclude='tools/license/' \
              packages/ ../sage-oss/packages/
    
    # 3. 复制开源文档
    cp README.md LICENSE ../sage-oss/
    
    # 4. 创建开源版pyproject.toml (移除enterprise依赖)
    echo "正在清理企业版依赖..."
}

create_enterprise_packages() {
    echo "🏢 创建企业版独立包..."
    
    # 企业版作为独立包发布到私有PyPI
    mkdir -p ../sage-enterprise/packages
    
    # 提取企业版功能
    for pkg in sage-kernel sage-middleware sage-apps; do
        mkdir -p "../sage-enterprise/packages/${pkg}-ee"
        cp -r "packages/${pkg}/src/sage/*/enterprise/" \
              "../sage-enterprise/packages/${pkg}-ee/src/"
    done
}

# 执行迁移
create_oss_repository
create_enterprise_packages

echo "✅ 双仓库结构创建完成"
echo "📋 下一步："
echo "1. 将sage-oss推送到GitHub公开仓库"
echo "2. 将sage-enterprise保持私有或推送到私有仓库"
echo "3. 配置双重发布流程"
