#!/usr/bin/env python3
"""
批量修复 dev-notes 文档元数据

⚠️ 此脚本已迁移到 sage-tools 包
📝 新位置: packages/sage-tools/src/sage/tools/dev/maintenance/metadata_fixer.py
🚀 新用法: sage-dev maintenance fix-metadata

保留此文件以便向后兼容
"""

import sys
import warnings

warnings.warn(
    "此脚本已迁移到 sage-tools 包。"
    "请使用: sage-dev maintenance fix-metadata",
    DeprecationWarning,
    stacklevel=2,
)

print("=" * 80)
print("⚠️  此脚本已迁移到 sage-tools 包")
print("=" * 80)
print()
print("新的使用方式:")
print("  sage-dev maintenance fix-metadata")
print()
print("或使用 Python API:")
print("  from sage.tools.dev.maintenance import MetadataFixer")
print("  fixer = MetadataFixer(root_dir)")
print("  fixer.fix_all()")
print()
print("继续使用旧脚本...")
print()

# 尝试导入新模块
try:
    from pathlib import Path
    from sage.tools.dev.maintenance import MetadataFixer

    root = Path.cwd()
    fixer = MetadataFixer(root)
    fixer.fix_all()
    sys.exit(0)
except ImportError:
    print("❌ 无法导入新模块，请安装 sage-tools:")
    print("  pip install -e packages/sage-tools")
    sys.exit(1)

# 原始代码保留（以防万一）
from pathlib import Path

# 需要修复的文件列表（从错误日志中提取）
FILES_TO_FIX = {
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
    # archive/2025-restructuring/ (批量处理)
    "docs/dev-notes/archive/2025-restructuring/TEST_COVERAGE_IMPROVEMENT_PLAN.md": {
        "date": "2025-01-20",
        "summary": "测试覆盖率提升计划",
    },
    "docs/dev-notes/archive/2025-restructuring/PACKAGE_RESTRUCTURING_ANALYSIS.md": {
        "date": "2025-01-18",
        "summary": "包结构重构分析",
    },
    "docs/dev-notes/archive/2025-restructuring/TOP_LAYER_REVIEW_2025.md": {
        "date": "2025-01-15",
        "summary": "顶层架构评审",
    },
    "docs/dev-notes/archive/2025-restructuring/TOP_LAYER_REVIEW_SUMMARY.md": {
        "date": "2025-01-15",
        "summary": "顶层架构评审总结",
    },
    "docs/dev-notes/archive/2025-restructuring/TEST_COVERAGE_REPORT_TOP_LAYERS.md": {
        "date": "2025-01-20",
        "summary": "顶层测试覆盖率报告",
    },
    "docs/dev-notes/archive/2025-restructuring/WORKFLOW_OPTIMIZER_DESIGN_2025.md": {
        "date": "2025-01-22",
        "summary": "工作流优化器设计",
    },
    "docs/dev-notes/archive/2025-restructuring/FULL_TEST_SUITE_REPORT.md": {
        "date": "2025-01-22",
        "summary": "完整测试套件报告",
    },
    "docs/dev-notes/archive/2025-restructuring/RESTRUCTURING_SUMMARY.md": {
        "date": "2025-01-22",
        "summary": "重构总结",
    },
    "docs/dev-notes/archive/2025-restructuring/PACKAGE_RESTRUCTURING_FINAL.md": {
        "date": "2025-01-22",
        "summary": "包重构最终方案",
    },
    "docs/dev-notes/archive/2025-restructuring/TEST_STATUS_REPORT.md": {
        "date": "2025-01-20",
        "summary": "测试状态报告",
    },
    "docs/dev-notes/archive/2025-restructuring/REFACTORING_SUMMARY_2025-01-22.md": {
        "date": "2025-01-22",
        "summary": "重构总结",
    },
    "docs/dev-notes/archive/2025-restructuring/TEST_MIGRATION_PLAN_L2_PLATFORM.md": {
        "date": "2025-01-18",
        "summary": "L2 Platform 层测试迁移计划",
    },
    "docs/dev-notes/archive/2025-restructuring/TEST_MIGRATION_SUMMARY_L2_PLATFORM.md": {
        "date": "2025-01-18",
        "summary": "L2 Platform 层测试迁移总结",
    },
    "docs/dev-notes/archive/2025-restructuring/STUDIO_ARCHITECTURE_REFACTOR.md": {
        "date": "2025-01-20",
        "summary": "Studio 架构重构",
    },
}


def fix_file_metadata(filepath: str, metadata: dict):
    """为文件添加元数据"""
    path = Path(filepath)

    if not path.exists():
        print(f"⚠️  文件不存在: {filepath}")
        return False

    content = path.read_text(encoding="utf-8")
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
    path.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"✅ 已修复: {filepath}")
    return True


def main():
    print("🔧 批量修复 dev-notes 文档元数据")
    print(f"📝 需要修复 {len(FILES_TO_FIX)} 个文件\n")

    success_count = 0
    fail_count = 0

    for filepath, metadata in FILES_TO_FIX.items():
        if fix_file_metadata(filepath, metadata):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"✅ 成功修复: {success_count}")
    print(f"❌ 失败: {fail_count}")
    print("=" * 80)


if __name__ == "__main__":
    main()
