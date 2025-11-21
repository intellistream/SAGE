"""
Dev-notes 文档整理工具

帮助整理现有的 dev-notes 文档：
1. 分析文档内容
2. 建议分类目录
3. 检查元数据
4. 生成整理建议

从 tools/maintenance/helpers/devnotes_organizer.py 迁移

Author: SAGE Team
Date: 2025-10-27
"""

import re
from pathlib import Path

# 关键词到分类的映射
CATEGORY_KEYWORDS = {
    "architecture": [
        "architecture",
        "design",
        "system",
        "structure",
        "模块",
        "架构",
        "设计",
    ],
    "kernel": ["kernel", "runtime", "scheduler", "dispatcher", "内核"],
    "middleware": ["middleware", "operator", "component", "中间件", "组件"],
    "libs": ["lib", "library", "agent", "rag", "tool", "库"],
    "apps": ["app", "application", "应用"],
    "ci-cd": ["ci", "cd", "build", "workflow", "github", "action", "构建"],
    "performance": ["performance", "optimization", "speed", "性能", "优化"],
    "security": ["security", "vulnerability", "安全", "漏洞"],
    "testing": ["test", "testing", "pytest", "测试"],
    "deployment": ["deploy", "deployment", "install", "部署", "安装"],
    "migration": ["migration", "refactor", "cleanup", "迁移", "重构", "清理"],
    "tools": ["tool", "script", "cli", "工具", "脚本"],
}


class DevNotesOrganizer:
    """Dev-notes 文档整理器"""

    def __init__(self, root_dir: Path):
        """
        初始化整理器

        Args:
            root_dir: 项目根目录
        """
        self.root_dir = Path(root_dir)
        self.devnotes_dir = self.root_dir / "docs" / "dev-notes"

    def analyze_file(self, file_path: Path) -> dict:
        """
        分析单个文件

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return {
                "error": str(e),
                "suggested_category": "unknown",
                "has_metadata": False,
            }

        # 获取相对路径
        try:
            rel_path = file_path.relative_to(self.devnotes_dir)
        except ValueError:
            return {"error": "文件不在 dev-notes 目录中"}

        # 检查元数据
        has_date, has_author, has_summary = self._check_metadata(content)

        # 分析内容并建议分类
        suggested_category = self._suggest_category(file_path.name, content)

        # 检查文件大小
        file_size = len(content)

        return {
            "path": str(rel_path),
            "has_date": has_date,
            "has_author": has_author,
            "has_summary": has_summary,
            "suggested_category": suggested_category,
            "file_size": file_size,
            "is_empty": file_size < 100,
            "current_category": (rel_path.parts[0] if len(rel_path.parts) > 1 else "root"),
        }

    def _check_metadata(self, content: str) -> tuple[bool, bool, bool]:
        """
        检查文档元数据

        Args:
            content: 文档内容

        Returns:
            (has_date, has_author, has_summary) 元组
        """
        lines = content.split("\n")[:30]
        has_date = False
        has_author = False
        has_summary = False

        for line in lines:
            if re.search(r"\*?\*?Date\*?\*?\s*[:：]", line, re.IGNORECASE):
                has_date = True
            if re.search(r"\*?\*?Author\*?\*?\s*[:：]", line, re.IGNORECASE):
                has_author = True
            if re.search(r"\*?\*?Summary\*?\*?\s*[:：]", line, re.IGNORECASE):
                has_summary = True

        return has_date, has_author, has_summary

    def _suggest_category(self, filename: str, content: str) -> str:
        """
        根据文件名和内容建议分类

        Args:
            filename: 文件名
            content: 文件内容

        Returns:
            建议的分类名
        """
        # 转为小写用于匹配
        text = (filename + " " + content[:1000]).lower()

        # 统计每个分类的关键词匹配数
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[category] = score

        # 返回得分最高的分类
        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type,return-value]
        return "migration"  # 默认归为迁移类

    def analyze_all(self) -> list[dict]:
        """
        分析所有文档文件

        Returns:
            分析结果列表
        """
        all_files = list(self.devnotes_dir.rglob("*.md"))
        # 排除特殊文件
        all_files = [f for f in all_files if f.name not in ["README.md", "TEMPLATE.md"]]

        results = []
        for file_path in all_files:
            result = self.analyze_file(file_path)
            results.append(result)

        return results

    def generate_report(self, results: list[dict], verbose: bool = True) -> dict:
        """
        生成整理报告

        Args:
            results: 分析结果列表
            verbose: 是否打印详细信息

        Returns:
            报告数据字典
        """
        # 统计
        total = len(results)
        root_files = [r for r in results if r.get("current_category") == "root"]
        missing_metadata = [
            r
            for r in results
            if not (r.get("has_date") and r.get("has_author") and r.get("has_summary"))
        ]
        empty_files = [r for r in results if r.get("is_empty")]

        report_data = {
            "total": total,
            "root_files": root_files,
            "missing_metadata": missing_metadata,
            "empty_files": empty_files,
        }

        if verbose:
            self._print_report(report_data)

        return report_data

    def _print_report(self, report_data: dict) -> None:
        """打印报告"""
        total = report_data["total"]
        root_files = report_data["root_files"]
        missing_metadata = report_data["missing_metadata"]
        empty_files = report_data["empty_files"]

        print("=" * 80)
        print("📊 Dev-notes 文档整理报告")
        print("=" * 80)
        print()

        print(f"📁 总文件数: {total}")
        print(f"📂 根目录文件: {len(root_files)} ⚠️")
        print(f"📝 缺少元数据: {len(missing_metadata)}")
        print(f"🗑️  空文件/过小: {len(empty_files)}")
        print()

        # 根目录文件（需要移动）
        if root_files:
            print("=" * 80)
            print("⚠️  根目录文件（需要移动到分类目录）")
            print("=" * 80)
            print()
            for r in root_files:
                path = r.get("path")
                suggested = r.get("suggested_category", "unknown")
                print(f"📄 {path}")
                print(f"   建议分类: {suggested}/")
                print(
                    f"   移动命令: git mv docs/dev-notes/{path} docs/dev-notes/{suggested}/{path}"
                )
                print()

        # 空文件（建议删除）
        if empty_files:
            print("=" * 80)
            print("🗑️  空文件或内容过少（建议删除）")
            print("=" * 80)
            print()
            for r in empty_files:
                path = r.get("path")
                size = r.get("file_size", 0)
                print(f"📄 {path} ({size} bytes)")
                print(f"   删除命令: git rm docs/dev-notes/{path}")
                print()

        # 缺少元数据的文件
        if missing_metadata:
            print("=" * 80)
            print("📝 缺少元数据的文件（需要补充）")
            print("=" * 80)
            print()
            for r in missing_metadata[:10]:  # 只显示前10个
                if r.get("is_empty"):
                    continue  # 空文件已在上面列出
                path = r.get("path")
                missing = []
                if not r.get("has_date"):
                    missing.append("Date")
                if not r.get("has_author"):
                    missing.append("Author")
                if not r.get("has_summary"):
                    missing.append("Summary")
                print(f"📄 {path}")
                print(f"   缺少字段: {', '.join(missing)}")
                print()

            if len(missing_metadata) > 10:
                print(f"... 还有 {len(missing_metadata) - 10} 个文件")
                print()

        # 生成清理脚本
        print("=" * 80)
        print("🔧 自动化清理脚本")
        print("=" * 80)
        print()
        print("# 删除空文件")
        for r in empty_files:
            path = r.get("path")
            print(f'git rm "docs/dev-notes/{path}"')
        print()
        print("# 移动根目录文件到建议的分类")
        for r in root_files:
            if r.get("is_empty"):
                continue  # 空文件已标记删除
            path = r.get("path")
            suggested = r.get("suggested_category", "migration")
            # 创建目标目录（如果不存在）
            print(f'mkdir -p "docs/dev-notes/{suggested}"')
            print(f'git mv "docs/dev-notes/{path}" "docs/dev-notes/{suggested}/{path}"')
        print()

        # 总结
        print("=" * 80)
        print("📋 整理建议")
        print("=" * 80)
        print()
        print(f"1. 删除 {len(empty_files)} 个空文件或内容过少的文件")
        print(
            f"2. 移动 {len([r for r in root_files if not r.get('is_empty')])} 个根目录文件到分类目录"
        )
        print(f"3. 为 {len(missing_metadata)} 个文件补充元数据")
        print()
        print("💡 提示:")
        print("  - 复制上面的命令到终端执行")
        print("  - 或者使用 sage-dev maintenance fix-metadata 自动修复")
        print("  - 重要文档可以移动到 docs-public 下")
        print()
