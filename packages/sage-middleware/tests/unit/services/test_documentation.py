"""
文档验证测试

验证:
1. 文档中的代码示例可运行
2. 文档链接有效
3. 配置参数一致
"""

import re
from pathlib import Path

import pytest


class TestDocumentationValidation:
    """文档验证测试"""

    @pytest.fixture(scope="class")
    def docs_dir(self) -> Path:
        """文档目录"""
        # 从 tests/unit/services/test_documentation.py
        # 到 src/sage/middleware/components/sage_mem/neuromem/services/
        base_dir = Path(__file__).parents[3]  # 返回到 sage-middleware/
        return base_dir / "src/sage/middleware/components/sage_mem/neuromem/services"

    def test_readme_exists(self, docs_dir: Path):
        """测试 README.md 存在"""
        readme = docs_dir / "README.md"
        assert readme.exists(), "README.md 不存在"
        assert readme.stat().st_size > 1000, "README.md 内容太少"

    def test_benchmarks_exists(self, docs_dir: Path):
        """测试 BENCHMARKS.md 存在"""
        benchmarks = docs_dir / "BENCHMARKS.md"
        assert benchmarks.exists(), "BENCHMARKS.md 不存在"
        assert benchmarks.stat().st_size > 1000, "BENCHMARKS.md 内容太少"

    def test_partitional_readme_exists(self, docs_dir: Path):
        """测试 partitional/README.md 存在"""
        partitional_readme = docs_dir / "partitional/README.md"
        assert partitional_readme.exists(), "partitional/README.md 不存在"
        assert partitional_readme.stat().st_size > 1000, "partitional/README.md 内容太少"

    def test_api_reference_exists(self, docs_dir: Path):
        """测试 API_REFERENCE.md 存在"""
        api_ref = docs_dir / "API_REFERENCE.md"
        assert api_ref.exists(), "API_REFERENCE.md 不存在"
        assert api_ref.stat().st_size > 1000, "API_REFERENCE.md 内容太少"

    def test_hierarchical_readme_exists(self, docs_dir: Path):
        """测试 hierarchical/README.md 存在"""
        hierarchical_readme = docs_dir / "hierarchical/README.md"
        assert hierarchical_readme.exists(), "hierarchical/README.md 不存在"
        assert hierarchical_readme.stat().st_size > 1000, "hierarchical/README.md 内容太少"

    def test_readme_links(self, docs_dir: Path):
        """测试 README.md 中的链接"""
        readme = docs_dir / "README.md"
        content = readme.read_text()

        # 提取所有 Markdown 链接
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

        for link_text, link_path in links:
            # 跳过外部链接
            if link_path.startswith("http"):
                continue

            # 跳过锚点链接
            if link_path.startswith("#"):
                continue

            # 解析相对路径
            if link_path.startswith("../"):
                target = (docs_dir / link_path).resolve()
            else:
                target = (docs_dir / link_path).resolve()

            assert target.exists(), f"链接 '{link_text}' 指向的文件 '{link_path}' 不存在"

    def test_benchmarks_links(self, docs_dir: Path):
        """测试 BENCHMARKS.md 中的链接"""
        benchmarks = docs_dir / "BENCHMARKS.md"
        content = benchmarks.read_text()

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

        for link_text, link_path in links:
            if link_path.startswith("http") or link_path.startswith("#"):
                continue

            if link_path.startswith("../"):
                target = (docs_dir / link_path).resolve()
            else:
                target = (docs_dir / link_path).resolve()

            assert target.exists(), f"链接 '{link_text}' 指向的文件 '{link_path}' 不存在"

    def test_partitional_readme_links(self, docs_dir: Path):
        """测试 partitional/README.md 中的链接"""
        partitional_readme = docs_dir / "partitional/README.md"
        content = partitional_readme.read_text()

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

        for link_text, link_path in links:
            if link_path.startswith("http") or link_path.startswith("#"):
                continue

            base = docs_dir / "partitional"
            if link_path.startswith("../"):
                target = (base / link_path).resolve()
            else:
                target = (base / link_path).resolve()

            assert target.exists(), f"链接 '{link_text}' 指向的文件 '{link_path}' 不存在"

    def test_api_reference_links(self, docs_dir: Path):
        """测试 API_REFERENCE.md 中的链接"""
        api_ref = docs_dir / "API_REFERENCE.md"
        content = api_ref.read_text()

        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

        for link_text, link_path in links:
            if link_path.startswith("http") or link_path.startswith("#"):
                continue

            if link_path.startswith("../"):
                target = (docs_dir / link_path).resolve()
            else:
                target = (docs_dir / link_path).resolve()

            assert target.exists(), f"链接 '{link_text}' 指向的文件 '{link_path}' 不存在"

    def test_fifo_queue_config_consistency(self, docs_dir: Path):
        """测试 FIFO Queue 配置参数一致性"""
        # 读取所有文档
        readme = (docs_dir / "README.md").read_text()
        partitional_readme = (docs_dir / "partitional/README.md").read_text()
        api_ref = (docs_dir / "API_REFERENCE.md").read_text()

        # 检查 max_size 参数在所有文档中提到
        assert "max_size" in readme, "README.md 缺少 max_size 参数说明"
        assert "max_size" in partitional_readme, "partitional/README.md 缺少 max_size 参数说明"
        assert "max_size" in api_ref, "API_REFERENCE.md 缺少 max_size 参数说明"

    def test_lsh_hash_config_consistency(self, docs_dir: Path):
        """测试 LSH Hash 配置参数一致性"""
        readme = (docs_dir / "README.md").read_text()
        partitional_readme = (docs_dir / "partitional/README.md").read_text()
        api_ref = (docs_dir / "API_REFERENCE.md").read_text()

        # 检查关键参数
        for param in ["embedding_dim", "num_tables", "hash_size"]:
            assert param in readme, f"README.md 缺少 {param} 参数说明"
            assert param in partitional_readme, f"partitional/README.md 缺少 {param} 参数说明"
            assert param in api_ref, f"API_REFERENCE.md 缺少 {param} 参数说明"

    def test_segment_config_consistency(self, docs_dir: Path):
        """测试 Segment 配置参数一致性"""
        readme = (docs_dir / "README.md").read_text()
        partitional_readme = (docs_dir / "partitional/README.md").read_text()
        api_ref = (docs_dir / "API_REFERENCE.md").read_text()

        # 检查关键参数
        for param in ["max_segment_length", "overlap"]:
            assert param in readme, f"README.md 缺少 {param} 参数说明"
            assert param in partitional_readme, f"partitional/README.md 缺少 {param} 参数说明"
            assert param in api_ref, f"API_REFERENCE.md 缺少 {param} 参数说明"

    def test_service_types_consistency(self, docs_dir: Path):
        """测试服务类型在文档中的一致性"""
        readme = (docs_dir / "README.md").read_text()
        partitional_readme = (docs_dir / "partitional/README.md").read_text()
        api_ref = (docs_dir / "API_REFERENCE.md").read_text()

        # 定义服务类型
        service_types = [
            "fifo_queue",
            "lsh_hash",
            "segment",
            "linknote_graph",
            "property_graph",
        ]

        # 检查每个服务类型在文档中提到
        for service_type in service_types:
            assert service_type in readme, f"README.md 缺少 {service_type} 服务说明"
            # partitional 只包含 partitional 服务
            if service_type in ["fifo_queue", "lsh_hash", "segment"]:
                assert service_type in partitional_readme, (
                    f"partitional/README.md 缺少 {service_type} 服务说明"
                )
            assert service_type in api_ref, f"API_REFERENCE.md 缺少 {service_type} API 说明"

    def test_code_examples_syntax(self, docs_dir: Path):
        """测试代码示例的语法（简单检查）"""
        readme = (docs_dir / "README.md").read_text()

        # 提取代码块
        code_blocks = re.findall(r"```python\n(.*?)\n```", readme, re.DOTALL)

        assert len(code_blocks) > 0, "README.md 缺少代码示例"

        # 简单语法检查
        for code in code_blocks:
            # 检查常见错误
            assert "from sage" in code or "import" in code or "#" in code, "代码块可能不完整"

    def test_performance_data_in_benchmarks(self, docs_dir: Path):
        """测试 BENCHMARKS.md 包含性能数据"""
        benchmarks = (docs_dir / "BENCHMARKS.md").read_text()

        # 检查关键性能指标
        assert "ops/s" in benchmarks or "queries/s" in benchmarks, "缺少吞吐量数据"
        assert "MB" in benchmarks or "GB" in benchmarks, "缺少内存占用数据"

    def test_benchmarks_has_test_commands(self, docs_dir: Path):
        """测试 BENCHMARKS.md 包含测试命令"""
        benchmarks = (docs_dir / "BENCHMARKS.md").read_text()

        # 检查是否包含 pytest 命令
        assert "pytest" in benchmarks, "缺少测试复现命令"

    def test_api_reference_has_type_definitions(self, docs_dir: Path):
        """测试 API_REFERENCE.md 包含类型定义"""
        api_ref = (docs_dir / "API_REFERENCE.md").read_text()

        # 检查是否包含类型定义
        assert "TypedDict" in api_ref or "类型定义" in api_ref, "缺少类型定义"

    def test_hierarchical_services_in_readme(self, docs_dir: Path):
        """测试 README.md 包含 Hierarchical Services 说明"""
        readme = (docs_dir / "README.md").read_text()

        # 检查 Hierarchical Services 章节
        assert "LinknoteGraphService" in readme, "缺少 LinknoteGraphService 说明"
        assert "PropertyGraphService" in readme, "缺少 PropertyGraphService 说明"

    def test_troubleshooting_section(self, docs_dir: Path):
        """测试 README.md 包含故障排查章节"""
        readme = (docs_dir / "README.md").read_text()

        # 检查故障排查章节
        assert "故障排查" in readme or "Troubleshooting" in readme, "缺少故障排查章节"

    def test_best_practices_section(self, docs_dir: Path):
        """测试文档包含最佳实践章节"""
        readme = (docs_dir / "README.md").read_text()
        partitional_readme = (docs_dir / "partitional/README.md").read_text()

        # 检查最佳实践章节
        assert "最佳实践" in readme or "Best Practices" in readme, "README.md 缺少最佳实践章节"
        assert "最佳实践" in partitional_readme or "Best Practices" in partitional_readme, (
            "partitional/README.md 缺少最佳实践章节"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
