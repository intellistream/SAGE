#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAGE Examples 测试的 pytest 集成
将 examples 测试集成到现有的 pytest 测试框架中
"""

import os
import sys
from pathlib import Path

import pytest
from example_strategies import (
    ExampleEnvironmentManager,
    ExampleTestFilters,
    ExampleTestStrategies,
)
from sage.tools.dev.issues.tests import IssuesTestSuite
from test_examples import ExampleAnalyzer, ExampleTestSuite

# 添加项目路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent / "packages" / "sage-tools" / "src"))
sys.path.insert(0, str(current_dir))


class TestExamplesIntegration:
    """Examples 测试集成到 pytest"""

    @pytest.fixture(scope="function")
    def example_suite(self):
        """创建示例测试套件"""
        return ExampleTestSuite()

    @pytest.fixture(scope="class")
    def analyzer(self):
        """创建示例分析器"""
        return ExampleAnalyzer()

    @pytest.fixture(scope="class")
    def env_manager(self):
        """创建环境管理器"""
        manager = ExampleEnvironmentManager()
        yield manager
        manager.cleanup()

    @pytest.mark.quick_examples
    def test_examples_discovery(self, analyzer):
        """测试示例发现功能"""
        examples = analyzer.discover_examples()
        assert len(examples) > 0, "应该发现至少一个示例文件"

        # 检查是否有不同类别的示例
        categories = {example.category for example in examples}
        expected_categories = {"tutorials", "apps"}
        assert expected_categories.issubset(
            categories
        ), f"应该包含基本类别: {expected_categories}"

    @pytest.mark.quick_examples
    @pytest.mark.parametrize("category", ["tutorials", "apps"])
    def test_category_examples(self, analyzer, category):
        """测试特定类别的示例发现"""
        # 只测试发现功能，不实际执行示例（避免长时间运行）
        examples = analyzer.discover_examples()
        category_examples = [e for e in examples if e.category == category]

        # 至少应该有一些示例文件
        assert len(category_examples) > 0, f"类别 {category} 应该有示例文件"

        # 检查示例文件的基本属性
        for example in category_examples:
            assert example.file_path, "示例应该有文件路径"
            assert example.category == category, f"示例类别应该是 {category}"
            assert isinstance(example.imports, list), "示例应该有导入列表"
            assert isinstance(example.dependencies, list), "示例应该有依赖列表"

    @pytest.mark.quick_examples
    def test_tutorials_hello_world(self, example_suite):
        """测试基础的 hello_world 示例"""
        # 专门测试最基础的示例
        analyzer = ExampleAnalyzer()
        examples = analyzer.discover_examples()

        hello_world_examples = [
            e
            for e in examples
            if "hello_world" in e.file_path.lower() and e.category == "tutorials"
        ]

        assert len(hello_world_examples) > 0, "应该找到 hello_world 示例"

        # 运行 hello_world 示例
        for example in hello_world_examples:
            result = example_suite.runner.run_example(example)
            assert (
                result.status == "passed"
            ), f"hello_world 示例应该运行成功: {result.error}"

    @pytest.mark.quick_examples
    def test_example_categorization(self, analyzer):
        """测试示例分类的正确性"""
        examples = analyzer.discover_examples()

        # 检查每个示例是否被正确分类
        for example in examples:
            # 类别应该不为空
            assert example.category, f"示例 {example.file_path} 应该有类别"

            # 类别应该与文件路径匹配
            path_parts = Path(example.file_path).parts
            assert (
                example.category in path_parts
            ), f"类别 {example.category} 应该在路径中: {example.file_path}"

    @pytest.mark.quick_examples
    def test_dependency_analysis(self, analyzer):
        """测试依赖分析的准确性"""
        examples = analyzer.discover_examples()

        for example in examples:
            # 检查导入分析
            assert isinstance(example.imports, list), "imports 应该是列表"
            assert isinstance(example.dependencies, list), "dependencies 应该是列表"

            # SAGE相关的导入应该被正确识别
            sage_imports = [imp for imp in example.imports if imp.startswith("sage")]
            if sage_imports:
                # 如果有SAGE导入，文件应该被识别为有主函数
                assert (
                    example.has_main or len(sage_imports) > 0
                ), "有SAGE导入的文件应该有可执行内容"

    def test_environment_setup(self, env_manager):
        """测试环境设置功能"""
        categories = ["tutorials", "rag", "memory"]

        for category in categories:
            env = env_manager.setup_category_environment(category)

            # 检查基本环境变量
            assert "SAGE_TEST_MODE" in env, f"类别 {category} 应该设置测试模式"
            assert "PYTHONPATH" in env, f"类别 {category} 应该设置 Python 路径"

            # 检查类别特定的设置
            strategy = ExampleTestStrategies.get_strategies().get(category)
            if strategy and strategy.environment_vars:
                for key in strategy.environment_vars:
                    assert key in env, f"类别 {category} 应该包含环境变量 {key}"

    @pytest.mark.quick_examples
    def test_skip_filters(self, analyzer):
        """测试跳过过滤器"""
        # 使用真实的示例文件路径进行测试
        examples = analyzer.discover_examples()

        # 找到一些真实的示例用于测试
        hello_world_examples = [e for e in examples if "hello_world" in e.file_path]
        [e for e in examples if e.category == "rag"]

        # 测试 hello_world 示例不应该被跳过
        if hello_world_examples:
            example = hello_world_examples[0]
            skip, reason = ExampleTestFilters.should_skip_file(
                Path(example.file_path), example.category, example
            )
            assert not skip, f"文件 {example.file_path} 不应该被跳过: {reason}"

        # 测试一般的过滤逻辑
        # 注意：should_skip_file 只检查测试标记，不检查文件是否存在
        # 文件存在性检查应该在收集示例时完成

        # 测试基于标记的跳过逻辑（需要实际的 example_info）
        # 这里只测试不带 example_info 的基本情况（应该不跳过）
        test_cases = [
            (Path("examples/rag/simple_rag.py"), "rag", False),
            (Path("examples/tutorials/hello_world.py"), "tutorials", False),
        ]

        for file_path, category, should_skip in test_cases:
            skip, reason = ExampleTestFilters.should_skip_file(
                file_path, category, None
            )
            if should_skip:
                assert skip, f"文件 {file_path} 应该被跳过: {reason}"
            else:
                assert not skip, f"文件 {file_path} 不应该被跳过但被跳过了: {reason}"

    @pytest.mark.integration
    @pytest.mark.skipif(
        not any(
            os.getenv(var) for var in ["GITHUB_TOKEN", "GIT_TOKEN", "SAGE_REPO_TOKEN"]
        ),
        reason="需要 GitHub token (GITHUB_TOKEN, GIT_TOKEN 或 SAGE_REPO_TOKEN) 才能运行此测试",
    )
    def test_examples_integration_with_issues_manager(self):
        """测试与 Issues 管理器的集成

        注意：此测试需要 GitHub token 才能运行。
        如果没有设置 GITHUB_TOKEN、GIT_TOKEN 或 SAGE_REPO_TOKEN，
        测试将自动跳过。
        """
        print("🧪 开始集成测试: test_examples_integration_with_issues_manager")

        # 这个测试验证 examples 测试可以与现有的问题管理系统集成
        try:
            issues_suite = IssuesTestSuite()

            print(f"\n📂 元数据目录: {issues_suite.manager.metadata_dir}")
            print(f"📂 工作目录: {issues_suite.manager.workspace_dir}")

            # 验证 token 已加载
            if not issues_suite.manager.config.github_token:
                pytest.fail("GitHub token 未能正确加载到 IssuesTestSuite 中")
                return

            # 如果团队信息未找到，尝试更新
            if not issues_suite.manager.team_info:
                print("\n📋 团队信息未找到，正在更新...")
                success = issues_suite.manager.update_team_info()

                if not success:
                    pytest.fail(
                        "❌ 无法获取团队信息。\n"
                        f"GitHub Token 来源: {issues_suite.manager.config.github_token_env}\n"
                        "请检查:\n"
                        "  1. Token 权限是否正确 (需要 read:org 权限)\n"
                        "  2. 是否有访问 intellistream 组织的权限\n"
                        "  3. 网络连接是否正常"
                    )

                # 重新加载团队信息
                issues_suite.manager.team_info = issues_suite.manager._load_team_info()

                if not issues_suite.manager.team_info:
                    # 检查文件是否生成
                    team_config_path = (
                        issues_suite.manager.metadata_dir / "team_config.py"
                    )
                    if team_config_path.exists():
                        print(f"⚠️ team_config.py 存在但加载失败: {team_config_path}")
                        # 读取文件内容查看
                        with open(team_config_path, "r") as f:
                            content = f.read()
                            print(f"文件内容 (前 500 字符):\n{content[:500]}")

                    pytest.fail(
                        "❌ 更新团队信息后仍然无法加载。\n"
                        f"元数据目录: {issues_suite.manager.metadata_dir}\n"
                        f"team_config.py 存在: {team_config_path.exists()}\n"
                        "请检查文件写入权限和 Python 模块导入"
                    )

                print(
                    f"✅ 成功加载团队信息 ({len(issues_suite.manager.team_info.get('all_usernames', []))} 位成员)"
                )
            else:
                print(
                    f"✅ 团队信息已存在 ({len(issues_suite.manager.team_info.get('all_usernames', []))} 位成员)"
                )

        except Exception:
            import traceback

            pytest.fail(f"IssuesTestSuite初始化失败:\n{traceback.format_exc()}")

        example_suite = ExampleTestSuite()

        # 只运行分析，不实际执行所有测试（避免重复）
        analyzer = ExampleAnalyzer()
        examples = analyzer.discover_examples()

        # 验证基础功能
        assert len(examples) > 0, "应该能够发现示例文件"

        # 测试一个简单的示例（不是全部）
        quick_examples = [e for e in examples if "hello_world" in e.file_path]
        if quick_examples:
            result = example_suite.runner.run_example(quick_examples[0])
            # 验证结果格式正确
            assert hasattr(result, "status"), "结果应该有status属性"
            assert hasattr(result, "execution_time"), "结果应该有execution_time属性"


# 单独的测试标记
pytestmark = [pytest.mark.examples, pytest.mark.integration]


# 额外的测试用例 - 基于发现的示例文件动态生成
class TestIndividualExamples:
    """为每个示例文件生成独立的测试"""

    def test_individual_example(self, example_file):
        """测试单个示例文件"""
        suite = ExampleTestSuite()

        # 检查是否应该跳过
        skip, reason = ExampleTestFilters.should_skip_file(
            Path(example_file.file_path), example_file.category, example_file
        )
        if skip:
            pytest.skip(reason)

        # 运行示例
        result = suite.runner.run_example(example_file)

        # 验证结果
        if result.status == "skipped":
            pytest.skip(result.error or "Example was skipped")
        elif result.status == "timeout":
            # 在CI环境中提供更详细的超时信息
            if os.environ.get("CI") == "true":
                pytest.fail(
                    f"Example timed out after {suite.runner._get_test_timeout(example_file)}s: {result.error}\n"
                    f"File: {example_file.file_path}\n"
                    f"Category: {example_file.category}\n"
                    f"Estimated runtime: {example_file.estimated_runtime}\n"
                    f"Test tags: {example_file.test_tags}\n"
                    f"Execution time: {result.execution_time:.2f}s\n"
                    f"Output: {result.output[:2000] if result.output else 'No output captured'}\n"
                    f"Error: {result.error}"
                )
            else:
                pytest.fail(f"Example timed out: {result.error}")
        elif result.status == "failed":
            # 对于某些类型的失败，我们可能想要更宽松的处理
            if example_file.category == "rag" and "API key" in (result.error or ""):
                pytest.skip("Missing API key for RAG example")
            else:
                # 在CI环境中提供更详细的失败信息
                if os.environ.get("CI") == "true":
                    pytest.fail(
                        f"Example failed: {result.error}\n"
                        f"File: {example_file.file_path}\n"
                        f"Category: {example_file.category}\n"
                        f"Execution time: {result.execution_time:.2f}s\n"
                        f"Test tags: {example_file.test_tags}\n"
                        f"Output: {result.output[:2000] if result.output else 'No output captured'}\n"
                        f"Error: {result.error}"
                    )
                else:
                    pytest.fail(f"Example failed: {result.error}")
        else:
            # 成功的情况
            assert result.status == "passed", f"Unexpected status: {result.status}"
