#!/usr/bin/env python3
"""
SAGE 智能安装脚本
根据配置和环境自动生成和执行安装
"""

import os
import sys
import yaml
import subprocess
import argparse
from pathlib import Path

def load_config():
    """加载SAGE配置文件"""
    config_file = Path("sage-config.yml")
    if not config_file.exists():
        print("❌ 配置文件 sage-config.yml 不存在")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def check_commercial_access():
    """检查是否有商业版本访问权限"""
    commercial_dir = Path("packages/commercial")
    return commercial_dir.exists() and any(commercial_dir.iterdir())

def generate_requirements(version_type, config, dev_mode=False):
    """生成requirements内容"""
    content = []
    
    # 添加注释头
    if version_type == "commercial":
        content.append("# SAGE 商业版安装 (需要商业授权)")
        content.append("# 适用于：企业开发者，内部团队")
    else:
        content.append("# SAGE 开源版安装")
        content.append("# 适用于：开源开发者，社区贡献者")
    
    content.append(f"# 安装方式：pip install -r requirements-{version_type}.txt")
    content.append("")
    content.append("# " + "="*50)
    content.append("# SAGE 包 (Editable 模式)" if dev_mode else "# SAGE 包")
    content.append("# " + "="*50)
    content.append("")
    
    # 添加核心包
    for pkg in config['packages']['core']:
        prefix = "-e " if dev_mode else ""
        content.append(f"{prefix}./{pkg}")
    
    # 添加版本特定包
    if version_type in config['packages']:
        for pkg in config['packages'][version_type]:
            prefix = "-e " if dev_mode else ""
            content.append(f"{prefix}./{pkg}")
    
    # 添加开发工具 (仅开发模式)
    if dev_mode:
        content.append("")
        content.append("# " + "="*50)
        content.append("# 开发工具")
        content.append("# " + "="*50)
        content.append("")
        for tool in config['dev-tools']:
            content.append(tool)
    
    return "\n".join(content)

def create_requirements_file(version_type, config, dev_mode=False):
    """创建requirements文件"""
    suffix = "-dev" if dev_mode else ""
    filename = f"requirements-{version_type}{suffix}.txt"
    
    content = generate_requirements(version_type, config, dev_mode)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 生成 {filename}")
    return filename

def install_packages(requirements_file):
    """安装包"""
    print(f"🔧 正在安装: {requirements_file}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], 
                      check=True)
        print("✅ 安装完成!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="SAGE 智能安装工具")
    parser.add_argument("--version", choices=["auto", "open-source", "commercial"], 
                       default="auto", help="指定安装版本")
    parser.add_argument("--dev", action="store_true", help="开发模式 (editable安装)")
    parser.add_argument("--generate-only", action="store_true", help="仅生成requirements文件，不安装")
    
    args = parser.parse_args()
    
    print("🚀 SAGE 智能安装工具")
    print("=" * 30)
    
    # 加载配置
    config = load_config()
    
    # 确定版本类型
    if args.version == "auto":
        # 自动检测
        if check_commercial_access():
            version_type = "commercial"
            print("🏢 检测到商业版本访问权限，使用商业版")
        else:
            version_type = "open-source"
            print("🌍 使用开源版本")
    else:
        version_type = args.version
        
    # 检查商业版本权限
    if version_type == "commercial" and not check_commercial_access():
        print("❌ 商业版本需要访问权限")
        print("💡 请联系管理员获取商业版本代码")
        sys.exit(1)
    
    # 生成requirements文件
    requirements_file = create_requirements_file(version_type, config, args.dev)
    
    if not args.generate_only:
        # 执行安装
        success = install_packages(requirements_file)
        
        if success:
            print(f"🎉 SAGE {version_type} 安装完成!")
            if args.dev:
                print("💡 开发模式：代码修改将立即生效")
        else:
            print("💥 安装失败，请检查错误信息")
            sys.exit(1)
    else:
        print(f"📝 已生成 {requirements_file}，使用以下命令安装:")
        print(f"   pip install -r {requirements_file}")

if __name__ == "__main__":
    main()
