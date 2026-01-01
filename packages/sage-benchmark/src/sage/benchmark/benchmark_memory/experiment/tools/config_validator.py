#!/usr/bin/env python3
"""
配置验证脚本 - 验证 memory_v2 配置文件的正确性

功能:
1. 验证YAML格式
2. 检查必需字段
3. 验证索引配置
4. 检查Service类型
5. 生成验证报告

使用方法:
    python config_validator.py <config_file_or_dir>
    python config_validator.py --strict <config_file>
    python config_validator.py --json-report <config_dir>

示例:
    python config_validator.py memory_v2/
    python config_validator.py memory_v2/partitional_fifo_queue.yaml
    python config_validator.py --strict memory_v2/ --json-report report.json
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


class ConfigValidator:
    """配置验证器"""

    # 支持的Service类型
    VALID_SERVICE_TYPES = {
        # Partitional
        "partitional.fifo_queue",
        "partitional.lru_cache",
        "partitional.lsh_hash",
        "partitional.time_window",
        "partitional.segment_index",
        "partitional.inverted_vectorstore_combination",
        "partitional.feature_summary_vectorstore_combination",
        # Hierarchical
        "hierarchical.linknote_graph",
        "hierarchical.property_graph",
        "hierarchical.semantic_inverted_knowledge_graph",
    }

    # 支持的索引类型
    VALID_INDEX_TYPES = {
        "fifo",
        "lru",
        "lsh",
        "time_window",
        "segment",
        "faiss",
        "bm25",
        "graph",
    }

    def __init__(self, strict: bool = False):
        """
        初始化验证器

        Args:
            strict: 严格模式，任何警告都视为错误
        """
        self.strict = strict
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, message: str) -> None:
        """添加错误"""
        self.errors.append(message)
        logger.error(f"  ✗ {message}")

    def add_warning(self, message: str) -> None:
        """添加警告"""
        self.warnings.append(message)
        if self.strict:
            logger.error(f"  ✗ {message} (strict mode)")
        else:
            logger.warning(f"  ⚠ {message}")

    def validate_file(self, config_path: Path) -> dict[str, Any]:
        """
        验证单个配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            验证结果字典
        """
        logger.info(f"Validating {config_path.name}")
        self.errors = []
        self.warnings = []

        # 1. 检查文件存在
        if not config_path.exists():
            self.add_error(f"File not found: {config_path}")
            return self._build_result(config_path, valid=False)

        # 2. 加载YAML
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.add_error(f"Invalid YAML format: {e}")
            return self._build_result(config_path, valid=False)
        except Exception as e:
            self.add_error(f"Failed to read file: {e}")
            return self._build_result(config_path, valid=False)

        # 3. 验证顶层结构
        if not isinstance(config, dict):
            self.add_error("Config must be a dictionary")
            return self._build_result(config_path, valid=False)

        # 4. 验证版本
        self._validate_version(config)

        # 5. 验证service节
        if "service" not in config:
            self.add_error("Missing 'service' section")
            return self._build_result(config_path, valid=False)

        self._validate_service(config["service"])

        # 6. 判断是否有效
        is_valid = len(self.errors) == 0
        if self.strict:
            is_valid = is_valid and len(self.warnings) == 0

        if is_valid:
            logger.info("  ✓ Valid configuration")
        else:
            logger.error(
                f"  ✗ Invalid configuration ({len(self.errors)} errors, {len(self.warnings)} warnings)"
            )

        return self._build_result(config_path, valid=is_valid, config=config)

    def _validate_version(self, config: dict[str, Any]) -> None:
        """验证版本字段"""
        if "version" not in config:
            self.add_warning("Missing 'version' field (recommended)")
        elif config["version"] != "2.0":
            self.add_warning(f"Unexpected version: {config['version']} (expected 2.0)")

    def _validate_service(self, service: dict[str, Any]) -> None:
        """验证service节"""
        if not isinstance(service, dict):
            self.add_error("'service' must be a dictionary")
            return

        # 必需字段
        required_fields = ["type", "name"]
        for field in required_fields:
            if field not in service:
                self.add_error(f"Missing required field: service.{field}")

        # 验证service类型
        if "type" in service:
            service_type = service["type"]
            if service_type not in self.VALID_SERVICE_TYPES:
                self.add_warning(f"Unknown service type: {service_type}")

        # 推荐字段
        if "description" not in service:
            self.add_warning("Missing 'description' field (recommended)")

        # 验证indexes
        if "indexes" in service:
            self._validate_indexes(service["indexes"])

        # 验证service_config
        if "service_config" in service:
            if not isinstance(service["service_config"], dict):
                self.add_error("service.service_config must be a dictionary")

    def _validate_indexes(self, indexes: Any) -> None:
        """验证indexes列表"""
        if not isinstance(indexes, list):
            self.add_error("service.indexes must be a list")
            return

        if len(indexes) == 0:
            self.add_warning("Empty indexes list")

        for i, index in enumerate(indexes):
            self._validate_index(index, i)

    def _validate_index(self, index: Any, position: int) -> None:
        """验证单个index配置"""
        if not isinstance(index, dict):
            self.add_error(f"Index {position} must be a dictionary")
            return

        # 必需字段
        required_fields = ["name", "type"]
        for field in required_fields:
            if field not in index:
                self.add_error(f"Index {position}: Missing required field '{field}'")

        # 验证索引类型
        if "type" in index:
            index_type = index["type"]
            if index_type not in self.VALID_INDEX_TYPES:
                self.add_warning(f"Index {position}: Unknown index type '{index_type}'")

        # config字段（可选）
        if "config" in index:
            if not isinstance(index["config"], dict):
                self.add_error(f"Index {position}: 'config' must be a dictionary")

    def _build_result(
        self, config_path: Path, valid: bool, config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """构建验证结果"""
        return {
            "file": str(config_path),
            "valid": valid,
            "errors": self.errors.copy(),
            "warnings": self.warnings.copy(),
            "config": config,
        }

    def validate_directory(self, config_dir: Path) -> dict[str, Any]:
        """
        验证整个目录

        Args:
            config_dir: 配置目录路径

        Returns:
            验证报告字典
        """
        if not config_dir.exists():
            logger.error(f"Directory not found: {config_dir}")
            return {"success": False, "error": "Directory not found"}

        # 查找所有YAML文件
        config_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))

        if not config_files:
            logger.warning(f"No YAML files found in {config_dir}")
            return {"success": True, "total": 0, "valid": 0, "invalid": 0}

        logger.info(f"Found {len(config_files)} configuration files\n")

        # 验证每个文件
        results = []
        valid_count = 0
        invalid_count = 0

        for config_file in sorted(config_files):
            result = self.validate_file(config_file)
            results.append(result)

            if result["valid"]:
                valid_count += 1
            else:
                invalid_count += 1

            print()  # 空行分隔

        # 生成报告
        report = {
            "success": invalid_count == 0,
            "total": len(config_files),
            "valid": valid_count,
            "invalid": invalid_count,
            "results": results,
            "strict_mode": self.strict,
        }

        return report


def print_report(report: dict[str, Any]) -> None:
    """打印验证报告"""
    print("=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)
    print(f"Total files:     {report['total']}")
    print(f"Valid:           {report['valid']}")
    print(f"Invalid:         {report['invalid']}")
    print(f"Strict mode:     {report.get('strict_mode', False)}")
    print(f"Status:          {'✓ ALL VALID' if report['success'] else '✗ VALIDATION FAILED'}")
    print("=" * 70)

    # 详细错误信息
    if report["invalid"] > 0:
        print("\nFailed files:")
        for result in report["results"]:
            if not result["valid"]:
                print(f"\n  {result['file']}:")
                for error in result["errors"]:
                    print(f"    ✗ {error}")
                for warning in result["warnings"]:
                    print(f"    ⚠ {warning}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Configuration validation tool")
    parser.add_argument("path", help="Configuration file or directory to validate")
    parser.add_argument("--strict", action="store_true", help="Strict mode: warnings as errors")
    parser.add_argument("--json-report", help="Output JSON report to file")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode: only show summary")

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    config_path = Path(args.path)
    validator = ConfigValidator(strict=args.strict)

    # 单文件验证
    if config_path.is_file():
        result = validator.validate_file(config_path)

        if args.json_report:
            with open(args.json_report, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\nReport saved to {args.json_report}")

        sys.exit(0 if result["valid"] else 1)

    # 目录验证
    elif config_path.is_dir():
        report = validator.validate_directory(config_path)

        # 打印报告
        print_report(report)

        # JSON报告
        if args.json_report:
            with open(args.json_report, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nJSON report saved to {args.json_report}")

        sys.exit(0 if report["success"] else 1)

    else:
        logger.error(f"Invalid path: {config_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
