"""
Tests for ToolAlpaca data loader.

Tests the download_toolalpaca module's conversion functions.
"""

import json
import tempfile
from pathlib import Path

import pytest


class TestToolAlpacaConversion:
    """Test ToolAlpaca data conversion."""

    @pytest.fixture
    def sample_toolalpaca_data(self) -> list:
        """Create sample ToolAlpaca data for testing (actual format is list)."""
        return [
            {
                "Name": "WeatherAPI",
                "Description": "Get weather information for a location",
                "Category": "Weather",
                "Function_Description": {"get_weather": "Get current weather"},
                "NLDocumentation": "get_weather: Get current weather for a location",
                "Instances": [
                    {
                        "input": "What's the weather in Tokyo?",
                        "output": "The weather in Tokyo is 25°C and sunny.",
                        "Final Thought": "Got the weather info.",
                        "intermediate_steps": [
                            [
                                [
                                    "get_weather",
                                    '{"location": "Tokyo"}',
                                    'Thought: Need weather.\nAction: get_weather\nAction Input: {"location": "Tokyo"}',
                                ],
                                'Observation: {"weather": "sunny", "temp": 25}',
                            ]
                        ],
                    },
                    {
                        "input": "How's the weather in Paris?",
                        "output": "The weather in Paris is 18°C and cloudy.",
                        "Final Thought": "Got Paris weather.",
                        "intermediate_steps": [
                            [
                                [
                                    "get_weather",
                                    '{"location": "Paris"}',
                                    'Thought: Check Paris.\nAction: get_weather\nAction Input: {"location": "Paris"}',
                                ],
                                'Observation: {"weather": "cloudy", "temp": 18}',
                            ]
                        ],
                    },
                ],
            },
            {
                "Name": "Calculator",
                "Description": "Perform mathematical calculations",
                "Category": "Utility",
                "Function_Description": {"calculate": "Evaluate a math expression"},
                "NLDocumentation": "calculate: Evaluate a mathematical expression",
                "Instances": [
                    {
                        "input": "What is 2 + 2?",
                        "output": "2 + 2 = 4",
                        "Final Thought": "Calculated.",
                        "intermediate_steps": [
                            [
                                [
                                    "calculate",
                                    '{"expression": "2 + 2"}',
                                    'Thought: Calculate.\nAction: calculate\nAction Input: {"expression": "2 + 2"}',
                                ],
                                'Observation: {"result": 4}',
                            ]
                        ],
                    }
                ],
            },
        ]

    @pytest.fixture
    def temp_toolalpaca_dir(self, sample_toolalpaca_data) -> Path:
        """Create a temporary directory with ToolAlpaca sample data."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # Write sample data
            data_file = tmp_path / "train_data.json"
            with open(data_file, "w") as f:
                json.dump(sample_toolalpaca_data, f)

            yield tmp_path

    def test_convert_toolalpaca(self, temp_toolalpaca_dir):
        """Test converting ToolAlpaca data to SAGE format."""
        from sage.data.sources.agent_benchmark.external_benchmarks.download_toolalpaca import (
            convert_toolalpaca_to_sage,
        )

        output_dir = temp_toolalpaca_dir / "converted"
        output_dir.mkdir(parents=True, exist_ok=True)

        convert_toolalpaca_to_sage(temp_toolalpaca_dir, output_dir)

        # Check output file exists
        output_file = output_dir / "toolalpaca.jsonl"
        assert output_file.exists(), "Output file should be created"

        # Load and verify content
        samples = []
        with open(output_file) as f:
            for line in f:
                samples.append(json.loads(line))

        # Should have 3 samples (2 from WeatherAPI, 1 from Calculator)
        assert len(samples) == 3

        # Verify first sample structure (SAGE unified format)
        sample = samples[0]
        assert "sample_id" in sample
        assert "task_type" in sample
        assert "instruction" in sample
        assert "candidate_tools" in sample
        assert "ground_truth" in sample
        assert "metadata" in sample
        assert "split" in sample

        # Verify instruction
        assert sample["instruction"] == "What's the weather in Tokyo?"

        # Verify candidate tools (list of tool names)
        assert "get_weather" in sample["candidate_tools"]

        # Verify ground truth has tool calls
        assert "tool_calls" in sample["ground_truth"]
        assert len(sample["ground_truth"]["tool_calls"]) == 1
        assert sample["ground_truth"]["tool_calls"][0]["tool"] == "get_weather"

        # Verify metadata
        assert sample["metadata"]["api_name"] == "WeatherAPI"
        assert sample["metadata"]["source"] == "toolalpaca"

    def test_convert_to_sft_format(self, temp_toolalpaca_dir):
        """Test converting ToolAlpaca to SFT training format."""
        from sage.data.sources.agent_benchmark.external_benchmarks.download_toolalpaca import (
            convert_toolalpaca_to_sft_format,
        )

        output_dir = temp_toolalpaca_dir / "converted"
        output_dir.mkdir(parents=True, exist_ok=True)

        convert_toolalpaca_to_sft_format(temp_toolalpaca_dir, output_dir)

        # Check output file exists
        output_file = output_dir / "toolalpaca_sft.jsonl"
        assert output_file.exists(), "SFT output file should be created"

        # Load and verify content
        samples = []
        with open(output_file) as f:
            for line in f:
                samples.append(json.loads(line))

        # Should have 3 samples
        assert len(samples) == 3

        # Verify first sample structure
        sample = samples[0]
        assert "messages" in sample
        messages = sample["messages"]

        # Should have system, user, and assistant messages
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # System message should mention tool use
        assert "tool" in messages[0]["content"].lower()

        # User message should be the query
        assert "weather" in messages[1]["content"].lower()


class TestExternalBenchmarkLoaderIntegration:
    """Integration tests with ExternalBenchmarkLoader."""

    @pytest.fixture
    def setup_toolalpaca_converted(self, tmp_path) -> Path:
        """Create converted ToolAlpaca data for loader testing."""
        converted_dir = tmp_path / "converted"
        converted_dir.mkdir(parents=True, exist_ok=True)

        # Create sample JSONL file
        samples = [
            {
                "sample_id": "toolalpaca_001",
                "task_type": "tool_selection",
                "instruction": "What's the weather in Tokyo?",
                "context": "{}",
                "candidate_tools": ["get_weather"],
                "ground_truth": {
                    "tool_calls": [{"tool": "get_weather", "input": {"location": "Tokyo"}}],
                    "final_output": "The weather in Tokyo is 25°C and sunny.",
                },
                "metadata": {"api_name": "weather_api", "source": "ToolAlpaca"},
                "split": "train",
            },
            {
                "sample_id": "toolalpaca_002",
                "task_type": "tool_selection",
                "instruction": "Calculate 5 * 3",
                "context": "{}",
                "candidate_tools": ["calculate"],
                "ground_truth": {
                    "tool_calls": [{"tool": "calculate", "input": {"expression": "5 * 3"}}],
                    "final_output": "5 * 3 = 15",
                },
                "metadata": {"api_name": "calculator_api", "source": "ToolAlpaca"},
                "split": "train",
            },
        ]

        output_file = converted_dir / "toolalpaca.jsonl"
        with open(output_file, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")

        return converted_dir

    def test_loader_loads_toolalpaca(self, setup_toolalpaca_converted):
        """Test that ExternalBenchmarkLoader can load ToolAlpaca data."""
        from sage.data.sources.agent_benchmark.external_benchmarks.loader import (
            ExternalBenchmarkLoader,
        )

        loader = ExternalBenchmarkLoader(
            benchmarks="toolalpaca", data_dir=setup_toolalpaca_converted
        )
        samples = list(loader.iter_samples())

        assert len(samples) == 2
        assert samples[0].sample_id == "toolalpaca_001"
        assert samples[0].instruction == "What's the weather in Tokyo?"
        assert samples[0].candidate_tools == ["get_weather"]
        assert samples[0].ground_truth is not None

    def test_loader_list_available_includes_toolalpaca(self, setup_toolalpaca_converted):
        """Test that list_benchmarks includes toolalpaca."""
        from sage.data.sources.agent_benchmark.external_benchmarks.loader import (
            ExternalBenchmarkLoader,
        )

        available = ExternalBenchmarkLoader.list_benchmarks()

        assert "toolalpaca" in available


class TestDownloadFunctions:
    """Test download functions (mocked network calls)."""

    def test_download_sample_creates_file(self, tmp_path):
        """Test that download_toolalpaca_sample creates sample data."""
        from sage.data.sources.agent_benchmark.external_benchmarks.download_toolalpaca import (
            download_toolalpaca_sample,
        )

        source_dir = download_toolalpaca_sample(tmp_path)

        # Check source directory exists
        assert source_dir.exists()

        # Check train_data.json exists
        train_file = source_dir / "train_data.json"
        assert train_file.exists()

        # Verify it's valid JSON
        with open(train_file) as f:
            data = json.load(f)

        # ToolAlpaca format is a list of API objects
        assert isinstance(data, list)
        assert len(data) > 0
        # Each API should have Name and Instances
        assert "Name" in data[0]
        assert "Instances" in data[0]

    def test_download_sample_idempotent(self, tmp_path):
        """Test that calling download_sample twice doesn't fail."""
        from sage.data.sources.agent_benchmark.external_benchmarks.download_toolalpaca import (
            download_toolalpaca_sample,
        )

        # Call twice
        source_dir1 = download_toolalpaca_sample(tmp_path)
        source_dir2 = download_toolalpaca_sample(tmp_path)

        assert source_dir1 == source_dir2
        assert source_dir1.exists()
