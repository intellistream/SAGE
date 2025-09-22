"""
import logging
Example tests for the complete agent workflow.

This demonstrates how the agent pipeline works with real examples.
These are educational examples, not formal unit tests.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch


def create_test_queries_file():
    """Create a temporary test queries file."""
    test_queries = [
        {"query": "在 arXiv 搜索关于 transformer 的论文"},
        {"query": "帮我找一些深度学习的最新研究"},
        {"query": "总结一下注意力机制的发展历程"},
    ]

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
    for query in test_queries:
        temp_file.write(json.dumps(query, ensure_ascii=False) + "\n")
    temp_file.close()

    return temp_file.name


def example_iter_queries():
    """Example: How to read queries from different sources."""
    logging.info("=== Query Reading Examples ===")

    # Import the agent module
    try:
        import sys

        sys.path.append("..")
        from agent import iter_queries

        # Example 1: Local JSONL file
        temp_file = create_test_queries_file()
        try:
            source_config = {
                "type": "local",
                "data_path": temp_file,
                "field_query": "query",
            }

            logging.info("Reading from local JSONL file:")
            queries = list(iter_queries(source_config))
            for i, query in enumerate(queries, 1):
                logging.info(f"  {i}. {query}")

        finally:
            os.unlink(temp_file)

        logging.info(f"\nTotal queries loaded: {len(queries)}")

    except ImportError as e:
        logging.info(f"Could not import agent module: {e}")


def example_mock_agent_workflow():
    """Example: Complete agent workflow with mocks."""
    logging.info("\n=== Mock Agent Workflow Example ===")

    try:
        # Mock all the components
        logging.info("Setting up mock components...")

        # Mock generator that creates plans
        mock_generator = Mock()

        def mock_execute(data):
            user_query = data[0]
            if "arxiv" in user_query.lower() or "论文" in user_query:
                plan = [
                    {
                        "type": "tool",
                        "name": "arxiv_search",
                        "arguments": {"query": "transformer", "max_results": 2},
                    },
                    {"type": "reply", "text": "已为您找到相关论文"},
                ]
            else:
                plan = [{"type": "reply", "text": "我理解您的问题，正在思考..."}]
            return (user_query, json.dumps(plan, ensure_ascii=False))

        mock_generator.execute = mock_execute

        # Mock ArxivSearchTool
        mock_tool = Mock()
        mock_tool.name = "arxiv_search"
        mock_tool.description = "Search arXiv papers"

        def mock_call(arguments):
            return {
                "output": [
                    {
                        "title": "Attention Is All You Need",
                        "authors": "Vaswani et al.",
                        "link": "https://arxiv.org/abs/1706.03762",
                        "abstract": "The dominant sequence transduction models...",
                    }
                ],
                "meta": arguments,
            }

        mock_tool.call = mock_call

        # Simulate the agent workflow
        test_query = "在 arXiv 搜索关于 transformer 的论文"
        logging.info(f"\nProcessing query: {test_query}")

        # Step 1: Generate plan
        logging.info("1. Generating plan...")
        _, plan_json = mock_generator.execute([test_query, "system prompt"])
        plan = json.loads(plan_json)
        logging.info(f"   Plan: {len(plan)} steps")
        for i, step in enumerate(plan, 1):
            logging.info(f"   Step {i}: {step['type']}")

        # Step 2: Execute tools
        logging.info("2. Executing tools...")
        observations = []
        for step in plan:
            if step["type"] == "tool":
                result = mock_tool.call(step["arguments"])
                observations.append(
                    {"tool": step["name"], "result": result, "success": True}
                )
                logging.info(f"   Tool {step['name']}: Found {len(result['output'])} results")

        # Step 3: Generate response
        logging.info("3. Generating response...")
        if any(step["type"] == "reply" for step in plan):
            reply = next(step["text"] for step in plan if step["type"] == "reply")
        else:
            reply = f"基于工具执行结果，为您找到了 {len(observations)} 个相关资源"

        logging.info(f"   Response: {reply}")

        logging.info("\n✅ Workflow completed successfully!")
        return True

    except Exception as e:
        logging.info(f"❌ Workflow failed: {e}")
        return False


def example_configuration_usage():
    """Example: How configuration is used in the agent."""
    logging.info("\n=== Configuration Usage Example ===")

    # Example configuration structure
    example_config = {
        "profile": {
            "name": "ResearchAssistant",
            "role": "助手",
            "language": "zh",
            "goals": ["帮助用户搜索和分析学术论文"],
            "constraints": ["使用提供的工具", "提供准确信息"],
        },
        "tools": [
            {
                "module": "examples.agents.tools.arxiv_search_tool",
                "class": "ArxivSearchTool",
                "init_kwargs": {},
            }
        ],
        "generator": {"remote": {"method": "openai", "model_name": "gpt-3.5-turbo"}},
        "planner": {"max_steps": 5, "enable_repair": True},
        "runtime": {"max_steps": 5, "summarizer": "reuse_generator"},
    }

    logging.info("Example configuration structure:")
    for section, content in example_config.items():
        logging.info(f"  {section}: {type(content).__name__}")
        if isinstance(content, dict):
            for key in content.keys():
                logging.info(f"    - {key}")
        elif isinstance(content, list) and content:
            logging.info(f"    - {len(content)} items")

    logging.info("\nThis configuration defines:")
    logging.info("- Agent profile and personality")
    logging.info("- Available tools and their setup")
    logging.info("- Generator settings for LLM")
    logging.info("- Planning and runtime parameters")


def test_all_examples():
    """Run all examples and report results."""
    logging.info("Agent Workflow Examples")
    logging.info("=" * 50)

    examples = [
        ("Query Reading", example_iter_queries),
        ("Mock Workflow", example_mock_agent_workflow),
        ("Configuration", example_configuration_usage),
    ]

    results = []
    for name, example_func in examples:
        try:
            logging.info(f"\n--- {name} ---")
            result = example_func()
            if result is None:  # For examples that don't return boolean
                result = True
            results.append((name, result))
        except Exception as e:
            logging.info(f"❌ {name} failed: {e}")
            results.append((name, False))

    logging.info("\n" + "=" * 50)
    logging.info("Example Results:")
    for name, success in results:
        status = "✅" if success else "❌"
        logging.info(f"  {status} {name}")

    total_success = sum(1 for _, success in results if success)
    logging.info(f"\nCompleted: {total_success}/{len(results)} examples")

    return total_success == len(results)


if __name__ == "__main__":
    success = test_all_examples()

    if success:
        logging.info("\n🎉 All examples completed successfully!")
        logging.info("\nThese examples demonstrate:")
        logging.info("- How to read queries from different sources")
        logging.info("- Complete agent workflow with mocking")
        logging.info("- Configuration structure and usage")
        logging.info("- Integration between components")
    else:
        logging.info("\n⚠️  Some examples had issues. Check the implementation.")

    logging.info(f"\nFor the real agent implementation, see: agent.py")
    logging.info(f"For configuration examples, see: ../config/config_agent_min.yaml")
