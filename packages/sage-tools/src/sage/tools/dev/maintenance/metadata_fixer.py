"""
Dev-notes 文档元数据批量修复工具

从 tools/maintenance/helpers/batch_fix_devnotes_metadata.py 迁移

Author: SAGE Team
Date: 2025-10-27
"""

from pathlib import Path

# 预定义需要修复的文件列表
DEFAULT_FILES_TO_FIX = {
    # architecture/
    "docs/dev-notes/architecture/DATA_TYPES_ARCHITECTURE.md": {
        "date": "2024-10-20",
        "summary": "SAGE 分层数据类型系统设计文档，包括 BaseDocument、RAGDocument 等核心类型的架构说明",
    },
    "docs/dev-notes/architecture/KERNEL_REFACTORING_ANALYSIS_1041.md": {
        "date": "2025-10-24",
        "summary": "Kernel 层功能重构分析，探讨将部分功能下沉到 platform 或 common 层的可行性",
    },
    "docs/dev-notes/architecture/NEUROMEM_ARCHITECTURE_ANALYSIS.md": {
        "date": "2025-01-22",
        "summary": "NeuroMem 作为独立记忆体组件的完整性评估，包括存储、检索、管理等核心功能分析",
    },
    "docs/dev-notes/architecture/SAGE_CHAT_ARCHITECTURE.md": {
        "date": "2024-10-15",
        "summary": "SAGE Chat 架构设计文档，包括对话管理、上下文处理和多轮对话支持",
    },
    "docs/dev-notes/architecture/VLLM_SERVICE_INTEGRATION_DESIGN.md": {
        "date": "2024-09-20",
        "summary": "vLLM 服务集成设计，包括 API 封装、配置管理和性能优化策略",
    },
    # archive/
    "docs/dev-notes/archive/PR_DESCRIPTION.md": {
        "date": "2024-08-15",
        "summary": "PR 描述模板和规范说明",
    },
    # autostop/
    "docs/dev-notes/autostop/AUTOSTOP_MODE_SUPPORT.md": {
        "date": "2024-11-10",
        "summary": "AutoStop 模式支持文档，包括自动停止机制的设计和实现",
    },
    "docs/dev-notes/autostop/AUTOSTOP_SERVICE_FIX_SUMMARY.md": {
        "date": "2024-11-12",
        "summary": "AutoStop 服务修复总结，包括已知问题和解决方案",
    },
    "docs/dev-notes/autostop/REMOTE_AUTOSTOP_IMPLEMENTATION.md": {
        "date": "2024-11-15",
        "summary": "远程 AutoStop 实现文档，支持分布式环境下的自动停止功能",
    },
    # migration/
    "docs/dev-notes/migration/EMBEDDING_SYSTEM_COMPLETE_SUMMARY.md": {
        "date": "2024-09-25",
        "summary": "Embedding 系统迁移完整总结，包括架构变更和性能对比",
    },
    # security/
    "docs/dev-notes/security/CONFIG_CLEANUP_REPORT.md": {
        "date": "2024-10-05",
        "summary": "配置文件清理报告，移除敏感信息和优化配置结构",
    },
    "docs/dev-notes/security/SECURITY_UPDATE_SUMMARY.md": {
        "date": "2024-10-08",
        "summary": "安全更新总结，包括漏洞修复和安全加固措施",
    },
    "docs/dev-notes/security/api_key_security.md": {
        "date": "2024-09-30",
        "summary": "API 密钥安全管理指南，包括存储、使用和轮换最佳实践",
    },
    "docs/dev-notes/security/TODO_SECURITY_CHECKLIST.md": {
        "date": "2024-10-01",
        "summary": "安全检查清单，包含代码审计、依赖扫描等待办事项",
    },
}


class MetadataFixer:
    """Dev-notes 元数据修复器"""

    def __init__(self, root_dir: Path | None = None):
        """
        初始化修复器

        Args:
            root_dir: 项目根目录，默认为当前目录
        """
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()

    def fix_file(self, filepath: str, metadata: dict[str, str]) -> bool:
        """
        为单个文件添加元数据

        Args:
            filepath: 相对于项目根目录的文件路径
            metadata: 元数据字典，包含 date 和 summary

        Returns:
            是否成功修复
        """
        path = self.root_dir / filepath

        if not path.exists():
            print(f"⚠️  文件不存在: {filepath}")
            return False

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️  读取文件失败: {filepath} - {e}")
            return False

        lines = content.split("\n")

        if not lines:
            print(f"⚠️  文件为空: {filepath}")
            return False

        # 检查是否已有元数据
        if "**Date**:" in content and "**Author**:" in content and "**Summary**:" in content:
            print(f"✓ 已有元数据: {filepath}")
            return True

        # 找到标题行
        title_line_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                title_line_idx = i
                break

        # 构造元数据
        metadata_lines = [
            "",
            f"**Date**: {metadata['date']}  ",
            "**Author**: SAGE Team  ",
            f"**Summary**: {metadata['summary']}",
            "",
            "---",
            "",
        ]

        # 插入元数据
        new_lines = lines[: title_line_idx + 1] + metadata_lines + lines[title_line_idx + 1 :]

        # 写回文件
        try:
            path.write_text("\n".join(new_lines), encoding="utf-8")
            print(f"✅ 已修复: {filepath}")
            return True
        except Exception as e:
            print(f"⚠️  写入文件失败: {filepath} - {e}")
            return False

    def fix_all(self, files_to_fix: dict[str, dict[str, str]] | None = None) -> dict[str, int]:
        """
        批量修复文件元数据

        Args:
            files_to_fix: 要修复的文件字典，默认使用 DEFAULT_FILES_TO_FIX

        Returns:
            修复统计字典 {'success': 成功数, 'failed': 失败数, 'skipped': 跳过数}
        """
        if files_to_fix is None:
            files_to_fix = DEFAULT_FILES_TO_FIX

        print("🔧 批量修复 dev-notes 文档元数据")
        print(f"📝 需要修复 {len(files_to_fix)} 个文件\n")

        stats = {"success": 0, "failed": 0, "skipped": 0}

        for filepath, metadata in files_to_fix.items():
            result = self.fix_file(filepath, metadata)
            if result:
                # 检查是否是跳过（已有元数据）
                if "已有元数据" in str(result):
                    stats["skipped"] += 1
                else:
                    stats["success"] += 1
            else:
                stats["failed"] += 1

        print("\n" + "=" * 80)
        print(f"✅ 成功修复: {stats['success']}")
        print(f"⏭️  已跳过: {stats['skipped']}")
        print(f"❌ 失败: {stats['failed']}")
        print("=" * 80)

        return stats

    def scan_and_fix(self, devnotes_dir: Path | None = None) -> dict[str, int]:
        """
        扫描 dev-notes 目录并修复缺失元数据的文件

        Args:
            devnotes_dir: dev-notes 目录路径，默认为 docs/dev-notes

        Returns:
            修复统计字典
        """
        if devnotes_dir is None:
            devnotes_dir = self.root_dir / "docs" / "dev-notes"

        if not devnotes_dir.exists():
            print(f"⚠️  目录不存在: {devnotes_dir}")
            return {"success": 0, "failed": 0, "skipped": 0}

        # 扫描所有 markdown 文件
        all_files = list(devnotes_dir.rglob("*.md"))
        all_files = [f for f in all_files if f.name not in ["README.md", "TEMPLATE.md"]]

        files_need_fix = {}

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                # 检查是否缺少元数据
                if not ("**Date**:" in content and "**Summary**:" in content):
                    rel_path = file_path.relative_to(self.root_dir)
                    # 生成默认元数据
                    files_need_fix[str(rel_path)] = {
                        "date": "2024-01-01",  # 默认日期
                        "summary": "待补充文档摘要",  # 默认摘要
                    }
            except Exception:
                continue

        if not files_need_fix:
            print("✅ 所有文件都有完整的元数据！")
            return {"success": 0, "failed": 0, "skipped": len(all_files)}

        print(f"📋 发现 {len(files_need_fix)} 个文件缺少元数据")
        print("⚠️  这些文件将使用默认元数据，请手动更新")
        print()

        return self.fix_all(files_need_fix)
