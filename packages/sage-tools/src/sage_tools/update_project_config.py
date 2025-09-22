#!/usr/bin/env python3
"""
SAGE 项目配置管理工具
用于生成统一的 pyproject.toml 文件
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import tomli
import tomli_w


def load_project_config(config_path: str = os.path.join(os.path.dirname(__file__), '../../../project_config.toml')) -> Dict[str, Any]:
    """加载项目配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "rb") as f:
        return tomli.load(f)


def generate_pyproject_config(
    package_key: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """为指定包生成 pyproject.toml 配置"""
    project_info = config["project"]
    urls = config["urls"]
    versions = config["versions"]
    package_descriptions = config["package_descriptions"]
    keywords_config = config["keywords"]

    # 基础配置
    pyproject_config = {
        "build-system": {
            "requires": ["setuptools>=64", "wheel"],
            "build-backend": "setuptools.build_meta",
        },
        "project": {
            "name": package_key,
            "version": versions["current"],
            "description": package_descriptions.get(
                package_key, f"SAGE Framework - {package_key}"
            ),
            "readme": "README.md",
            "requires-python": project_info["python_requires"],
            "license": {"text": project_info["license"]},
            "authors": [
                {
                    "name": project_info["team_name"],
                    "email": project_info["contact_email"],
                }
            ],
            "classifiers": config["classifiers"]["items"].copy(),
            "keywords": keywords_config["common"].copy(),
        },
        "project.urls": {
            "Homepage": urls["homepage"],
            "Repository": urls["repository"],
            "Documentation": urls["documentation"],
            "Issues": urls["issues"],
        },
    }

    # 根据包类型添加特定关键词
    if "kernel" in package_key:
        pyproject_config["project"]["keywords"].extend(keywords_config["kernel"])
    elif "middleware" in package_key:
        pyproject_config["project"]["keywords"].extend(keywords_config["middleware"])
    elif "userspace" in package_key:
        pyproject_config["project"]["keywords"].extend(keywords_config["userspace"])
    elif "dev-toolkit" in package_key:
        pyproject_config["project"]["keywords"].extend(keywords_config["dev_toolkit"])
    elif "frontend" in package_key:
        pyproject_config["project"]["keywords"].extend(keywords_config["frontend"])
    elif package_key == "intellistream":
        pyproject_config["project"]["keywords"].extend(keywords_config["platform"])

    # 去重关键词
    pyproject_config["project"]["keywords"] = list(
        set(pyproject_config["project"]["keywords"])
    )

    return pyproject_config


def update_package_pyproject(
    package_key: str, package_path: str, config: Dict[str, Any]
) -> bool:
    """更新指定包的 pyproject.toml 文件"""
    pyproject_path = os.path.join(package_path, "pyproject.toml")

    if not os.path.exists(pyproject_path):
        print(f"警告: {pyproject_path} 不存在，跳过")
        return False

    # 读取现有配置
    with open(pyproject_path, "rb") as f:
        existing_config = tomli.load(f)

    # 生成新的基础配置
    new_base_config = generate_pyproject_config(package_key, config)

    # 合并配置（保留现有的依赖和工具配置）
    merged_config = existing_config.copy()

    # 更新项目元数据部分
    merged_config["project"]["name"] = new_base_config["project"]["name"]
    merged_config["project"]["version"] = new_base_config["project"]["version"]
    merged_config["project"]["description"] = new_base_config["project"]["description"]
    merged_config["project"]["requires-python"] = new_base_config["project"][
        "requires-python"
    ]
    merged_config["project"]["license"] = new_base_config["project"]["license"]
    merged_config["project"]["authors"] = new_base_config["project"]["authors"]
    merged_config["project"]["classifiers"] = new_base_config["project"]["classifiers"]
    merged_config["project"]["keywords"] = new_base_config["project"]["keywords"]

    # 更新 URLs
    if "urls" not in merged_config["project"]:
        merged_config["project"]["urls"] = {}
    merged_config["project"]["urls"].update(new_base_config["project.urls"])

    # 写回文件
    with open(pyproject_path, "wb") as f:
        tomli_w.dump(merged_config, f)

    print(f"✅ 已更新: {pyproject_path}")
    return True


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python update_project_config.py <command> [args]")
        print("命令:")
        print("  update-all              更新所有包的配置")
        print("  update <package-name>   更新指定包的配置")
        print("  generate <package-name> 生成包配置并打印")
        sys.exit(1)

    command = sys.argv[1]

    # 加载项目配置
    try:
        config = load_project_config()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    if command == "update-all":
        print("🔄 更新所有包的配置...")
        success_count = 0
        total_count = len(config["packages"])

        for package_key, package_path in config["packages"].items():
            if update_package_pyproject(package_key, package_path, config):
                success_count += 1

        print(f"\n📊 完成: {success_count}/{total_count} 个包配置已更新")

    elif command == "update":
        if len(sys.argv) < 3:
            print("错误: 请指定包名")
            sys.exit(1)

        package_key = sys.argv[2]
        if package_key not in config["packages"]:
            print(f"错误: 未知包名 {package_key}")
            print(f"可用包: {', '.join(config['packages'].keys())}")
            sys.exit(1)

        package_path = config["packages"][package_key]
        if update_package_pyproject(package_key, package_path, config):
            print(f"✅ {package_key} 配置已更新")

    elif command == "generate":
        if len(sys.argv) < 3:
            print("错误: 请指定包名")
            sys.exit(1)

        package_key = sys.argv[2]
        if package_key not in config["packages"]:
            print(f"错误: 未知包名 {package_key}")
            sys.exit(1)

        pyproject_config = generate_pyproject_config(package_key, config)
        print(tomli_w.dumps(pyproject_config))

    else:
        print(f"错误: 未知命令 {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
