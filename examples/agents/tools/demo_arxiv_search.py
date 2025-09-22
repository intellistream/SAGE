"""
import logging
Demo: ArxivSearchTool Usage Examples

This demo file shows practical examples of how to use the ArxivSearchTool
in different scenarios. These are educational demonstrations for developers
and users, not formal unit tests.

For the actual tool implementation, see: arxiv_search_tool.py
For formal unit tests, see: packages/sage-libs/tests/lib/agents/test_arxiv_tool.py

Examples included:
- Basic usage with different parameters
- Error handling and offline fallback
- Integration with MCP Registry
- Parameter variations and configurations
"""

import json
from unittest.mock import Mock, patch

import pytest
from arxiv_search_tool import ArxivSearchTool


def example_basic_usage():
    """Example: Basic usage of ArxivSearchTool."""
    logging.info("=== Basic ArxivSearchTool Usage Example ===")

    tool = ArxivSearchTool()

    # Mock the network call for demonstration
    with patch.object(tool, "_search_arxiv") as mock_search:
        mock_search.return_value = [
            {
                "title": "Attention Is All You Need",
                "authors": "Ashish Vaswani, Noam Shazeer, Niki Parmar",
                "link": "https://arxiv.org/abs/1706.03762",
                "abstract": "The dominant sequence transduction models...",
            },
            {
                "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                "authors": "Jacob Devlin, Ming-Wei Chang, Kenton Lee",
                "link": "https://arxiv.org/abs/1810.04805",
                "abstract": "We introduce a new language representation model...",
            },
        ]

        # Example usage
        result = tool.call(
            {"query": "transformer attention", "max_results": 2, "with_abstract": True}
        )

        logging.info(f"Query: {result['meta']['query']}")
        logging.info(f"Found {len(result['output'])} papers:")
        for i, paper in enumerate(result["output"], 1):
            logging.info(f"\n{i}. {paper['title']}")
            logging.info(f"   Authors: {paper['authors']}")
            logging.info(f"   Link: {paper['link']}")
            logging.info(f"   Abstract: {paper['abstract'][:100]}...")


def example_parameter_variations():
    """Example: Different parameter configurations."""
    logging.info("\n=== Parameter Variations Example ===")

    tool = ArxivSearchTool()

    with patch.object(tool, "_search_arxiv") as mock_search:
        mock_search.return_value = [
            {
                "title": "Sample Paper",
                "authors": "Sample Author",
                "link": "https://arxiv.org/abs/1234.5678",
                "abstract": "Sample abstract",
            }
        ]

        # Example 1: Minimal parameters
        result1 = tool.call({"query": "machine learning"})
        logging.info(f"Minimal call - max_results: {result1['meta']['max_results']}")

        # Example 2: Custom parameters
        result2 = tool.call(
            {
                "query": "deep learning",
                "max_results": 5,
                "size": 50,
                "with_abstract": False,
            }
        )
        logging.info(
            f"Custom call - max_results: {result2['meta']['max_results']}, size: {result2['meta']['size']}"
        )


def example_error_handling():
    """Example: Error handling and offline fallback."""
    logging.info("\n=== Error Handling Example ===")

    tool = ArxivSearchTool()

    # Simulate network error
    with patch.object(tool, "_search_arxiv") as mock_search:
        mock_search.side_effect = Exception("Network error")

        result = tool.call({"query": "neural networks", "max_results": 3})

        logging.info(f"Network error occurred, using offline fallback:")
        logging.info(f"Offline mock: {result['meta'].get('offline_mock', False)}")
        logging.info(f"Results: {len(result['output'])} papers")


def example_mcp_integration():
    """Example: Integration with MCP Registry."""
    logging.info("\n=== MCP Registry Integration Example ===")

    try:
        from sage.libs.agents.action.mcp_registry import MCPRegistry

        # Create registry and register tool
        registry = MCPRegistry()
        tool = ArxivSearchTool()
        registry.register(tool)

        # Mock the search for demonstration
        with patch.object(tool, "_search_arxiv") as mock_search:
            mock_search.return_value = [
                {
                    "title": "GPT-3 Paper",
                    "authors": "OpenAI Team",
                    "link": "https://arxiv.org/abs/example",
                    "abstract": "Language models are few-shot learners",
                }
            ]

            # Call through registry
            result = registry.call(
                "arxiv_search", {"query": "GPT language models", "max_results": 1}
            )

            logging.info(f"Called through MCP Registry:")
            logging.info(f"Tool: {tool.name}")
            logging.info(f"Result: {result['output'][0]['title']}")

    except ImportError:
        logging.info("MCP Registry not available - skipping integration example")


def test_example_runs():
    """Test that all examples run without errors."""
    try:
        example_basic_usage()
        example_parameter_variations()
        example_error_handling()
        example_mcp_integration()
        logging.info("\n✅ All examples completed successfully!")
        return True
    except Exception as e:
        logging.info(f"\n❌ Example failed: {e}")
        return False


if __name__ == "__main__":
    logging.info("ArxivSearchTool Examples")
    logging.info("=" * 40)

    success = test_example_runs()

    if success:
        logging.info("\nThese examples show how to:")
        logging.info("1. Use ArxivSearchTool with different parameters")
        logging.info("2. Handle network errors with offline fallback")
        logging.info("3. Integrate with MCP Registry")
        logging.info("4. Process and display results")

        logging.info("\nFor more details, see the tool implementation in arxiv_search_tool.py")
    else:
        logging.info("\nSome examples failed. Check the implementation and dependencies.")
