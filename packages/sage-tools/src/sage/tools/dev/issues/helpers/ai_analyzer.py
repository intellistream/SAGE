#!/usr/bin/env python3
"""
AI 分析器（简化实现）
接受 --mode 参数：duplicates | labels | priority | comprehensive
参考 legacy 实现，提供本地 issues 的简单分析功能并输出到 output/ 目录
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# 动态导入config模块
try:
    # 尝试相对导入（当作为模块运行时）
    from ..config import IssuesConfig
except ImportError:
    # 如果相对导入失败，使用绝对导入
    sys.path.insert(0, str(SCRIPT_DIR.parent))
    from config import IssuesConfig
config = IssuesConfig()


def load_local_issues():
    """从 workspace/issues 目录加载本地保存的 issue markdown 文件为简化字典列表"""
    issues_dir = config.workspace_path / "issues"
    issues = []
    if not issues_dir.exists():
        print(f"⚠️ 未找到本地 issues 目录: {issues_dir}")
        return issues

    for f in issues_dir.rglob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            # 简单解析标题和编号
            first_line = text.splitlines()[0] if text else ""
            title = first_line.lstrip("# ").strip()
            # try get number from filename
            name = f.name
            number = None
            parts = name.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                number = int(parts[1])

            issues.append({"number": number, "title": title, "path": str(f)})
        except Exception:
            continue

    return issues


def detect_duplicates(issues: list):
    """基于标题的简单重复检测（子串/词交集）"""
    dup_pairs = []
    for i in range(len(issues)):
        for j in range(i + 1, len(issues)):
            t1 = issues[i]["title"].lower() if issues[i]["title"] else ""
            t2 = issues[j]["title"].lower() if issues[j]["title"] else ""
            if not t1 or not t2:
                continue
            # 子串检查
            if t1 in t2 or t2 in t1:
                dup_pairs.append((issues[i], issues[j], "substring"))
                continue
            # 词交集
            s1 = {w for w in re.split(r"\W+", t1) if w}
            s2 = {w for w in re.split(r"\W+", t2) if w}
            if not s1 or not s2:
                continue
            inter = s1.intersection(s2)
            jaccard = len(inter) / max(len(s1.union(s2)), 1)
            if jaccard > 0.5:
                dup_pairs.append((issues[i], issues[j], f"jaccard={jaccard:.2f}"))
    return dup_pairs


def suggest_label_optimizations(issues: list):
    """基于标题关键词做简易标签推荐（示例）"""
    keyword_map = {
        "bug": ["bug", "error", "fail", "exception"],
        "performance": ["slow", "performance", "latency"],
        "docs": ["doc", "documentation", "readme"],
        "api": ["api", "endpoint", "request"],
    }
    suggestions = []
    for issue in issues:
        title = (issue.get("title") or "").lower()
        recs = set()
        for label, keys in keyword_map.items():
            for k in keys:
                if k in title:
                    recs.add(label)
        if recs:
            suggestions.append(
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "recommend": list(recs),
                }
            )
    return suggestions


def assess_priority(issues: list):
    """根据简单规则评估优先级（示例）"""
    results = []
    for issue in issues:
        title = (issue.get("title") or "").lower()
        priority = "low"
        if any(k in title for k in ("critical", "urgent", "blocker")):
            priority = "high"
        elif any(k in title for k in ("important", "major", "failure")):
            priority = "medium"
        results.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "priority": priority,
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description="AI 智能分析 Issues")
    parser.add_argument(
        "--mode",
        choices=["duplicates", "labels", "priority", "comprehensive"],
        required=True,
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    issues = load_local_issues()
    if not issues:
        print("⚠️ 未找到本地Issues，先运行下载功能")
        return

    if args.mode == "duplicates":
        dups = detect_duplicates(issues)
        print(f"找到 {len(dups)} 组可能的重复Items")
        for a, b, reason in dups:
            print(
                f" - #{a.get('number')} {a.get('title')[:80]} <-> #{b.get('number')} {b.get('title')[:80]} ({reason})"
            )
        # 写入报告
        out = config.output_path / f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# 重复Issues分析\n\n共 {len(dups)} 组\n\n")
            for a, b, reason in dups:
                f.write(
                    f"- #{a.get('number')} {a.get('title')} <-> #{b.get('number')} {b.get('title')} ({reason})\n"
                )
        print(f"报告已保存: {out}")

    elif args.mode == "labels":
        suggestions = suggest_label_optimizations(issues)
        print(f"为 {len(suggestions)} 个Issues 推荐标签")
        out = (
            config.output_path / f"label_suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# 标签优化建议\n\n共 {len(suggestions)} 条建议\n\n")
            for s in suggestions:
                f.write(
                    f"- #{s.get('number')}: {s.get('title')} -> {', '.join(s.get('recommend', []))}\n"
                )
        print(f"报告已保存: {out}")

    elif args.mode == "priority":
        res = assess_priority(issues)
        out = (
            config.output_path
            / f"priority_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# 优先级评估\n\n共 {len(res)} 条\n\n")
            for r in res:
                f.write(f"- #{r.get('number')}: {r.get('title')} -> {r.get('priority')}\n")
        print(f"报告已保存: {out}")

    elif args.mode == "comprehensive":
        print("执行综合分析: 调用 duplicates + labels + priority")
        # 逐个运行并合并报告
        # 为简单起见，分别生成三个报告
        for m in ("duplicates", "labels", "priority"):
            sys.argv = [sys.argv[0], "--mode", m]
            main()


if __name__ == "__main__":
    main()
