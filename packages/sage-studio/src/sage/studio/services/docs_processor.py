"""SAGE 文档处理器 - 用于微调数据准备"""

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SAGEDocsProcessor:
    """处理 SAGE 官方文档，转换为微调训练数据"""

    DOCS_REPO_URL = "https://github.com/intellistream/SAGE-Pub.git"
    DOCS_BRANCH = "main"
    DOCS_PATH = "docs_src"

    def __init__(self, output_dir: Path | None = None):
        """
        Args:
            output_dir: 输出目录，默认为 ~/.sage/studio_finetune/sage_docs
        """
        if output_dir is None:
            output_dir = Path.home() / ".sage" / "studio_finetune" / "sage_docs"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_docs(self, force_refresh: bool = False) -> Path:
        """
        从 GitHub 下载 SAGE 文档

        Args:
            force_refresh: 是否强制重新下载

        Returns:
            文档目录路径
        """
        docs_dir = self.output_dir / "raw_docs"

        if docs_dir.exists() and not force_refresh:
            logger.info(f"SAGE docs already exist at {docs_dir}")
            return docs_dir / self.DOCS_PATH

        # 使用 sparse checkout 只下载 docs_src 目录
        import subprocess

        logger.info("Downloading SAGE docs from GitHub...")

        # 清理旧文件
        if docs_dir.exists():
            shutil.rmtree(docs_dir)

        docs_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 初始化 git repo
            subprocess.run(["git", "init"], cwd=docs_dir, check=True, capture_output=True)

            # 配置 sparse checkout
            subprocess.run(
                ["git", "config", "core.sparseCheckout", "true"],
                cwd=docs_dir,
                check=True,
                capture_output=True,
            )

            # 指定只下载 docs_src
            sparse_file = docs_dir / ".git" / "info" / "sparse-checkout"
            sparse_file.parent.mkdir(parents=True, exist_ok=True)
            sparse_file.write_text(f"{self.DOCS_PATH}\n")

            # 添加远程仓库
            subprocess.run(
                ["git", "remote", "add", "origin", self.DOCS_REPO_URL],
                cwd=docs_dir,
                check=True,
                capture_output=True,
            )

            # 拉取指定分支
            logger.info(f"Fetching branch: {self.DOCS_BRANCH}")
            subprocess.run(
                ["git", "pull", "--depth=1", "origin", self.DOCS_BRANCH],
                cwd=docs_dir,
                check=True,
                capture_output=True,
                timeout=120,  # 2分钟超时
            )

            docs_path = docs_dir / self.DOCS_PATH
            if not docs_path.exists():
                raise RuntimeError(f"Failed to download docs: {self.DOCS_PATH} not found")

            logger.info(f"✅ SAGE docs downloaded to {docs_path}")
            return docs_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            raise RuntimeError(f"Failed to download SAGE docs: {e}")
        except Exception as e:
            logger.error(f"Download error: {e}")
            raise

    def convert_markdown_to_qa(self, md_content: str, file_name: str) -> list[dict[str, str]]:
        """
        将 Markdown 内容转换为 QA 格式

        策略：
        1. 按照标题分段
        2. 每个段落生成一个 instruction-output 对
        3. instruction 为 "关于 {topic} 的问题"
        4. output 为段落内容
        """
        qa_pairs = []

        # 提取标题和内容
        sections = self._split_by_headers(md_content)

        for section_title, section_content in sections:
            # 清理内容
            cleaned_content = self._clean_markdown(section_content)

            if len(cleaned_content.strip()) < 50:  # 跳过太短的内容
                continue

            # 生成 instruction
            if section_title:
                instruction = f"请介绍 SAGE 框架中关于 {section_title} 的内容"
            else:
                # 从文件名生成
                topic = file_name.replace("-", " ").replace(".md", "")
                instruction = f"请介绍 SAGE 框架中 {topic} 的相关内容"

            qa_pairs.append(
                {
                    "instruction": instruction,
                    "input": "",
                    "output": cleaned_content,
                }
            )

        return qa_pairs

    def _split_by_headers(self, md_content: str) -> list[tuple[str, str]]:
        """按照 Markdown 标题分割内容"""
        sections = []
        current_title = ""
        current_content = []

        lines = md_content.split("\n")

        for line in lines:
            # 检测标题 (# 或 ##)
            header_match = re.match(r"^(#{1,3})\s+(.+)$", line)

            if header_match:
                # 保存上一个段落
                if current_content:
                    sections.append((current_title, "\n".join(current_content)))

                # 开始新段落
                current_title = header_match.group(2).strip()
                current_content = []
            else:
                current_content.append(line)

        # 添加最后一个段落
        if current_content:
            sections.append((current_title, "\n".join(current_content)))

        return sections

    def _clean_markdown(self, content: str) -> str:
        """清理 Markdown 格式，保留可读性"""
        # 移除代码块标记但保留代码内容
        content = re.sub(r"```[a-z]*\n", "", content)
        content = content.replace("```", "")

        # 移除图片引用
        content = re.sub(r"!\[.*?\]\(.*?\)", "", content)

        # 移除链接但保留文本
        content = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", content)

        # 清理多余空行
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def prepare_training_data(self, force_refresh: bool = False) -> Path:
        """
        准备训练数据（完整流程）

        Args:
            force_refresh: 是否重新下载文档

        Returns:
            训练数据 JSON 文件路径
        """
        logger.info("Starting SAGE docs preparation for fine-tuning...")

        # 1. 下载文档
        docs_path = self.download_docs(force_refresh=force_refresh)

        # 2. 遍历所有 Markdown 文件
        all_qa_pairs = []
        md_files = list(docs_path.rglob("*.md"))

        logger.info(f"Found {len(md_files)} markdown files")

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                qa_pairs = self.convert_markdown_to_qa(content, md_file.stem)
                all_qa_pairs.extend(qa_pairs)
                logger.debug(f"Processed {md_file.name}: {len(qa_pairs)} QA pairs")
            except Exception as e:
                logger.warning(f"Failed to process {md_file}: {e}")
                continue

        # 3. 保存为 Alpaca 格式 JSON
        output_file = self.output_dir / "sage_docs_finetune_data.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_qa_pairs, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Training data prepared: {output_file}")
        logger.info(f"   Total QA pairs: {len(all_qa_pairs)}")

        return output_file

    def get_stats(self, data_file: Path) -> dict[str, Any]:
        """获取数据集统计信息"""
        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        total_chars = sum(len(item["output"]) for item in data)
        avg_chars = total_chars / len(data) if data else 0

        return {
            "total_samples": len(data),
            "total_chars": total_chars,
            "avg_chars_per_sample": int(avg_chars),
            "estimated_tokens": int(total_chars / 4),  # 粗略估计（1 token ≈ 4 chars）
        }


# 单例实例
_processor_instance = None


def get_docs_processor() -> SAGEDocsProcessor:
    """获取文档处理器单例"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = SAGEDocsProcessor()
    return _processor_instance
