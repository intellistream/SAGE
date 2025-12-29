#!/usr/bin/env python3
"""
配置迁移脚本 - 从旧版格式迁移到 memory_v2 格式

功能:
1. 检测旧版配置格式（非YAML）
2. 转换为新的YAML格式
3. 验证迁移后的配置
4. 生成迁移报告

使用方法:
    python config_migration.py <old_config_dir> <new_config_dir>
    python config_migration.py --check <config_dir>  # 检查模式
    python config_migration.py --batch <dir>         # 批量迁移

示例:
    python config_migration.py old_configs/ memory_v2/
    python config_migration.py --check memory_v2/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ConfigMigrator:
    """配置迁移器"""

    def __init__(self, dry_run: bool = False):
        """
        初始化迁移器

        Args:
            dry_run: 试运行模式，不实际写入文件
        """
        self.dry_run = dry_run
        self.migration_count = 0
        self.error_count = 0

    def detect_format(self, config_path: Path) -> str:
        """
        检测配置文件格式

        Args:
            config_path: 配置文件路径

        Returns:
            格式类型: "yaml", "json", "unknown"
        """
        if not config_path.exists():
            return "unknown"

        suffix = config_path.suffix.lower()
        if suffix in [".yaml", ".yml"]:
            return "yaml"
        elif suffix == ".json":
            return "json"

        # 尝试读取内容判断
        try:
            with open(config_path) as f:
                content = f.read()
                # 简单判断：如果有 { 开头，可能是JSON
                if content.strip().startswith("{"):
                    return "json"
                elif ":" in content and "-" in content:
                    return "yaml"
        except Exception:
            pass

        return "unknown"

    def load_old_config(self, config_path: Path) -> dict[str, Any] | None:
        """
        加载旧版配置

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典，失败返回None
        """
        format_type = self.detect_format(config_path)

        try:
            if format_type == "yaml":
                with open(config_path) as f:
                    return yaml.safe_load(f)
            elif format_type == "json":
                with open(config_path) as f:
                    return json.load(f)
            else:
                logger.error(f"Unknown format for {config_path}")
                return None
        except Exception as e:
            logger.error(f"Failed to load {config_path}: {e}")
            return None

    def convert_to_v2(self, old_config: dict[str, Any], service_name: str) -> dict[str, Any]:
        """
        转换为 memory_v2 格式

        Args:
            old_config: 旧版配置
            service_name: Service名称

        Returns:
            新版配置字典
        """
        # 基础 v2 模板
        v2_config = {
            "version": "2.0",
            "service": {
                "type": self._infer_service_type(service_name, old_config),
                "name": service_name,
                "description": old_config.get("description", f"{service_name} service"),
            },
        }

        # 转换索引配置
        if "indexes" in old_config:
            v2_config["service"]["indexes"] = self._convert_indexes(old_config["indexes"])
        elif "index" in old_config:
            # 单索引情况
            v2_config["service"]["indexes"] = [self._convert_index(old_config["index"])]

        # 转换Service配置
        if "config" in old_config:
            v2_config["service"]["service_config"] = old_config["config"]
        elif "service_config" in old_config:
            v2_config["service"]["service_config"] = old_config["service_config"]

        # 添加默认配置
        if "service_config" not in v2_config["service"]:
            v2_config["service"]["service_config"] = {}

        return v2_config

    def _infer_service_type(self, name: str, config: dict[str, Any]) -> str:
        """推断Service类型"""
        name_lower = name.lower()

        # Partitional services
        if "fifo" in name_lower or "queue" in name_lower:
            return "partitional.fifo_queue"
        elif "lru" in name_lower or "cache" in name_lower:
            return "partitional.lru_cache"
        elif "lsh" in name_lower:
            return "partitional.lsh_hash"
        elif "time_window" in name_lower or "window" in name_lower:
            return "partitional.time_window"
        elif "inverted" in name_lower and "vector" in name_lower:
            return "partitional.inverted_vectorstore_combination"
        elif "feature" in name_lower and "summary" in name_lower:
            return "partitional.feature_summary_vectorstore_combination"

        # Hierarchical services
        elif "semantic" in name_lower and "inverted" in name_lower and "kg" in name_lower:
            return "hierarchical.semantic_inverted_knowledge_graph"
        elif "linknote" in name_lower or "note" in name_lower:
            return "hierarchical.linknote_graph"
        elif "property" in name_lower and "graph" in name_lower:
            return "hierarchical.property_graph"

        # 默认返回
        return "partitional.unknown"

    def _convert_indexes(self, old_indexes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """转换索引列表"""
        return [self._convert_index(idx) for idx in old_indexes]

    def _convert_index(self, old_index: dict[str, Any]) -> dict[str, Any]:
        """
        转换单个索引配置

        Args:
            old_index: 旧版索引配置

        Returns:
            新版索引配置
        """
        # 基础字段映射
        new_index = {
            "name": old_index.get("name", "unnamed_index"),
            "type": old_index.get("type", old_index.get("index_type", "unknown")),
        }

        # 转换配置字段
        if "config" in old_index:
            new_index["config"] = old_index["config"]
        else:
            # 收集所有非基础字段作为config
            config_keys = set(old_index.keys()) - {"name", "type", "index_type"}
            if config_keys:
                new_index["config"] = {k: old_index[k] for k in config_keys}

        return new_index

    def migrate_file(self, old_path: Path, new_path: Path) -> bool:
        """
        迁移单个配置文件

        Args:
            old_path: 旧配置文件路径
            new_path: 新配置文件路径

        Returns:
            成功返回True
        """
        logger.info(f"Migrating {old_path.name} -> {new_path.name}")

        # 加载旧配置
        old_config = self.load_old_config(old_path)
        if old_config is None:
            self.error_count += 1
            return False

        # 检查是否已经是v2格式
        if old_config.get("version") == "2.0":
            logger.info("  Already in v2 format, copying...")
            if not self.dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                with open(new_path, "w") as f:
                    yaml.dump(old_config, f, default_flow_style=False, sort_keys=False)
            return True

        # 转换
        service_name = old_path.stem
        try:
            new_config = self.convert_to_v2(old_config, service_name)

            # 写入新配置
            if not self.dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                with open(new_path, "w") as f:
                    yaml.dump(new_config, f, default_flow_style=False, sort_keys=False)

            logger.info("  ✓ Migrated successfully")
            self.migration_count += 1
            return True

        except Exception as e:
            logger.error(f"  ✗ Migration failed: {e}")
            self.error_count += 1
            return False

    def migrate_directory(self, old_dir: Path, new_dir: Path) -> dict[str, Any]:
        """
        迁移整个目录

        Args:
            old_dir: 旧配置目录
            new_dir: 新配置目录

        Returns:
            迁移报告字典
        """
        if not old_dir.exists():
            logger.error(f"Old directory does not exist: {old_dir}")
            return {"success": False, "error": "Directory not found"}

        # 查找所有配置文件
        config_files = list(old_dir.glob("*.yaml")) + list(old_dir.glob("*.yml"))
        config_files += list(old_dir.glob("*.json"))

        if not config_files:
            logger.warning(f"No configuration files found in {old_dir}")
            return {"success": True, "migrated": 0, "errors": 0}

        logger.info(f"Found {len(config_files)} configuration files")

        # 迁移每个文件
        for old_file in config_files:
            new_file = new_dir / f"{old_file.stem}.yaml"
            self.migrate_file(old_file, new_file)

        # 生成报告
        report = {
            "success": self.error_count == 0,
            "total_files": len(config_files),
            "migrated": self.migration_count,
            "errors": self.error_count,
            "dry_run": self.dry_run,
        }

        return report

    def check_v2_format(self, config_path: Path) -> bool:
        """
        检查是否符合v2格式

        Args:
            config_path: 配置文件路径

        Returns:
            符合返回True
        """
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # 检查必需字段
            if config.get("version") != "2.0":
                logger.warning(f"{config_path.name}: Missing or incorrect version")
                return False

            if "service" not in config:
                logger.warning(f"{config_path.name}: Missing 'service' section")
                return False

            service = config["service"]
            required_fields = ["type", "name"]
            for field in required_fields:
                if field not in service:
                    logger.warning(f"{config_path.name}: Missing service.{field}")
                    return False

            logger.info(f"{config_path.name}: ✓ Valid v2 format")
            return True

        except Exception as e:
            logger.error(f"{config_path.name}: Error checking format: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Configuration migration tool")
    parser.add_argument("source", help="Source directory or file")
    parser.add_argument("target", nargs="?", help="Target directory (optional for check mode)")
    parser.add_argument("--check", action="store_true", help="Check v2 format only")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without writing files")
    parser.add_argument("--batch", action="store_true", help="Batch migration mode")

    args = parser.parse_args()

    source_path = Path(args.source)
    migrator = ConfigMigrator(dry_run=args.dry_run)

    # 检查模式
    if args.check:
        if source_path.is_file():
            valid = migrator.check_v2_format(source_path)
            sys.exit(0 if valid else 1)
        elif source_path.is_dir():
            config_files = list(source_path.glob("*.yaml")) + list(source_path.glob("*.yml"))
            all_valid = all(migrator.check_v2_format(f) for f in config_files)
            logger.info(f"\nChecked {len(config_files)} files")
            sys.exit(0 if all_valid else 1)
        else:
            logger.error(f"Invalid path: {source_path}")
            sys.exit(1)

    # 迁移模式
    if not args.target:
        logger.error("Target directory required for migration")
        parser.print_help()
        sys.exit(1)

    target_path = Path(args.target)

    # 单文件迁移
    if source_path.is_file():
        target_file = target_path / f"{source_path.stem}.yaml"
        success = migrator.migrate_file(source_path, target_file)
        sys.exit(0 if success else 1)

    # 目录迁移
    elif source_path.is_dir():
        report = migrator.migrate_directory(source_path, target_path)

        # 打印报告
        print("\n" + "=" * 60)
        print("MIGRATION REPORT")
        print("=" * 60)
        print(f"Total files:    {report['total_files']}")
        print(f"Migrated:       {report['migrated']}")
        print(f"Errors:         {report['errors']}")
        print(f"Dry run:        {report['dry_run']}")
        print(f"Status:         {'✓ SUCCESS' if report['success'] else '✗ FAILED'}")
        print("=" * 60)

        sys.exit(0 if report["success"] else 1)

    else:
        logger.error(f"Invalid source path: {source_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
